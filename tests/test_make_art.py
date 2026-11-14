"""tools/make_art.py 시험. 진짜 그림 API 대신 이 파일 안의 가짜 서버를 쓴다."""

import base64
import contextlib
import http.server
import importlib.util
import io
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("make_art", ROOT / "tools" / "make_art.py")
make_art = importlib.util.module_from_spec(_SPEC)
sys.modules["make_art"] = make_art
_SPEC.loader.exec_module(make_art)

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None

TILDE = chr(126)       # 문자열에 쓰면 안 되는 두 글자. 이 파일에도 직접 적지 않는다
EM_DASH = chr(0x2014)
PNG_HEAD = b"\x89PNG\r\n\x1a\n"
TINY_PNG = PNG_HEAD + b"rest-of-a-fake-png"
GOOD_ENV = {
    "CLOUDFLARE_ACCOUNT_ID": "acct123",
    "CLOUDFLARE_API_TOKEN": "good-token",
    "GEMINI_API_KEY": "good-gemini",
}
HAIR = [
    ("orange", (240, 110, 40)), ("navy-blue", (30, 40, 90)), ("yellow-green", (170, 225, 120)),
    ("yellow", (250, 215, 60)), ("purple", (150, 80, 200)), ("Black bob", (25, 25, 30)),
]


def parse_multipart(content_type, body):
    boundary = content_type.split("boundary=")[1].encode()
    fields, files = {}, {}
    for chunk in body.split(b"--" + boundary)[1:]:
        if chunk.startswith(b"--"):
            break
        head, _, data = chunk.partition(b"\r\n\r\n")
        data = data[:-2]
        name = re.search(r'name="([^"]+)"', head.decode()).group(1)
        if b"filename=" in head:
            files[name] = data
        else:
            fields[name] = data.decode("utf-8")
    return fields, files


def fake_sprite(width, height, key_rgb, hair, wide_mouth):
    """단색 배경 위에 머리, 얼굴, 몸이 있는 그림. 두 배로 그렸다가 줄여서 가장자리를 부드럽게 한다."""
    big = Image.new("RGB", (width * 2, height * 2), key_rgb)
    draw = ImageDraw.Draw(big)
    w, h = big.size
    draw.rounded_rectangle((w * 0.2, h * 0.58, w * 0.8, h * 1.1), radius=w * 0.1, fill=(40, 50, 110))
    draw.ellipse((w * 0.26, h * 0.14, w * 0.74, h * 0.56), fill=hair)
    draw.ellipse((w * 0.33, h * 0.24, w * 0.67, h * 0.6), fill=(255, 222, 200))
    mouth = 0.12 if wide_mouth else 0.05
    draw.ellipse((w * (0.5 - mouth), h * 0.48, w * (0.5 + mouth), h * 0.52), fill=(190, 60, 70))
    return big.resize((width, height), Image.LANCZOS)


def fake_scene(width, height):
    image = Image.new("RGB", (width, height), (150, 200, 240))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, height * 0.6, width, height), fill=(200, 180, 150))
    draw.rectangle((width * 0.1, height * 0.2, width * 0.3, height * 0.6), fill=(120, 90, 70))
    return image


def render(prompt, width, height, as_jpeg):
    if Image is None:
        return TINY_PNG
    if "chroma key" in prompt:
        key = (0, 255, 0) if "#00FF00" in prompt else (255, 0, 255)
        hair = next((color for word, color in HAIR if word in prompt), (90, 90, 90))
        image = fake_sprite(width, height, key, hair, "smile" in prompt)
    else:
        image = fake_scene(width, height)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG" if as_jpeg else "PNG", quality=92)
    return buffer.getvalue()


DAILY_LIMIT_TEXT = (
    "You have used up your daily free allocation of 10,000 neurons. "
    "Please upgrade to Cloudflare's Workers Paid plan if you would like to continue usage."
)
BAD_INPUT = 5006   # 입력이 틀렸을 때 가짜 서버가 쓰는 번호. 공식 오류 표에는 없는 임의의 값이다
GEMINI_1K = {"1:1": (1024, 1024), "2:3": (848, 1264), "16:9": (1376, 768)}   # 문서의 1K 크기 표


class FakeApi(http.server.ThreadingHTTPServer):
    """Cloudflare와 Gemini 흉내. 2026-11-13의 공식 문서에 적힌 형식을 따른다. 받은 요청을 log에 적어 둔다.

    Cloudflare (developers.cloudflare.com/workers-ai):
      - flux-2-klein-4b는 multipart만 받는다. 칸은 prompt, width, height(256에서 1920), seed, guidance,
        input_image_0부터 input_image_3. 참고 그림은 512x512보다 작아야 한다.
      - flux-1-schnell은 JSON만 받는다. 입력 스키마는 prompt(2048자까지)와 steps(8까지)뿐이다.
      - 답은 {"result": {"image": base64}, "success": true, "errors": [], "messages": []}.
      - 오류는 {"success": false, "errors": [{"code": 숫자, "message": ...}]}. 번호는 오류 표의 것.
    Gemini (ai.google.dev, Interactions API):
      - 답은 steps 안의 model_output 단계에 그림이 들어 있다. 생각 단계(thought)에 중간 그림이 올 수 있다.
      - 오류는 {"error": {"code": "snake_case 글자", "message": ...}}.
    """

    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), FakeHandler)
        self.log = []
        self.reject_first = False     # 첫 요청을 3030으로 돌려보낸다 (공식 표에 없는, 알려진 번호)
        self.timeout_first = False    # 첫 요청을 3007(HTTP 408)로 돌려보낸다
        self.quota_after = None       # 이만큼 만든 뒤로는 하루 한도 오류(3036)를 낸다
        self.schnell_refuses_seed = False   # 입력 스키마에 없는 칸이 오면 거절한다
        self.gemini_rejects_format = False
        self.served = 0

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"


class FakeHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body, content_type="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cf_error(self, status, code, message):
        self._send(status, {
            "success": False, "errors": [{"code": code, "message": message}], "messages": [], "result": None,
        })

    def _cf_input_problem(self, entry):
        """문서에 적힌 입력 규칙에 어긋나는 점을 찾는다. 없으면 None."""
        fields, files = entry["fields"], entry["files"]
        if not isinstance(fields.get("prompt"), str) or not fields["prompt"]:
            return "prompt is required"
        if "flux-2" in entry["path"]:
            if entry["type"] != "multipart/form-data":
                return "this model takes multipart form data"
            unknown = set(fields) - {"prompt", "width", "height", "seed", "guidance"}
            if unknown:
                return f"unknown field: {sorted(unknown)}"
            for name in ("width", "height"):
                if name in fields and not 256 <= int(fields[name]) <= 1920:
                    return f"{name} must be between 256 and 1920"
            if set(files) - {f"input_image_{i}" for i in range(4)}:
                return "input images must be named input_image_0 to input_image_3"
            if Image is not None:
                for data in files.values():
                    with Image.open(io.BytesIO(data)) as ref:
                        if max(ref.size) >= 512:
                            return "input images must be smaller than 512x512"
            return None
        if entry["type"] != "application/json":
            return "this model takes JSON"
        if len(fields["prompt"]) > 2048:
            return "prompt must be at most 2048 characters"
        if fields.get("steps", 4) > 8:
            return "steps must be at most 8"
        if self.server.schnell_refuses_seed and set(fields) - {"prompt", "steps"}:
            return "must NOT have additional properties"
        return None

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        content_type = self.headers.get("Content-Type", "")
        server = self.server
        if self.path == "/interactions":
            return self._gemini(body)
        entry = {"path": self.path, "type": content_type.split(";")[0], "agent": self.headers.get("User-Agent")}
        if content_type.startswith("multipart/form-data"):
            entry["fields"], entry["files"] = parse_multipart(content_type, body)
        else:
            entry["fields"], entry["files"] = json.loads(body), {}
        server.log.append(entry)
        if self.headers.get("Authorization") != "Bearer good-token":
            return self._cf_error(401, 10000, "Authentication error")
        if server.quota_after is not None and server.served >= server.quota_after:
            return self._cf_error(429, 3036, DAILY_LIMIT_TEXT)
        if server.timeout_first and len(server.log) == 1:
            return self._cf_error(408, 3007, "Request timeout")
        if server.reject_first and len(server.log) == 1:
            return self._cf_error(400, 3030, "Output image was rejected")
        problem = self._cf_input_problem(entry)
        if problem:
            return self._cf_error(400, BAD_INPUT, problem)
        fields = entry["fields"]
        # schnell은 JPEG로 준다. klein이 어떤 형식으로 주는지는 문서에 없어서 PNG와 JPEG를 번갈아 준다.
        as_jpeg = "flux-2" not in self.path or server.served % 2 == 1
        data = render(fields["prompt"], int(fields.get("width", 1024)), int(fields.get("height", 1024)), as_jpeg)
        server.served += 1
        self._send(200, {
            "result": {"image": base64.b64encode(data).decode()}, "success": True, "errors": [], "messages": [],
        })

    def _gemini_error(self, status, code, message):
        self._send(status, {"error": {"code": code, "message": message}})

    def _gemini(self, body):
        server = self.server
        doc = json.loads(body)
        server.log.append({"path": self.path, "doc": doc})
        if self.headers.get("x-goog-api-key") != "good-gemini":
            return self._gemini_error(401, "authentication", "API key not valid. Please pass a valid API key.")
        if server.gemini_rejects_format and "response_format" in doc:
            return self._gemini_error(400, "parameter_unknown", "Unknown parameter: 'response_format'.")
        aspect = doc.get("response_format", {}).get("aspect_ratio", "1:1")
        data = render(doc["input"][0]["text"], *GEMINI_1K[aspect], True)
        draft = render("draft", 64, 64, True)
        server.served += 1

        def image(blob):
            return {"type": "image", "mime_type": "image/jpeg", "data": base64.b64encode(blob).decode()}

        self._send(200, {
            "id": "v1_abc", "object": "interaction", "model": doc["model"], "status": "completed",
            "created": "2026-11-13T00:00:00Z", "updated": "2026-11-13T00:00:00Z",
            "steps": [
                {"type": "thought", "signature": "sig", "summary": [
                    {"type": "text", "text": "Testing the composition."}, image(draft),
                ]},
                {"type": "model_output", "content": [image(data)]},
            ],
            "usage": {"total_input_tokens": 300, "total_output_tokens": 1120, "total_tokens": 1420},
        })


class Unit(unittest.TestCase):
    def setUp(self):
        self.cfg = make_art.load_config()

    def test_multipart_carries_fields_and_binary_files(self):
        blob = bytes(range(256)) * 3 + b"\r\n--tail"
        body, content_type = make_art.encode_multipart(
            {"prompt": "한글 prompt", "width": 768}, [("input_image_0", "ref0.jpg", "image/jpeg", blob)]
        )
        self.assertTrue(content_type.startswith("multipart/form-data; boundary="))
        fields, files = parse_multipart(content_type, body)
        self.assertEqual(fields, {"prompt": "한글 prompt", "width": "768"})
        self.assertEqual(files, {"input_image_0": blob})

    def test_sniff_image(self):
        self.assertEqual(make_art.sniff_image(TINY_PNG), "png")
        self.assertEqual(make_art.sniff_image(b"\xff\xd8\xff\xe0rest"), "jpg")
        self.assertEqual(make_art.sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "webp")
        self.assertIsNone(make_art.sniff_image(b'{"result": 1}'))

    def test_cloudflare_answer_in_both_shapes(self):
        # FLUX 계열이 주는 모양: 문서의 응답 예시와 출력 스키마({"image": base64})
        wrapped = json.dumps({
            "result": {"image": base64.b64encode(TINY_PNG).decode()}, "success": True, "errors": [], "messages": [],
        })
        self.assertEqual(make_art.decode_cloudflare(200, wrapped.encode()), TINY_PNG)
        # 옛 그림 모델은 그림 바이트를 그대로 준다. 그것도 받는다
        self.assertEqual(make_art.decode_cloudflare(200, TINY_PNG), TINY_PNG)

    def _cf_error(self, status, code, message):
        body = json.dumps({"success": False, "errors": [{"code": code, "message": message}]}).encode()
        with self.assertRaises(make_art.ArtError) as caught:
            make_art.decode_cloudflare(status, body)
        return caught.exception

    def test_cloudflare_errors_are_sorted(self):
        # 번호와 HTTP 상태와 문장은 Workers AI 문서의 오류 표에서 가져왔다 (10000과 3030은 표에 없다)
        auth = self._cf_error(401, 10000, "Authentication error")
        self.assertTrue(auth.stop)
        self.assertIn("CLOUDFLARE_API_TOKEN", str(auth))
        limit = self._cf_error(429, 3036, DAILY_LIMIT_TEXT)
        self.assertTrue(limit.stop)
        self.assertIn("오전 9시", str(limit))
        self.assertTrue(self._cf_error(400, 3030, "Output image was rejected").reroll)
        busy = self._cf_error(429, 3040, "Capacity temporarily exceeded, please try again.")
        self.assertTrue(busy.retry and busy.quota and not busy.stop)
        self.assertTrue(self._cf_error(408, 3007, "Request timeout").retry)
        self.assertTrue(self._cf_error(408, 3008, "Request was aborted").retry)
        self.assertTrue(self._cf_error(503, None, "upstream error").retry)
        for status, code, message in (
            (400, 5007, "No such model @cf/nobody/nothing or task"),
            (404, 3042, "The model name is invalid"),
            (410, 5028, "@cf/old/model was deprecated on 2026-01-01."),
        ):
            gone = self._cf_error(status, code, message)
            self.assertTrue(gone.stop, code)
            self.assertIn("--model", str(gone))
        paid = self._cf_error(403, 5035, "This model requires a Workers Paid plan.")
        self.assertTrue(paid.stop)
        self.assertNotIn("CLOUDFLARE_API_TOKEN", str(paid))   # 토큰 탓이 아니다
        for status, code, message in (
            (400, BAD_INPUT, "width must be between 256 and 1920"), (413, 3006, "Request is too large"),
        ):
            plain = self._cf_error(status, code, message)
            self.assertFalse(plain.stop or plain.retry or plain.reroll, code)
            self.assertIn(message, str(plain))

    def test_cloudflare_garbage_answer(self):
        with self.assertRaises(make_art.ArtError):
            make_art.decode_cloudflare(200, b"<html>oops</html>")
        with self.assertRaises(make_art.ArtError):
            make_art.decode_cloudflare(200, json.dumps({"success": True, "result": {}}).encode())

    def test_gemini_answer(self):
        def image(blob):
            return {"type": "image", "mime_type": "image/jpeg", "data": base64.b64encode(blob).decode()}

        first, draft = b"\xff\xd8\xff-first", b"\xff\xd8\xff-draft"
        doc = {"steps": [{"type": "model_output", "content": [image(first), image(TINY_PNG)]}]}
        self.assertEqual(make_art.decode_gemini(200, json.dumps(doc).encode()), TINY_PNG)
        # 생각 단계의 중간 그림이 아니라 결과 단계의 그림을 고른다. 단계의 순서와 상관없다
        doc = {"steps": [
            {"type": "model_output", "content": [image(TINY_PNG)]},
            {"type": "thought", "signature": "sig", "summary": [image(draft)]},
        ]}
        self.assertEqual(make_art.decode_gemini(200, json.dumps(doc).encode()), TINY_PNG)
        # 단계에 이름표가 없어도 그림이 있으면 받는다
        doc = {"steps": [{"content": [image(first), image(TINY_PNG)]}]}
        self.assertEqual(make_art.decode_gemini(200, json.dumps(doc).encode()), TINY_PNG)
        empty = {"steps": [{"type": "model_output", "content": [{"type": "text", "text": "no"}]}]}
        with self.assertRaises(make_art.ArtError) as caught:
            make_art.decode_gemini(200, json.dumps(empty).encode())
        self.assertTrue(caught.exception.reroll)

    def _gemini_error(self, status, code, message):
        body = json.dumps({"error": {"code": code, "message": message}}).encode()
        with self.assertRaises(make_art.ArtError) as caught:
            make_art.decode_gemini(status, body)
        return caught.exception

    def test_gemini_errors_are_sorted(self):
        # 코드와 HTTP 상태는 Gemini 문서의 API errors 표에서 가져왔다
        for status, code in ((401, "authentication"), (403, "permission_denied")):
            denied = self._gemini_error(status, code, "API key not valid.")
            self.assertTrue(denied.stop, code)
            self.assertIn("GEMINI_API_KEY", str(denied))
        for status, code in ((402, "payment_required"), (400, "failed_precondition")):
            unpaid = self._gemini_error(status, code, "Billing is not enabled.")
            self.assertTrue(unpaid.stop, code)
            self.assertIn("결제", str(unpaid))
        missing = self._gemini_error(404, "model_not_found", "The specified model was not found.")
        self.assertTrue(missing.stop)
        self.assertIn("--model", str(missing))
        for code in ("rate_limit_exceeded", "quota_exceeded", "too_many_requests"):
            busy = self._gemini_error(429, code, "Too many requests.")
            self.assertTrue(busy.retry and busy.quota and not busy.stop, code)
        for status, code in ((500, "api_error"), (503, "service_unavailable"), (504, "deadline_exceeded")):
            self.assertTrue(self._gemini_error(status, code, "Try again.").retry, code)
        # 그림이 걸러졌다는 코드. 어떤 HTTP 상태로 오는지는 문서에 없어서 두 경우를 다 본다
        for status in (200, 400):
            for code in ("image_safety", "image_other", "no_image"):
                blocked = self._gemini_error(status, code, "Safety violations blocked image generation.")
                self.assertTrue(blocked.reroll and not blocked.stop, code)
        plain = self._gemini_error(400, "invalid_request", "The request payload is malformed.")
        self.assertFalse(plain.stop or plain.retry or plain.reroll)
        self.assertIn("malformed", str(plain))

    def test_only_names(self):
        everything = make_art.all_keys(self.cfg)
        extra = sum(len(make_art.faces_for(self.cfg, c)) - 6 for c in self.cfg["characters"])
        self.assertEqual(len(everything), 6 * 6 + extra + 8)
        self.assertEqual(make_art.parse_only([], self.cfg), everything)
        self.assertEqual(
            make_art.parse_only(["astra"], self.cfg),
            [f"astra:{face}" for face in make_art.FACES] + ["astra:huff", "astra:denial"],
        )
        self.assertEqual(
            make_art.parse_only(["library,sora:smile", "bg:rooftop"], self.cfg),
            ["sora:smile", "bg:library", "bg:rooftop"],
        )
        self.assertEqual(len(make_art.parse_only(["bg"], self.cfg)), 8)
        self.assertEqual(len(make_art.parse_only(["sprites"], self.cfg)), 36 + extra)
        self.assertEqual(make_art.parse_only(["astra:huff"], self.cfg), ["astra:huff"])
        with self.assertRaises(ValueError) as caught:
            make_art.parse_only(["giulhe"], self.cfg)
        self.assertIn("astra", str(caught.exception))

    def test_extra_face_names_and_poses_are_checked(self):
        for change, word in (
            (lambda c: c["characters"]["astra"]["faces"].update({"Bad-Name": "x"}), "Bad-Name"),
            (lambda c: c["characters"]["astra"].update({"poses": {"nobody": "x"}}), "nobody"),
            (lambda c: c["characters"]["astra"].update({"poses": {"neutral": "x"}}), "neutral"),
        ):
            cfg = json.loads((ROOT / "tools" / "art_prompts.json").read_text(encoding="utf-8"))
            change(cfg)
            with tempfile.TemporaryDirectory() as tmp:
                path = pathlib.Path(tmp) / "prompts.json"
                path.write_text(json.dumps(cfg), encoding="utf-8")
                with self.assertRaises(ValueError) as caught:
                    make_art.load_config(path)
            self.assertIn(word, str(caught.exception))

    def test_faces_match_the_engine(self):
        from sogaeting import actor, content
        self.assertEqual(make_art.FACES, actor.FACES)
        self.assertEqual(sorted(self.cfg["characters"]), sorted(content.list_character_ids()))
        # 캐릭터만의 표정: 그림 요청문과 게임의 캐릭터 설정(extra_faces)이 같은 이름을 갖는다
        for char_id in self.cfg["characters"]:
            with self.subTest(character=char_id):
                self.assertEqual(make_art.faces_for(self.cfg, char_id),
                                 actor.faces_for(content.load_character(char_id)))
        seeds = json.loads((ROOT / "sogaeting" / "data" / "seeds.json").read_text(encoding="utf-8"))
        self.assertEqual([b["seed"] for b in self.cfg["backgrounds"].values()], seeds["entrance"])

    def test_prompts(self):
        for key in make_art.all_keys(self.cfg):
            left, right = make_art.split_key(key)
            if make_art.is_bg(key):
                prompts = [make_art.bg_prompt(self.cfg, right)]
                self.assertIn("no people", prompts[0])
            else:
                prompts = [make_art.sprite_prompt(self.cfg, left, right, variant=v) for v in (False, True)]
                for prompt in prompts:
                    self.assertIn("chroma key", prompt)
                    self.assertIn("modest", prompt)
                    self.assertIn(self.cfg["characters"][left]["look"], prompt)
                self.assertIn("Expression:", prompts[0])
                self.assertIn("reference image", prompts[1])
                self.assertNotIn("reference image", prompts[0])
            for prompt in prompts:
                self.assertLess(len(prompt), 2000, key)   # schnell은 2048자까지만 받는다
                self.assertNotIn(TILDE, prompt)
                self.assertNotIn(EM_DASH, prompt)
                self.assertNotIn("{", prompt)
        smile = make_art.sprite_prompt(self.cfg, "haiku", "smile", variant=True)
        self.assertIn("deadpan", smile)   # 캐릭터가 따로 정한 표정이 공통 표정보다 먼저다

    def test_seed_is_stable(self):
        self.assertEqual(make_art.seed_for("astra"), make_art.seed_for("astra"))
        self.assertNotEqual(make_art.seed_for("astra"), make_art.seed_for("sora"))
        self.assertEqual(make_art.seed_for("astra", 3), make_art.seed_for("astra") + 3)

    def test_dotenv(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / ".env"
            path.write_text('﻿# 주석\nART_TEST_A="따옴표"\nART_TEST_B = plain \nART_TEST_C=새 값\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {"ART_TEST_C": "원래 값"}):
                make_art.load_dotenv(path)
                self.assertEqual(os.environ["ART_TEST_A"], "따옴표")
                self.assertEqual(os.environ["ART_TEST_B"], "plain")
                self.assertEqual(os.environ["ART_TEST_C"], "원래 값")
                for name in ("ART_TEST_A", "ART_TEST_B"):
                    os.environ.pop(name)

    def test_no_keys_in_the_script(self):
        text = (ROOT / "tools" / "make_art.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"AIza[0-9A-Za-z_\-]{20,}", text))
        self.assertNotIn(TILDE, text)
        self.assertNotIn(EM_DASH, text)


class OldFolderTest(unittest.TestCase):
    def test_raw_in_old_folder_is_found(self):
        # 2026-11-13에 id를 바꿨다. 받은 그림을 예전 폴더(art/raw/giulhee)에 넣어도 찾는다
        with tempfile.TemporaryDirectory() as tmp:
            old = pathlib.Path(tmp) / "raw" / "giulhee"
            old.mkdir(parents=True)
            (old / "smile.png").write_bytes(b"x")
            self.assertEqual(make_art.find_raw(tmp, "astra:smile"), old / "smile.png")
            new = pathlib.Path(tmp) / "raw" / "astra"
            new.mkdir(parents=True)
            (new / "smile.png").write_bytes(b"y")
            self.assertEqual(make_art.find_raw(tmp, "astra:smile"), new / "smile.png")  # 새 폴더가 먼저다


class GptDoc(unittest.TestCase):
    def setUp(self):
        self.cfg = make_art.load_config()
        self.doc = make_art.gpt_doc(self.cfg)

    def test_every_character_and_face_has_a_prompt(self):
        for char_id, char in self.cfg["characters"].items():
            self.assertIn(f"### {char['name']} ({char_id})", self.doc)
            self.assertIn(char["look"], self.doc)
            for face in make_art.faces_for(self.cfg, char_id):
                self.assertIn(f"`art/raw/{char_id}/{face}.png`", self.doc)

    def test_prompts_keep_the_all_ages_line_and_style(self):
        for char_id in self.cfg["characters"]:
            prompt = make_art.gpt_sprite_prompt(self.cfg, char_id)
            self.assertIn(self.cfg["sprite"]["safety"], prompt)
            self.assertIn(self.cfg["sprite"]["style"], prompt)
            self.assertIn("transparent", prompt)

    def test_no_forbidden_marks(self):
        self.assertNotIn(TILDE, self.doc)
        self.assertNotIn(EM_DASH, self.doc)

    def test_committed_doc_is_up_to_date(self):
        # art_prompts.json을 고치면 문서도 다시 만들어야 한다
        saved = (ROOT / "docs" / "art-prompts-gpt.md").read_text(encoding="utf-8")
        self.assertEqual(saved, self.doc, "python tools/make_art.py --gpt-doc 을 다시 실행하세요")


@unittest.skipIf(Image is None, "Pillow가 없으면 건너뛴다")
class Cutting(unittest.TestCase):
    def _cut(self, key, key_rgb, hair, as_jpeg=False):
        image = fake_sprite(384, 576, key_rgb, hair, False)
        if as_jpeg:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            image = Image.open(io.BytesIO(buffer.getvalue()))
        return make_art.cut_background(image, key)

    def test_background_becomes_transparent(self):
        for key, key_rgb, hair in (
            ("green", (0, 255, 0), (240, 110, 40)), ("green", (0, 255, 0), (150, 80, 200)),
            ("green", (40, 215, 60), (30, 40, 90)),        # 모델이 초록을 조금 다르게 칠한 경우
            ("magenta", (255, 0, 255), (170, 225, 120)), ("magenta", (255, 0, 255), (250, 215, 60)),
            ("magenta", (235, 30, 215), (25, 25, 30)),
        ):
            for as_jpeg in (False, True):
                with self.subTest(key=key, hair=hair, jpeg=as_jpeg):
                    cut, warning = self._cut(key, key_rgb, hair, as_jpeg)
                    self.assertIsNone(warning)
                    self.assertEqual(cut.mode, "RGBA")
                    width, height = cut.size
                    for corner in ((2, 2), (width - 3, 2), (2, height // 3), (width - 3, height // 3)):
                        self.assertEqual(cut.getpixel(corner)[3], 0)
                    self.assertEqual(cut.getpixel((width // 2, height * 4 // 10))[3], 255)   # 얼굴
                    self.assertEqual(cut.getpixel((width // 2, height * 2 // 10))[3], 255)   # 머리
                    self.assertEqual(cut.getpixel((width // 2, height - 3))[3], 255)         # 몸
                    # 남은 가장자리에 배경색이 묻어 있으면 안 된다
                    data = cut.tobytes()
                    worst = 0
                    for at in range(0, len(data), 4):
                        red, green, blue, alpha = data[at:at + 4]
                        if alpha > 40:
                            spill = green - max(red, blue) if key == "green" else min(red, blue) - green
                            worst = max(worst, spill)
                    self.assertLessEqual(worst, 45)

    def test_wrong_background_is_reported_not_cut(self):
        image = fake_sprite(200, 300, (250, 250, 250), (240, 110, 40), False)
        cut, warning = make_art.cut_background(image, "green")
        self.assertIn("단색", warning)
        self.assertEqual(cut.getpixel((2, 2))[3], 255)

    def test_already_transparent_image_is_kept_as_is(self):
        # 다른 도구로 뽑은 투명 배경 그림: 색을 지우지 않고 크기만 맞춘다
        image = Image.new("RGBA", (400, 600), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle((100, 100, 299, 599), fill=(0, 255, 0, 255))  # 초록 옷
        self.assertTrue(make_art.has_transparency(image))
        self.assertFalse(make_art.has_transparency(Image.new("RGB", (40, 60), (0, 255, 0))))
        self.assertFalse(make_art.has_transparency(Image.new("RGBA", (40, 60), (0, 255, 0, 255))))
        with tempfile.TemporaryDirectory() as tmp:
            raw = pathlib.Path(tmp) / "neutral.png"
            out = pathlib.Path(tmp) / "out" / "neutral.png"
            image.save(raw)
            cfg = make_art.load_config()
            self.assertIsNone(make_art.finish_sprite(raw, out, cfg, "astra"))
            with Image.open(out) as done:
                self.assertEqual(done.size, (cfg["sprite"]["width"], cfg["sprite"]["height"]))
                center = done.getpixel((done.width // 2, done.height - 10))
                self.assertEqual(center, (0, 255, 0, 255))   # 초록 옷이 지워지지 않았다
                self.assertEqual(done.getpixel((2, 2))[3], 0)

    def test_normalize_puts_figure_bottom_center(self):
        image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle((50, 100, 149, 299), fill=(200, 0, 0, 255))
        placed = make_art.normalize_sprite(image, (300, 600), top_margin=0.0, max_scale=10)
        self.assertEqual(placed.size, (300, 600))
        self.assertEqual(placed.getchannel("A").getbbox(), (0, 0, 300, 600))
        capped = make_art.normalize_sprite(image, (300, 600), top_margin=0.0, max_scale=1.5)
        self.assertEqual(capped.getchannel("A").getbbox(), (75, 300, 225, 600))
        self.assertIsNone(make_art.normalize_sprite(Image.new("RGBA", (10, 10), (0, 0, 0, 0)), (20, 20)))


@unittest.skipIf(Image is None, "Pillow가 없으면 건너뛴다")
class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        threading.Thread(target=self.api.serve_forever, daemon=True).start()
        self.addCleanup(self.api.server_close)
        self.addCleanup(self.api.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.out = pathlib.Path(folder.name) / "art"
        for target, value in (
            ("CF_BASE", self.api.url), ("GEMINI_BASE", self.api.url),
            ("_sleep", lambda seconds: None), ("load_dotenv", lambda path: None),
        ):
            patcher = mock.patch.object(make_art, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_tool(self, *argv, env=GOOD_ENV):
        clean = {k: v for k, v in os.environ.items() if k not in GOOD_ENV}
        screen = io.StringIO()
        with mock.patch.dict(os.environ, {**clean, **env}, clear=True), contextlib.redirect_stdout(screen):
            code = make_art.main([*argv, "--out", str(self.out)])
        return code, screen.getvalue()

    def test_one_character_and_one_background(self):
        faces = make_art.faces_for(make_art.load_config(), "astra")
        n = len(faces)      # 기준 그림 한 장과 표정 n-1장
        code, screen = self.run_tool("--only", "astra", "library")
        self.assertEqual(code, 0, screen)
        log = self.api.log
        self.assertEqual(len(log), n + 1)
        self.assertTrue(all(e["path"].endswith("/accounts/acct123/ai/run/" + make_art.CF_KLEIN) for e in log))
        self.assertTrue(all(e["type"] == "multipart/form-data" for e in log))
        self.assertTrue(all(e["agent"] == make_art.USER_AGENT for e in log))
        # 기준 그림은 글만, 나머지 표정은 기준 그림을 참고로 붙여 보낸다
        self.assertEqual(log[0]["files"], {})
        self.assertIn("Expression:", log[0]["fields"]["prompt"])
        for entry in log[1:n]:
            self.assertEqual(list(entry["files"]), ["input_image_0"])
            self.assertEqual(make_art.sniff_image(entry["files"]["input_image_0"]), "jpg")
            with Image.open(io.BytesIO(entry["files"]["input_image_0"])) as ref:
                self.assertLess(max(ref.size), 512)   # 문서: 참고 그림은 512x512보다 작아야 한다
            self.assertIn("reference image", entry["fields"]["prompt"])
            self.assertEqual(entry["fields"]["seed"], log[0]["fields"]["seed"])
            self.assertEqual((entry["fields"]["width"], entry["fields"]["height"]), ("768", "1152"))
        # 몸짓도 바꾸는 표정(poses)은 몸짓을 함께 적는다
        huff = log[faces.index("huff")]["fields"]["prompt"]
        self.assertIn("New pose: She turns her head further away", huff)
        self.assertIn("New pose:", huff)
        self.assertNotIn("New pose:", log[1]["fields"]["prompt"])
        self.assertEqual(log[n]["files"], {})
        self.assertEqual((log[n]["fields"]["width"], log[n]["fields"]["height"]), ("1280", "720"))

        for face in faces:
            self.assertIsNotNone(make_art.find_raw(self.out, f"astra:{face}"))
            with Image.open(self.out / "sprites" / "astra" / f"{face}.png") as sprite:
                self.assertEqual((sprite.mode, sprite.size), ("RGBA", (768, 1152)))
                self.assertEqual(sprite.getpixel((3, 3))[3], 0)
                self.assertEqual(sprite.getpixel((384, 1148))[3], 255)
        with Image.open(self.out / "bg" / "library.jpg") as scene:
            self.assertEqual(scene.size, (1280, 720))
        self.assertTrue((self.out / "preview.png").is_file())
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest), n + 1)
        self.assertEqual(manifest["astra:smile"]["model"], make_art.CF_KLEIN)
        self.assertNotIn("good-token", json.dumps(manifest))
        self.assertNotIn("good-token", screen)

        # 다시 실행하면 이미 받은 것은 건너뛴다
        code, screen = self.run_tool("--only", "astra", "library")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), n + 1)
        self.assertIn("새로 0장", screen)

        # 한 장만 다시 뽑기
        code, _ = self.run_tool("--only", "astra:pout", "--force", "--seed", "5")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), n + 2)
        self.assertEqual(list(self.api.log[n + 1]["files"]), ["input_image_0"])
        self.assertEqual(int(self.api.log[n + 1]["fields"]["seed"]), int(log[0]["fields"]["seed"]) + 5)

        # 기준 그림만 다시 뽑으면 예전 표정과 어긋난다고 알려 준다
        code, screen = self.run_tool("--only", "astra:neutral", "--force")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), n + 3)
        self.assertIn("--only astra --force", screen)

    def test_variant_alone_makes_the_base_first(self):
        code, _ = self.run_tool("--only", "sora:blush")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), 2)
        self.assertEqual(self.api.log[0]["files"], {})
        self.assertEqual(list(self.api.log[1]["files"]), ["input_image_0"])
        self.assertTrue((self.out / "sprites" / "sora" / "neutral.png").is_file())
        self.assertTrue((self.out / "sprites" / "sora" / "blush.png").is_file())

    def test_rejected_image_is_retried_with_another_seed(self):
        self.api.reject_first = True
        code, _ = self.run_tool("--only", "bg:rooftop")
        self.assertEqual(code, 0)
        first, second = self.api.log
        self.assertEqual(int(second["fields"]["seed"]), int(first["fields"]["seed"]) + 1000)

    def test_wrong_token_stops_at_once(self):
        code, screen = self.run_tool("--only", "astra", env={**GOOD_ENV, "CLOUDFLARE_API_TOKEN": "bad"})
        self.assertEqual(code, 1)
        self.assertEqual(len(self.api.log), 1)
        self.assertIn("CLOUDFLARE_API_TOKEN", screen)
        self.assertNotIn("bad", screen.replace("bad request", ""))

    def test_daily_limit_stops_and_next_run_continues(self):
        self.api.quota_after = 2
        code, screen = self.run_tool("--only", "nova")
        self.assertEqual(code, 1)
        self.assertEqual(len(self.api.log), 3)
        self.assertIn("3036", screen)
        self.assertIn("오전 9시", screen)
        self.api.quota_after = None
        code, _ = self.run_tool("--only", "nova")
        self.assertEqual(code, 0)
        nova = len(make_art.faces_for(make_art.load_config(), "nova"))
        self.assertEqual(len(self.api.log), 3 + nova - 2)   # 앞에서 받은 두 장은 건너뛴다

    def test_timeout_is_tried_again(self):
        self.api.timeout_first = True
        code, screen = self.run_tool("--only", "bg:library")
        self.assertEqual(code, 0, screen)
        first, second = self.api.log
        self.assertEqual(first["fields"]["seed"], second["fields"]["seed"])

    def test_without_pillow_cloudflare_gets_no_reference(self):
        # 참고 그림을 512보다 작게 줄일 수 없으면 큰 그림을 보내지 않고 글만 보낸다
        with mock.patch.object(make_art, "Image", None):
            code, screen = self.run_tool("--only", "sora:neutral", "sora:smile")
        self.assertEqual(code, 0, screen)
        self.assertEqual([entry["files"] for entry in self.api.log], [{}, {}])
        self.assertIn("Expression:", self.api.log[1]["fields"]["prompt"])
        self.assertIn("Pillow", screen)

    def test_schnell_sends_json_without_reference(self):
        code, screen = self.run_tool("--only", "mistral:neutral", "mistral:smile", "--backend", "schnell")
        self.assertEqual(code, 0, screen)
        self.assertEqual(len(self.api.log), 2)
        for entry in self.api.log:
            self.assertTrue(entry["path"].endswith(make_art.CF_SCHNELL))
            self.assertEqual(entry["type"], "application/json")
            self.assertEqual(set(entry["fields"]), {"prompt", "steps", "seed"})
            self.assertEqual(entry["fields"]["steps"], 4)
            self.assertIn("Expression:", entry["fields"]["prompt"])
        self.assertEqual(self.api.log[0]["fields"]["seed"], self.api.log[1]["fields"]["seed"])

    def test_schnell_drops_seed_when_the_schema_is_enforced(self):
        # 문서의 예시는 seed를 보내지만 입력 스키마에는 prompt와 steps뿐이다. 거절되면 seed를 뺀다
        self.api.schnell_refuses_seed = True
        code, screen = self.run_tool("--only", "mistral:neutral", "mistral:smile", "--backend", "schnell")
        self.assertEqual(code, 0, screen)
        self.assertEqual(
            [set(entry["fields"]) for entry in self.api.log],
            [{"prompt", "steps", "seed"}, {"prompt", "steps"}, {"prompt", "steps"}],
        )

    def test_schnell_refuses_a_prompt_that_is_too_long(self):
        backend = make_art.Cloudflare("acct123", "good-token", make_art.CF_SCHNELL)
        with self.assertRaises(make_art.ArtError) as caught:
            backend.generate("a" * 2049, width=768, height=1152, aspect="2:3", seed=1)
        self.assertIn("2048", str(caught.exception))
        self.assertEqual(self.api.log, [])

    def test_gemini(self):
        code, screen = self.run_tool("--only", "gemma:neutral", "gemma:dark", "corridor", "--backend", "gemini")
        self.assertEqual(code, 0, screen)
        docs = [entry["doc"] for entry in self.api.log]
        self.assertEqual(len(docs), 3)
        self.assertEqual([d["model"] for d in docs], [make_art.GEMINI_MODEL] * 3)
        self.assertEqual([d["response_format"]["aspect_ratio"] for d in docs], ["2:3", "2:3", "16:9"])
        self.assertEqual([len(d["input"]) for d in docs], [1, 2, 1])
        self.assertEqual(docs[1]["input"][1]["type"], "image")
        self.assertEqual(docs[1]["input"][1]["mime_type"], "image/jpeg")
        for doc in docs:
            self.assertEqual(doc["input"][0]["type"], "text")
            self.assertEqual(doc["response_format"]["type"], "image")
            self.assertEqual(doc["response_format"]["mime_type"], "image/jpeg")
            self.assertEqual(doc["response_format"]["image_size"], "1K")
        # 생각 단계의 작은 중간 그림이 아니라 결과 그림을 저장한다 (1K의 2:3은 848x1264)
        with Image.open(make_art.find_raw(self.out, "gemma:dark")) as raw:
            self.assertEqual(raw.size, (848, 1264))
        with Image.open(self.out / "sprites" / "gemma" / "dark.png") as sprite:
            self.assertEqual(sprite.size, (768, 1152))
        with Image.open(self.out / "bg" / "corridor.jpg") as scene:
            self.assertEqual(scene.size, (1280, 720))

    def test_gemini_wrong_key_stops_at_once(self):
        code, screen = self.run_tool("--only", "gemma", "--backend", "gemini", env={"GEMINI_API_KEY": "bad"})
        self.assertEqual(code, 1)
        self.assertEqual(len(self.api.log), 1)
        self.assertIn("GEMINI_API_KEY", screen)

    def test_gemini_falls_back_when_format_is_refused(self):
        self.api.gemini_rejects_format = True
        code, _ = self.run_tool("--only", "front_gate", "--backend", "gemini")
        self.assertEqual(code, 0)
        first, second = [entry["doc"] for entry in self.api.log]
        self.assertIn("response_format", first)
        self.assertNotIn("response_format", second)
        self.assertIn("16:9", second["input"][0]["text"])

    def test_auto_uses_gemini_when_only_that_key_exists(self):
        code, _ = self.run_tool("--only", "cafeteria", env={"GEMINI_API_KEY": "good-gemini"})
        self.assertEqual(code, 0)
        self.assertEqual(self.api.log[0]["path"], "/interactions")

    def test_no_keys(self):
        code, screen = self.run_tool("--only", "astra", env={})
        self.assertEqual(code, 2)
        self.assertEqual(self.api.log, [])
        self.assertIn("CLOUDFLARE_API_TOKEN", screen)

    def test_dry_run_and_list_need_no_keys(self):
        code, screen = self.run_tool("--dry-run", env={})
        self.assertEqual(code, 0)
        cfg = make_art.load_config()
        self.assertIn(f"모두 {len(make_art.all_keys(cfg))}장", screen)
        code, screen = self.run_tool("--list", env={})
        self.assertEqual(code, 0)
        self.assertIn("astra", screen)
        self.assertEqual(self.api.log, [])
        self.assertFalse(self.out.exists())

    def test_recut_uses_saved_images_only(self):
        self.run_tool("--only", "haiku:neutral")
        sprite = self.out / "sprites" / "haiku" / "neutral.png"
        sprite.unlink()
        (self.out / "preview.png").unlink()
        code, _ = self.run_tool("--recut", env={})
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), 1)
        self.assertTrue(sprite.is_file())
        self.assertTrue((self.out / "preview.png").is_file())

    def test_unknown_name(self):
        code, screen = self.run_tool("--only", "nobody")
        self.assertEqual(code, 2)
        self.assertIn("모르는 이름", screen)


if __name__ == "__main__":
    unittest.main()

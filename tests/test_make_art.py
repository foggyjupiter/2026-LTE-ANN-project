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


class FakeApi(http.server.ThreadingHTTPServer):
    """Cloudflare와 Gemini 흉내. 받은 요청을 log에 적어 둔다."""

    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), FakeHandler)
        self.log = []
        self.reject_first = False     # 첫 요청을 3030(결과 그림 걸러짐)으로 돌려보낸다
        self.quota_after = None       # 이만큼 만든 뒤로는 하루 한도 오류를 낸다
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
        self._send(status, {"success": False, "errors": [{"code": code, "message": message}], "result": None})

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
            return self._cf_error(429, 4006, "you have used up your daily free allocation of 10,000 neurons")
        if server.reject_first and len(server.log) == 1:
            return self._cf_error(400, 3030, "Output image was rejected")
        fields = entry["fields"]
        as_jpeg = server.served % 2 == 1
        data = render(fields["prompt"], int(fields.get("width", 1024)), int(fields.get("height", 1024)), as_jpeg)
        server.served += 1
        if as_jpeg:   # 그림 바이트를 그대로 주는 경우
            return self._send(200, data, "image/jpeg")
        self._send(200, {"success": True, "errors": [], "result": {"image": base64.b64encode(data).decode()}})

    def _gemini(self, body):
        server = self.server
        doc = json.loads(body)
        server.log.append({"path": self.path, "doc": doc})
        if self.headers.get("x-goog-api-key") != "good-gemini":
            return self._send(403, {"error": {"code": 403, "message": "API key not valid"}})
        if server.gemini_rejects_format and "response_format" in doc:
            return self._send(400, {"error": {"code": 400, "message": "Unknown field response_format"}})
        aspect = doc.get("response_format", {}).get("aspect_ratio", "1:1")
        width, height = (512, 768) if aspect == "2:3" else (1024, 576)
        data = render(doc["input"][0]["text"], width, height, True)
        server.served += 1
        self._send(200, {
            "id": "abc", "status": "completed",
            "steps": [{"type": "model_output", "content": [
                {"type": "text", "text": "done"},
                {"type": "image", "mime_type": "image/jpeg", "data": base64.b64encode(data).decode()},
            ]}],
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
        wrapped = json.dumps({"success": True, "result": {"image": base64.b64encode(TINY_PNG).decode()}})
        self.assertEqual(make_art.decode_cloudflare(200, wrapped.encode()), TINY_PNG)
        self.assertEqual(make_art.decode_cloudflare(200, TINY_PNG), TINY_PNG)

    def _cf_error(self, status, code, message):
        body = json.dumps({"success": False, "errors": [{"code": code, "message": message}]}).encode()
        with self.assertRaises(make_art.ArtError) as caught:
            make_art.decode_cloudflare(status, body)
        return caught.exception

    def test_cloudflare_errors_are_sorted(self):
        auth = self._cf_error(401, 10000, "Authentication error")
        self.assertTrue(auth.stop)
        self.assertIn("CLOUDFLARE_API_TOKEN", str(auth))
        self.assertTrue(self._cf_error(429, 4006, "daily free allocation of 10,000 neurons").stop)
        self.assertTrue(self._cf_error(400, 3030, "Output image was rejected").reroll)
        busy = self._cf_error(429, 3040, "Capacity temporarily exceeded")
        self.assertTrue(busy.retry and busy.quota and not busy.stop)
        self.assertTrue(self._cf_error(503, 3007, "upstream timeout").retry)
        plain = self._cf_error(400, 5006, "width must be >= 256")
        self.assertFalse(plain.stop or plain.retry or plain.reroll)
        self.assertIn("width must be", str(plain))

    def test_cloudflare_garbage_answer(self):
        with self.assertRaises(make_art.ArtError):
            make_art.decode_cloudflare(200, b"<html>oops</html>")
        with self.assertRaises(make_art.ArtError):
            make_art.decode_cloudflare(200, json.dumps({"success": True, "result": {}}).encode())

    def test_gemini_answer(self):
        doc = {"steps": [{"content": [
            {"type": "image", "data": base64.b64encode(b"\xff\xd8\xff-first").decode()},
            {"type": "image", "data": base64.b64encode(TINY_PNG).decode()},
        ]}]}
        self.assertEqual(make_art.decode_gemini(200, json.dumps(doc).encode()), TINY_PNG)
        with self.assertRaises(make_art.ArtError) as caught:
            make_art.decode_gemini(200, json.dumps({"steps": [{"content": [{"type": "text", "text": "no"}]}]}).encode())
        self.assertTrue(caught.exception.reroll)
        with self.assertRaises(make_art.ArtError) as caught:
            make_art.decode_gemini(403, json.dumps({"error": {"message": "API key not valid"}}).encode())
        self.assertTrue(caught.exception.stop)
        with self.assertRaises(make_art.ArtError) as caught:
            make_art.decode_gemini(429, json.dumps({"error": {"message": "quota exceeded, limit: 0"}}).encode())
        self.assertTrue(caught.exception.quota)

    def test_only_names(self):
        everything = make_art.all_keys(self.cfg)
        self.assertEqual(len(everything), 6 * 6 + 8)
        self.assertEqual(make_art.parse_only([], self.cfg), everything)
        self.assertEqual(
            make_art.parse_only(["giulhee"], self.cfg), [f"giulhee:{face}" for face in make_art.FACES]
        )
        self.assertEqual(
            make_art.parse_only(["library,anna:smile", "bg:rooftop"], self.cfg),
            ["anna:smile", "bg:library", "bg:rooftop"],
        )
        self.assertEqual(len(make_art.parse_only(["bg"], self.cfg)), 8)
        self.assertEqual(len(make_art.parse_only(["sprites"], self.cfg)), 36)
        with self.assertRaises(ValueError) as caught:
            make_art.parse_only(["giulhe"], self.cfg)
        self.assertIn("giulhee", str(caught.exception))

    def test_faces_match_the_engine(self):
        from sogaeting import actor, content
        self.assertEqual(make_art.FACES, actor.FACES)
        self.assertEqual(sorted(self.cfg["characters"]), sorted(content.list_character_ids()))
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
        smile = make_art.sprite_prompt(self.cfg, "boxhyun", "smile", variant=True)
        self.assertIn("deadpan", smile)   # 캐릭터가 따로 정한 표정이 공통 표정보다 먼저다

    def test_seed_is_stable(self):
        self.assertEqual(make_art.seed_for("giulhee"), make_art.seed_for("giulhee"))
        self.assertNotEqual(make_art.seed_for("giulhee"), make_art.seed_for("anna"))
        self.assertEqual(make_art.seed_for("giulhee", 3), make_art.seed_for("giulhee") + 3)

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
        code, screen = self.run_tool("--only", "giulhee", "library")
        self.assertEqual(code, 0, screen)
        log = self.api.log
        self.assertEqual(len(log), 7)
        self.assertTrue(all(e["path"].endswith("/accounts/acct123/ai/run/" + make_art.CF_KLEIN) for e in log))
        self.assertTrue(all(e["type"] == "multipart/form-data" for e in log))
        self.assertTrue(all(e["agent"] == make_art.USER_AGENT for e in log))
        # 기준 그림은 글만, 표정 다섯 장은 기준 그림을 참고로 붙여 보낸다
        self.assertEqual(log[0]["files"], {})
        self.assertIn("Expression:", log[0]["fields"]["prompt"])
        for entry in log[1:6]:
            self.assertEqual(list(entry["files"]), ["input_image_0"])
            self.assertEqual(make_art.sniff_image(entry["files"]["input_image_0"]), "jpg")
            with Image.open(io.BytesIO(entry["files"]["input_image_0"])) as ref:
                self.assertLessEqual(max(ref.size), 512)
            self.assertIn("reference image", entry["fields"]["prompt"])
            self.assertEqual(entry["fields"]["seed"], log[0]["fields"]["seed"])
            self.assertEqual((entry["fields"]["width"], entry["fields"]["height"]), ("768", "1152"))
        self.assertEqual(log[6]["files"], {})
        self.assertEqual((log[6]["fields"]["width"], log[6]["fields"]["height"]), ("1280", "720"))

        for face in make_art.FACES:
            self.assertIsNotNone(make_art.find_raw(self.out, f"giulhee:{face}"))
            with Image.open(self.out / "sprites" / "giulhee" / f"{face}.png") as sprite:
                self.assertEqual((sprite.mode, sprite.size), ("RGBA", (768, 1152)))
                self.assertEqual(sprite.getpixel((3, 3))[3], 0)
                self.assertEqual(sprite.getpixel((384, 1148))[3], 255)
        with Image.open(self.out / "bg" / "library.jpg") as scene:
            self.assertEqual(scene.size, (1280, 720))
        self.assertTrue((self.out / "preview.png").is_file())
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest), 7)
        self.assertEqual(manifest["giulhee:smile"]["model"], make_art.CF_KLEIN)
        self.assertNotIn("good-token", json.dumps(manifest))
        self.assertNotIn("good-token", screen)

        # 다시 실행하면 이미 받은 것은 건너뛴다
        code, screen = self.run_tool("--only", "giulhee", "library")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), 7)
        self.assertIn("새로 0장", screen)

        # 한 장만 다시 뽑기
        code, _ = self.run_tool("--only", "giulhee:pout", "--force", "--seed", "5")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), 8)
        self.assertEqual(list(self.api.log[7]["files"]), ["input_image_0"])
        self.assertEqual(int(self.api.log[7]["fields"]["seed"]), int(log[0]["fields"]["seed"]) + 5)

        # 기준 그림만 다시 뽑으면 예전 표정과 어긋난다고 알려 준다
        code, screen = self.run_tool("--only", "giulhee:neutral", "--force")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), 9)
        self.assertIn("--only giulhee --force", screen)

    def test_variant_alone_makes_the_base_first(self):
        code, _ = self.run_tool("--only", "anna:blush")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), 2)
        self.assertEqual(self.api.log[0]["files"], {})
        self.assertEqual(list(self.api.log[1]["files"]), ["input_image_0"])
        self.assertTrue((self.out / "sprites" / "anna" / "neutral.png").is_file())
        self.assertTrue((self.out / "sprites" / "anna" / "blush.png").is_file())

    def test_rejected_image_is_retried_with_another_seed(self):
        self.api.reject_first = True
        code, _ = self.run_tool("--only", "bg:rooftop")
        self.assertEqual(code, 0)
        first, second = self.api.log
        self.assertEqual(int(second["fields"]["seed"]), int(first["fields"]["seed"]) + 1000)

    def test_wrong_token_stops_at_once(self):
        code, screen = self.run_tool("--only", "giulhee", env={**GOOD_ENV, "CLOUDFLARE_API_TOKEN": "bad"})
        self.assertEqual(code, 1)
        self.assertEqual(len(self.api.log), 1)
        self.assertIn("CLOUDFLARE_API_TOKEN", screen)
        self.assertNotIn("bad", screen.replace("bad request", ""))

    def test_daily_limit_stops_and_next_run_continues(self):
        self.api.quota_after = 2
        code, screen = self.run_tool("--only", "relu")
        self.assertEqual(code, 1)
        self.assertEqual(len(self.api.log), 3)
        self.assertIn("내일", screen)
        self.api.quota_after = None
        code, _ = self.run_tool("--only", "relu")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.api.log), 3 + 4)

    def test_schnell_sends_json_without_reference(self):
        code, screen = self.run_tool("--only", "haru:neutral", "haru:smile", "--backend", "schnell")
        self.assertEqual(code, 0, screen)
        self.assertEqual(len(self.api.log), 2)
        for entry in self.api.log:
            self.assertTrue(entry["path"].endswith(make_art.CF_SCHNELL))
            self.assertEqual(entry["type"], "application/json")
            self.assertEqual(set(entry["fields"]), {"prompt", "steps", "seed"})
            self.assertIn("Expression:", entry["fields"]["prompt"])
        self.assertEqual(self.api.log[0]["fields"]["seed"], self.api.log[1]["fields"]["seed"])

    def test_gemini(self):
        code, screen = self.run_tool("--only", "oeun:neutral", "oeun:dark", "corridor", "--backend", "gemini")
        self.assertEqual(code, 0, screen)
        docs = [entry["doc"] for entry in self.api.log]
        self.assertEqual(len(docs), 3)
        self.assertEqual([d["model"] for d in docs], [make_art.GEMINI_MODEL] * 3)
        self.assertEqual([d["response_format"]["aspect_ratio"] for d in docs], ["2:3", "2:3", "16:9"])
        self.assertEqual([len(d["input"]) for d in docs], [1, 2, 1])
        self.assertEqual(docs[1]["input"][1]["type"], "image")
        self.assertEqual(docs[1]["input"][1]["mime_type"], "image/jpeg")
        with Image.open(self.out / "sprites" / "oeun" / "dark.png") as sprite:
            self.assertEqual(sprite.size, (768, 1152))

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
        code, screen = self.run_tool("--only", "giulhee", env={})
        self.assertEqual(code, 2)
        self.assertEqual(self.api.log, [])
        self.assertIn("CLOUDFLARE_API_TOKEN", screen)

    def test_dry_run_and_list_need_no_keys(self):
        code, screen = self.run_tool("--dry-run", env={})
        self.assertEqual(code, 0)
        self.assertIn("모두 44장", screen)
        code, screen = self.run_tool("--list", env={})
        self.assertEqual(code, 0)
        self.assertIn("giulhee", screen)
        self.assertEqual(self.api.log, [])
        self.assertFalse(self.out.exists())

    def test_recut_uses_saved_images_only(self):
        self.run_tool("--only", "boxhyun:neutral")
        sprite = self.out / "sprites" / "boxhyun" / "neutral.png"
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

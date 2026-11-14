#!/usr/bin/env python3
"""소개팅 그림(캐릭터 표정, 배경)을 한꺼번에 뽑는 스크립트.

    python tools/make_art.py --only astra     한 명만 먼저 뽑아 본다
    python tools/make_art.py                    없는 그림을 전부 뽑는다
    python tools/make_art.py --dry-run          요청문만 보여 주고 끝낸다

키는 레포 맨 위의 .env 파일에서 읽는다. 자세한 설명은 tools/README.md.
요청문은 tools/art_prompts.json에 있다. 그림이 마음에 안 들면 그 파일만 고친다.

순서: 캐릭터마다 기준 그림(neutral) 한 장 → 그 그림을 참고로 표정 다섯 장 → 배경.
받은 그림은 art/raw/에 그대로 두고, 단색 배경을 지운 것을 art/sprites/에 따로 만든다.
이미 받은 그림은 건너뛰므로 중간에 끊겨도 같은 명령을 다시 실행하면 이어진다.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import http.client
import io
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

try:  # 배경 지우기와 미리보기에만 쓴다. 없으면 받은 그림만 저장한다.
    from PIL import Image, ImageChops, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - 설치 여부에 따라 갈린다
    Image = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
GPT_DOC_PATH = ROOT / "docs" / "art-prompts-gpt.md"
PROMPTS_PATH = pathlib.Path(__file__).resolve().with_name("art_prompts.json")

CF_BASE = "https://api.cloudflare.com/client/v4"
CF_KLEIN = "@cf/black-forest-labs/flux-2-klein-4b"
CF_SCHNELL = "@cf/black-forest-labs/flux-1-schnell"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-nano-banana-2.1"

FACES = ("neutral", "smile", "blush", "pout", "shock", "dark")
BASE_FACE = "neutral"
# 캐릭터만의 표정 이름(characters.<이름>.faces 에서 FACES 밖의 것). 게임의 캐릭터 설정 extra_faces 와 같은 이름이다
EXTRA_FACE_RE = re.compile(r"[a-z][a-z_]{1,23}")
RAW_EXTS = ("png", "jpg", "webp")
TIMEOUT_SEC = 180
RETRY_WAITS = (5, 20, 60)   # 잠깐 생긴 문제일 때 기다렸다 다시 해 보는 간격(초)
MAX_REROLLS = 2             # 그림이 걸러졌을 때 씨앗을 바꿔 다시 해 보는 횟수
PAUSE_SEC = 0.5             # 요청 사이에 쉬는 시간
USER_AGENT = "lte-ann-make-art/1.0"

_sleep = time.sleep


class ArtError(Exception):
    """그림 한 장을 만들지 못했다.

    stop   : 남은 것도 전부 안 될 문제(키 오류, 하루 한도)라 실행을 멈춘다.
    retry  : 잠깐 기다리면 풀릴 수 있다.
    reroll : 씨앗을 바꾸면 될 수 있다(결과 그림이 걸러진 경우).
    quota  : 요청이 너무 많다는 응답. 기다려도 안 풀리면 멈춘다.
    """

    def __init__(self, message, *, stop=False, retry=False, reroll=False, quota=False):
        super().__init__(message)
        self.stop = stop
        self.retry = retry
        self.reroll = reroll
        self.quota = quota


# ---------------------------------------------------------------- 공통 도구

def say(text="", end="\n"):
    print(text, end=end, flush=True)


def load_dotenv(path):
    """KEY=값 줄을 환경 변수로 읽는다. 이미 있는 값은 건드리지 않는다."""
    path = pathlib.Path(path)
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


def load_config(path=PROMPTS_PATH):
    cfg = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    for face in FACES:
        if face not in cfg["faces"]:
            raise ValueError(f"art_prompts.json의 faces에 {face}가 없습니다")
    for char_id, char in cfg["characters"].items():
        if char.get("key") not in ("green", "magenta"):
            raise ValueError(f"{char_id}의 key는 green이나 magenta여야 합니다")
        for face in char.get("faces", {}):
            if face not in FACES and not EXTRA_FACE_RE.fullmatch(face):
                raise ValueError(f"{char_id}의 표정 이름 {face}: 영문 소문자와 밑줄로 짓습니다")
        for face in char.get("poses", {}):
            if face not in faces_for(cfg, char_id) or face == BASE_FACE:
                raise ValueError(f"{char_id}의 poses에 있는 {face}는 그 캐릭터의 표정이 아닙니다")
    return cfg


def faces_for(cfg, char_id):
    """그 캐릭터의 표정: 기본 여섯 가지와 캐릭터만의 표정."""
    extra = [face for face in cfg["characters"][char_id].get("faces", {}) if face not in FACES]
    return FACES + tuple(extra)


def sniff_image(data):
    """앞머리 바이트로 그림 형식을 알아낸다. 그림이 아니면 None."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


MIME = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def encode_multipart(fields, files=()):
    """multipart/form-data 본문을 직접 만든다. (본문, Content-Type 값)을 돌려준다."""
    boundary = "----makeart" + uuid.uuid4().hex
    out = []
    for name, value in fields.items():
        out.append(f"--{boundary}\r\n".encode())
        out.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        out.append(str(value).encode("utf-8"))
        out.append(b"\r\n")
    for name, filename, mime, data in files:
        out.append(f"--{boundary}\r\n".encode())
        out.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        out.append(f"Content-Type: {mime}\r\n\r\n".encode())
        out.append(data)
        out.append(b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def http_post(url, headers, body):
    """POST 한 번. (상태 코드, 본문 바이트)를 돌려준다. 연결이 안 되면 ArtError."""
    headers = {"User-Agent": USER_AGENT, **headers}
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SEC) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()
    except (urllib.error.URLError, http.client.HTTPException, OSError) as err:
        reason = getattr(err, "reason", err)
        raise ArtError(f"연결 실패: {reason}", retry=True) from None


def _snippet(body, limit=300):
    return body[:limit].decode("utf-8", "replace").replace("\n", " ")


def _parse_json(status, body):
    try:
        doc = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ArtError(
            f"읽을 수 없는 응답 (HTTP {status}): {_snippet(body)}", retry=status >= 500
        ) from None
    if not isinstance(doc, dict):
        raise ArtError(f"읽을 수 없는 응답 (HTTP {status}): {_snippet(body)}")
    return doc


def _decode_base64_image(text, status):
    try:
        data = base64.b64decode(text, validate=False)
    except ValueError:
        data = b""
    if not sniff_image(data):
        raise ArtError(f"응답에 그림이 들어 있지 않습니다 (HTTP {status})")
    return data


# ---------------------------------------------------------------- Cloudflare

# 오류 번호는 developers.cloudflare.com/workers-ai/platform/errors/ 의 표에서 가져왔다.
CF_DAILY_LIMIT = 3036                        # 하루 무료 한도(10,000 뉴런)를 다 씀. HTTP 429
CF_BAD_MODEL = (5007, 3042, 5028)            # 없는 모델, 잘못된 모델 이름, 없어진 모델
CF_NOT_THE_TOKEN = (3023, 3041, 5016, 5018, 5035)   # 403이지만 계정이나 모델 쪽 사정
CF_REJECTED = 3030   # 그림이 걸러졌을 때의 번호라고 알려져 있으나 공식 표에는 없다
CF_SCHNELL_PROMPT_MAX = 2048                 # schnell 입력 스키마의 prompt maxLength


def decode_cloudflare(status, body):
    """Workers AI 응답에서 그림 바이트를 꺼낸다.

    FLUX 계열은 {"result": {"image": "base64..."}, "success": true, ...} 모양으로 준다.
    옛 모델처럼 그림 바이트가 그대로 와도 받는다.
    """
    if status < 400 and sniff_image(body):
        return body
    doc = _parse_json(status, body)
    errors = doc.get("errors") or []
    if status >= 400 or doc.get("success") is False or errors:
        first = errors[0] if errors and isinstance(errors[0], dict) else {}
        code = first.get("code")
        message = str(first.get("message") or _snippet(body))
        text = f"HTTP {status}, 코드 {code}: {message}"
        low = message.lower()
        if code in CF_NOT_THE_TOKEN:
            raise ArtError(text, stop=True)
        if status in (401, 403) or code == 10000:
            raise ArtError(
                text + "\n  → .env의 CLOUDFLARE_ACCOUNT_ID와 CLOUDFLARE_API_TOKEN을 확인하세요. "
                "토큰에는 Workers AI 권한이 있어야 합니다.",
                stop=True,
            )
        if code == CF_DAILY_LIMIT or "neuron" in low or "allocation" in low or "daily" in low:
            raise ArtError(
                text + "\n  → 하루 무료 한도(10,000 뉴런)를 다 썼습니다. "
                "한도는 매일 00:00 UTC(한국 시간 오전 9시)에 다시 찹니다. "
                "그 뒤에 같은 명령을 다시 실행하면 남은 것부터 이어집니다.",
                stop=True,
            )
        if code in CF_BAD_MODEL or status in (404, 410):
            raise ArtError(
                text + "\n  → CLOUDFLARE_ACCOUNT_ID와 모델 이름(--model)을 확인하세요.", stop=True
            )
        if code == CF_REJECTED or "rejected" in low or "flagged" in low or "nsfw" in low:
            raise ArtError(text, reroll=True)
        if status == 429:
            raise ArtError(text, retry=True, quota=True)
        raise ArtError(text, retry=status == 408 or status >= 500)
    result = doc.get("result", doc)
    image = result.get("image") if isinstance(result, dict) else None
    if not isinstance(image, str):
        raise ArtError(f"응답에 그림이 들어 있지 않습니다 (HTTP {status}): {_snippet(body)}")
    return _decode_base64_image(image, status)


class Cloudflare:
    name = "cloudflare"
    # 문서: "All input images must be smaller than 512x512." 512도 되는지는 적혀 있지 않아서 511로 둔다.
    ref_max_side = 511
    max_refs = 4   # 문서: "supports up to 4 image inputs"

    def __init__(self, account, token, model=CF_KLEIN):
        self.account = account
        self.token = token
        self.model = model
        self.send_seed = True

    @property
    def uses_reference(self):
        return "flux-2" in self.model

    def generate(self, prompt, *, width, height, aspect, seed, refs=()):
        url = f"{CF_BASE}/accounts/{self.account}/ai/run/{self.model}"
        headers = {"Authorization": f"Bearer {self.token}"}
        if self.uses_reference:
            # FLUX.2 계열은 글만 보낼 때도 multipart로 보내야 한다. 크기는 256에서 1920까지.
            # klein은 4단계로 고정이라 steps는 보내지 않는다.
            fields = {"prompt": prompt, "width": width, "height": height, "seed": seed}
            files = [
                (f"input_image_{i}", f"ref{i}.{ext}", MIME[ext], data)
                for i, (ext, data) in enumerate(refs[:self.max_refs])
            ]
            body, content_type = encode_multipart(fields, files)
            status, raw = http_post(url, {**headers, "Content-Type": content_type}, body)
            return decode_cloudflare(status, raw)

        # schnell의 입력 스키마에는 prompt와 steps뿐이다. 크기도 참고 그림도 받지 않는다.
        if len(prompt) > CF_SCHNELL_PROMPT_MAX:
            raise ArtError(
                f"요청문이 {len(prompt)}자입니다. 이 모델은 {CF_SCHNELL_PROMPT_MAX}자까지만 받습니다."
            )
        headers["Content-Type"] = "application/json"
        payload = {"prompt": prompt, "steps": 4}
        if self.send_seed:
            payload["seed"] = seed
        status, raw = http_post(url, headers, json.dumps(payload).encode("utf-8"))
        if status == 400 and "seed" in payload:
            # 문서의 예시는 seed를 보내는데 입력 스키마에는 seed가 없다(additionalProperties: false).
            # seed 때문에 거절됐을 수 있으니 빼고 한 번 더 보낸다.
            first_raw = raw
            payload.pop("seed")
            status, raw = http_post(url, headers, json.dumps(payload).encode("utf-8"))
            if status == 400:
                return decode_cloudflare(400, first_raw)
            if status < 400:
                self.send_seed = False
        return decode_cloudflare(status, raw)


# ---------------------------------------------------------------- Gemini

def find_images(node):
    """응답 어디에 있든 type이 image인 덩어리의 data를 순서대로 모은다."""
    found = []
    if isinstance(node, dict):
        if node.get("type") == "image" and isinstance(node.get("data"), str):
            found.append(node["data"])
        for value in node.values():
            found.extend(find_images(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(find_images(value))
    return found


# 그림이 걸러졌거나 만들어지지 않았다는 오류 코드. ai.google.dev/gemini-api/docs/api-errors 의 표.
GEMINI_BLOCKED = frozenset({
    "safety", "recitation", "language", "prohibited_content", "spii", "blocklist",
    "image_safety", "image_prohibited_content", "image_recitation", "image_other",
    "content_blocked", "no_image",
})


def _gemini_error(doc):
    """오류 응답 {"error": {"code": "snake_case", "message": "..."}}에서 (코드, 문장)을 꺼낸다."""
    error = doc.get("error") if isinstance(doc, dict) else None
    if not isinstance(error, dict):
        return None, None
    return error.get("code"), error.get("message")


def _gemini_format_refused(raw):
    """HTTP 400이 형식 지정 탓일 수 있는지. 그림이 걸러졌거나 결제 문제라면 아니다."""
    try:
        code, _ = _gemini_error(json.loads(raw))
    except ValueError:
        return True
    return code != "failed_precondition" and code not in GEMINI_BLOCKED


def gemini_images(doc):
    """결과 단계(model_output)의 그림을 먼저 찾는다. 생각 단계(thought)에는 중간 그림이 섞여 있다."""
    steps = doc.get("steps")
    outputs = [
        step for step in steps if isinstance(step, dict) and step.get("type") == "model_output"
    ] if isinstance(steps, list) else []
    return find_images(outputs) or find_images(doc)


def decode_gemini(status, body):
    doc = _parse_json(status, body)
    code, message = _gemini_error(doc)
    if status >= 400 or doc.get("error"):
        text = f"HTTP {status}, 코드 {code}: {message or _snippet(body)}"
        if status in (401, 403) or code in ("authentication", "permission_denied"):
            raise ArtError(
                text + "\n  → .env의 GEMINI_API_KEY를 확인하세요. "
                "그림 모델은 결제가 연결된 프로젝트의 키만 쓸 수 있습니다.",
                stop=True,
            )
        if status == 402 or code in ("payment_required", "failed_precondition"):
            raise ArtError(
                text + "\n  → 결제 설정과 선불 잔액을 확인하세요. Gemini 그림 모델은 무료 한도가 없습니다.",
                stop=True,
            )
        if status == 404:
            raise ArtError(text + "\n  → 모델 이름(--model)을 확인하세요.", stop=True)
        if status == 429:
            raise ArtError(
                text + "\n  → Gemini 그림 모델은 무료 한도가 없습니다. "
                "결제가 연결된 키인지 확인하세요.",
                retry=True, quota=True,
            )
        if code in GEMINI_BLOCKED:
            raise ArtError(text, reroll=True)
        raise ArtError(text, retry=status == 408 or status >= 500)
    images = gemini_images(doc)
    if not images:
        raise ArtError("그림 없이 답이 왔습니다 (걸러졌을 수 있음)", reroll=True)
    return _decode_base64_image(images[-1], status)


class Gemini:
    name = "gemini"
    uses_reference = True
    ref_max_side = None   # 참고 그림 크기 한도가 문서에 없다

    def __init__(self, key, model=GEMINI_MODEL):
        self.key = key
        self.model = model

    def generate(self, prompt, *, width, height, aspect, seed, refs=()):
        url = f"{GEMINI_BASE}/interactions"
        headers = {"x-goog-api-key": self.key, "Content-Type": "application/json"}
        parts = [{"type": "text", "text": prompt}]
        for ext, data in refs[:4]:
            parts.append({
                "type": "image",
                "mime_type": MIME[ext],
                "data": base64.b64encode(data).decode("ascii"),
            })
        # Interactions API. response_format의 mime_type은 image/jpeg 하나뿐이다.
        # 1K로 받으면 2:3은 848x1264, 16:9는 1376x768로 온다. 게임에 쓸 크기로는 나중에 맞춘다.
        payload = {
            "model": self.model,
            "input": parts,
            "response_format": {
                "type": "image",
                "mime_type": "image/jpeg",
                "aspect_ratio": aspect,
                "image_size": "1K",
            },
        }
        status, raw = http_post(url, headers, json.dumps(payload).encode("utf-8"))
        if status == 400 and _gemini_format_refused(raw):
            # 형식 지정을 못 알아듣는 모델일 수 있다. 빼고 한 번 더 보낸다.
            first_raw = raw
            payload.pop("response_format")
            payload["input"][0]["text"] = f"{prompt} Image aspect ratio {aspect}."
            status, raw = http_post(url, headers, json.dumps(payload).encode("utf-8"))
            if status == 400:
                return decode_gemini(400, first_raw)
        return decode_gemini(status, raw)


def pick_backend(name, model=None):
    """쓸 곳을 고른다. auto면 키가 있는 쪽을 쓴다(Cloudflare 먼저)."""
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if name == "auto":
        if account and token:
            name = "cloudflare"
        elif gemini_key:
            name = "gemini"
        else:
            raise ArtError(
                "키가 없습니다. 레포 맨 위의 .env 파일에 아래 두 줄을 적어 주세요.\n"
                "  CLOUDFLARE_ACCOUNT_ID=...\n"
                "  CLOUDFLARE_API_TOKEN=...\n"
                "받는 방법은 tools/README.md에 있습니다.",
                stop=True,
            )
    if name in ("cloudflare", "schnell"):
        if not (account and token):
            raise ArtError(
                ".env에 CLOUDFLARE_ACCOUNT_ID와 CLOUDFLARE_API_TOKEN이 필요합니다.", stop=True
            )
        default = CF_SCHNELL if name == "schnell" else CF_KLEIN
        return Cloudflare(account, token, model or default)
    if name == "gemini":
        if not gemini_key:
            raise ArtError(".env에 GEMINI_API_KEY가 필요합니다.", stop=True)
        return Gemini(gemini_key, model or GEMINI_MODEL)
    raise ArtError(f"모르는 backend: {name}", stop=True)


def generate(backend, prompt, *, seed, **kwargs):
    """다시 시도까지 포함해 그림 한 장을 받는다. (바이트, 실제로 쓴 씨앗)을 돌려준다."""
    waits = list(RETRY_WAITS)
    rerolls = 0
    while True:
        try:
            return backend.generate(prompt, seed=seed, **kwargs), seed
        except ArtError as err:
            if err.stop:
                raise
            if err.reroll and rerolls < MAX_REROLLS:
                rerolls += 1
                seed += 1000
                continue
            if err.retry and waits:
                _sleep(waits.pop(0))
                continue
            if err.quota:
                err.stop = True
            raise


# ---------------------------------------------------------------- 할 일 목록

def all_keys(cfg):
    keys = [f"{char}:{face}" for char in cfg["characters"] for face in faces_for(cfg, char)]
    keys += [f"bg:{place}" for place in cfg["backgrounds"]]
    return keys


def parse_only(tokens, cfg):
    """--only에 적은 이름을 그림 열쇠 목록으로 바꾼다.

    astra          그 캐릭터의 표정 전부 (기본 여섯 장과 캐릭터만의 표정)
    astra:smile    그 한 장
    sprites          캐릭터 전부
    bg               배경 전부
    library, bg:library   그 배경 한 장
    """
    everything = all_keys(cfg)
    if not tokens:
        return everything
    chosen = []
    for token in (t for chunk in tokens for t in chunk.split(",")):
        token = token.strip()
        if not token:
            continue
        if token == "sprites":
            picked = [k for k in everything if not k.startswith("bg:")]
        elif token == "bg":
            picked = [k for k in everything if k.startswith("bg:")]
        elif token in cfg["characters"]:
            picked = [f"{token}:{face}" for face in faces_for(cfg, token)]
        elif token in cfg["backgrounds"]:
            picked = [f"bg:{token}"]
        elif token in everything:
            picked = [token]
        else:
            names = ", ".join([*cfg["characters"], "sprites", "bg", *cfg["backgrounds"]])
            faces = ", ".join(FACES)
            raise ValueError(
                f"모르는 이름: {token}\n  쓸 수 있는 이름: {names}\n"
                f"  표정 한 장만: 캐릭터:표정 (표정: {faces}, 그리고 캐릭터만의 표정)"
            )
        chosen.extend(k for k in picked if k not in chosen)
    return [k for k in everything if k in chosen]


def split_key(key):
    left, _, right = key.partition(":")
    return left, right


def is_bg(key):
    return key.startswith("bg:")


def raw_stem(out, key):
    left, right = split_key(key)
    return pathlib.Path(out) / "raw" / left / right


# 2026-11-13에 바꾸기 전의 캐릭터 id. 받은 그림을 예전 폴더 이름(art/raw/giulhee)에 넣어도 찾는다
OLD_IDS = {"astra": "giulhee", "gemma": "oeun", "sora": "anna", "nova": "relu", "mistral": "haru", "haiku": "boxhyun"}


def find_raw(out, key):
    stem = raw_stem(out, key)
    stems = [stem]
    left, right = split_key(key)
    if left in OLD_IDS:
        stems.append(pathlib.Path(out) / "raw" / OLD_IDS[left] / right)
    for candidate in stems:
        for ext in RAW_EXTS:
            path = candidate.with_name(f"{candidate.name}.{ext}")
            if path.is_file():
                return path
    return None


def final_path(out, key):
    left, right = split_key(key)
    if is_bg(key):
        return pathlib.Path(out) / "bg" / f"{right}.jpg"
    return pathlib.Path(out) / "sprites" / left / f"{right}.png"


def seed_for(name, offset=0):
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 1_000_000_000 + offset


def variant_text(cfg, char_id, face):
    """기준 그림에서 표정을 바꾸라는 말. 몸짓도 바꾸는 표정(poses)이면 몸짓도 적는다."""
    char = cfg["characters"][char_id]
    expression = char.get("faces", {}).get(face) or cfg["faces"][face]
    pose = char.get("poses", {}).get(face)
    if pose:
        return f"{cfg['sprite']['variant_pose']} New expression: {expression}. New pose: {pose}"
    return f"{cfg['sprite']['variant']} New expression: {expression}."


def sprite_prompt(cfg, char_id, face, *, variant=False):
    sprite = cfg["sprite"]
    char = cfg["characters"][char_id]
    expression = char.get("faces", {}).get(face) or cfg["faces"][face]
    key_words = cfg["keys"][char["key"]]["words"]
    parts = []
    if variant:
        parts.append(variant_text(cfg, char_id, face))
    parts += [sprite["style"], sprite["framing"], sprite["safety"], char["look"], sprite["uniform"]]
    if not variant:
        parts.append(f"Expression: {expression}.")
    parts.append(sprite["background"].format(key=key_words))
    return " ".join(parts)


def gpt_sprite_prompt(cfg, char_id):
    """ChatGPT 같은 대화형 도구에 붙여 넣을 기준 그림(neutral) 요청문."""
    sprite = cfg["sprite"]
    char = cfg["characters"][char_id]
    expression = char.get("faces", {}).get("neutral") or cfg["faces"]["neutral"]
    key_words = cfg["keys"][char["key"]]["words"]
    return "\n".join([
        "Draw one character sprite for a visual novel game.",
        f"Art style: {sprite['style']}",
        f"Framing: {sprite['framing']}",
        f"Character: {char['look']} {sprite['uniform']}",
        f"Expression: {expression}.",
        f"Content: {sprite['safety']}",
        "Background: fully transparent (PNG with alpha). If a transparent background is not "
        f"possible, fill the whole background with one flat {key_words} color, "
        "with no gradient, shadow, floor or objects.",
        f"No text, no watermark, no border. Portrait image, aspect ratio {sprite['aspect']}.",
    ])


def gpt_variant_prompt(cfg, char_id, face):
    """기준 그림을 붙인 채로 보내는 표정 바꾸기 요청문."""
    return variant_text(cfg, char_id, face) + " Keep the same background and the same image size."


def gpt_doc(cfg):
    """docs/art-prompts-gpt.md 의 내용. 요청문은 art_prompts.json에서 가져온다."""
    extra_count = sum(len(faces_for(cfg, c)) - len(FACES) for c in cfg["characters"])
    lines = [
        "# GPT로 캐릭터 그림 뽑기",
        "",
        "ChatGPT 같은 대화형 그림 도구에 붙여 넣을 요청문이다. "
        f"캐릭터 {len(cfg['characters'])}명, 기본 표정 {len(FACES)}장씩과 캐릭터만의 표정 {extra_count}장, "
        f"모두 {len(FACES) * len(cfg['characters']) + extra_count}장.",
        "",
        "이 글은 `python tools/make_art.py --gpt-doc` 이 만든다. 직접 고치지 말고 "
        "`tools/art_prompts.json`을 고친 뒤 같은 명령으로 다시 만든다.",
        "",
        "## 순서",
        "",
        "1. 캐릭터마다 새 대화를 연다. \"기준 그림\" 요청문을 붙여 넣어 한 장을 받는다. "
        "마음에 들 때까지 다시 뽑는다.",
        "2. 같은 대화에서 표정 요청문을 하나씩 보낸다. 기준 그림이 대화에 없으면 첨부한다. "
        "얼굴, 머리, 옷이 기준 그림과 같은지 본다.",
        "3. 받은 그림을 `art/raw/<캐릭터 id>/<표정>.png` 로 저장한다. "
        "예: `art/raw/astra/neutral.png`. jpg와 webp도 된다.",
        "4. `python tools/make_art.py --recut` 을 실행한다. 배경을 지우고(이미 투명이면 그대로 두고) "
        f"{cfg['sprite']['width']}x{cfg['sprite']['height']} 크기로 맞춰 `art/sprites/` 에 넣는다. "
        "`art/preview.png` 도 다시 만든다.",
        "5. `art/preview.png` 를 열어 모든 표정이 같은 얼굴인지, 머리가 잘리지 않았는지, "
        "배경이 깨끗이 지워졌는지 본다.",
        "6. 게임은 `run_booth.py` 로 켤 때 `art/` 의 그림을 가져다 쓴다. "
        "그림이 없는 캐릭터와 표정은 자리표시 그림이 나온다.",
        "",
        "## 지킬 것",
        "",
        "- 캐릭터는 전원 동갑 고2이고 전체 이용가다. 교복을 단정하게 입은 허리 위 그림만 쓴다. "
        "선정적으로 나온 그림은 쓰지 않는다.",
        "- 그림에 글자나 워터마크가 들어가면 다시 뽑는다.",
        "- 배경이 투명하게 안 나오면 요청문에 적힌 단색 배경으로 받는다. "
        "`--recut` 이 그 색을 지운다. 투명 배경 대신 체크무늬가 그려져 나와도 `--recut` 이 알아보고 지운다.",
        "- 기본 표정 이름: " + ", ".join(FACES) + ".",
        "- 캐릭터만의 표정은 그 캐릭터의 요청문 끝에 있다. 성격에 맞춰 더한 표정이고, 몸짓이 조금 바뀌는 것도 있다. "
        "그림이 없으면 게임은 비슷한 기본 표정의 그림을 대신 쓴다.",
        "",
        "## 캐릭터별 요청문",
    ]
    for char_id, char in cfg["characters"].items():
        lines += [
            "",
            f"### {char['name']} ({char_id})",
            "",
            f"기준 그림. 저장할 곳: `art/raw/{char_id}/neutral.png`",
            "",
            "```",
            gpt_sprite_prompt(cfg, char_id),
            "```",
        ]
        for face in faces_for(cfg, char_id):
            if face == "neutral":
                continue
            label = "표정" if face in FACES else "캐릭터만의 표정"
            lines += [
                "",
                f"{label} {face}. 저장할 곳: `art/raw/{char_id}/{face}.png`",
                "",
                "```",
                gpt_variant_prompt(cfg, char_id, face),
                "```",
            ]
    return "\n".join(lines) + "\n"


def bg_prompt(cfg, place):
    background = cfg["background"]
    return " ".join([background["style"], cfg["backgrounds"][place]["prompt"], background["rules"]])


# ---------------------------------------------------------------- 그림 다듬기

def _median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def estimate_background(rgb):
    """위, 왼쪽, 오른쪽 가장자리의 가운데값 색. 아래쪽은 몸이 걸쳐 있어서 보지 않는다."""
    width, height = rgb.size
    band = max(2, min(width, height) // 100)
    data = b"".join(
        strip.tobytes()
        for strip in (
            rgb.crop((0, 0, width, band)),
            rgb.crop((0, 0, band, height)),
            rgb.crop((width - band, 0, width, height)),
        )
    )
    return tuple(_median(data[i::3]) for i in range(3))


def _spill_image(rgb, key):
    """배경색이 얼마나 도드라지는지를 0-255로 나타낸 그림. 사람 쪽은 0에 가깝다."""
    red, green, blue = rgb.split()
    if key == "green":
        return ImageChops.subtract(green, ImageChops.lighter(red, blue))
    return ImageChops.subtract(ImageChops.darker(red, blue), green)


def _spill_value(color, key):
    red, green, blue = color
    value = green - max(red, blue) if key == "green" else min(red, blue) - green
    return max(0, value)


def cut_background(image, key, *, low=40, high=0.75):
    """단색 배경을 투명하게 만든다. (RGBA 그림, 경고 문장 또는 None)을 돌려준다."""
    rgb = image.convert("RGB")
    background = estimate_background(rgb)
    strength = _spill_value(background, key)
    if strength < 80:
        return rgb.convert("RGBA"), "배경이 요청한 단색이 아니라서 지우지 못함"
    top = max(low + 20, int(strength * high))
    span = top - low
    table = [255 if s <= low else 0 if s >= top else 255 - (s - low) * 255 // span
             for s in range(256)]
    alpha = _spill_image(rgb, key).point(table)

    # 반투명한 가장자리는 배경색이 섞여 있다. 섞인 만큼 빼서 원래 색을 되찾는다.
    alpha_bytes = alpha.tobytes()
    pixels = bytearray(rgb.tobytes())
    for run in re.finditer(rb"[\x01-\xfe]+", alpha_bytes):
        for index in range(run.start(), run.end()):
            scale = 255.0 / alpha_bytes[index]
            at = index * 3
            color = []
            for channel in range(3):
                value = background[channel] + (pixels[at + channel] - background[channel]) * scale
                color.append(0 if value < 0 else 255 if value > 255 else int(value))
            red, green, blue = color
            if key == "green":
                green = min(green, max(red, blue))
            else:
                excess = min(red, blue) - green
                if excess > 0:
                    red -= excess
                    blue -= excess
            pixels[at:at + 3] = bytes((red, green, blue))
    result = Image.frombytes("RGB", rgb.size, bytes(pixels)).convert("RGBA")
    result.putalpha(alpha)
    return result, None


# 그림 도구(ChatGPT 등)가 투명 배경을 달라는 요청에 체크무늬(흰 칸과 밝은 회색 칸)를 그림에 그려 넣을 때가 있다
# (2026-11-14 아스트라 denial). 칸의 색은 고르지 않고 칸 크기도 들쭉날쭉해서 정확한 격자로는 찾지 못한다.
# 그래서 "거의 무채색이고 밝은 점"을 위, 왼쪽, 오른쪽 테두리에서부터 이어지는 데까지 배경으로 본다.
# 아래쪽 테두리에서는 시작하지 않는다. 흰 셔츠가 아래 테두리에 닿아 있어서 셔츠까지 지워진다
CHECKER_SAT = 16            # 체크무늬 점: 가장 큰 채널과 가장 작은 채널의 차이가 이만큼 이하(셔츠는 연보라라서 더 크다)
CHECKER_LOW = 188           # 체크무늬 점: 가장 작은 채널이 이만큼 이상(어두운 칸도 꽤 밝다)
CHECKER_SPLIT = 232         # 이보다 밝으면 흰 칸, 어두우면 회색 칸
CHECKER_EDGE_SHARE = 0.6    # 테두리 점의 이만큼 이상이 체크무늬 점이고 흰 칸과 회색 칸이 다 있으면 체크무늬 배경이다
CHECKER_MIX = 0.15          # 흰 칸과 회색 칸이 저마다 이만큼 이상 섞여 있어야 체크무늬다
CHECKER_HOLE_MIN = 20       # 머리카락 사이에 갇힌 체크무늬 조각은 이만큼 이상 크고 두 칸이 섞여 있으면 지운다
FRINGE_LOW = 150            # 사람 가장자리에서 이보다 밝고
FRINGE_SAT = 40             # 이보다 무채색에 가까운 점은 체크무늬가 섞인 것이라 지운다
FRINGE_PASSES = 2


def _checker_masks(rgb):
    """(체크무늬 색인 점, 흰 칸 점)을 점마다 0/1인 bytes로."""
    red, green, blue = rgb.split()
    high = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    low = ImageChops.darker(ImageChops.darker(red, green), blue)
    gray = ImageChops.subtract(high, low).point(lambda v: 1 if v <= CHECKER_SAT else 0)
    bright = low.point(lambda v: 1 if v >= CHECKER_LOW else 0)
    light = low.point(lambda v: 1 if v >= CHECKER_SPLIT else 0)
    # 두 판은 점마다 0 또는 1이다. 둘 다 1인 점(darker는 작은 쪽)이 체크무늬 색이다. multiply는 255로 나눠서 쓰지 않는다
    return ImageChops.darker(gray, bright).tobytes(), light.tobytes(), low.tobytes(), \
        ImageChops.subtract(high, low).tobytes()


def _edge_indexes(width, height):
    """위, 왼쪽, 오른쪽 테두리 점의 번호."""
    return list(range(width)) + [y * width for y in range(height)] + [y * width + width - 1 for y in range(height)]


def looks_like_checker(image):
    """배경에 체크무늬가 그려진 그림인가."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    candidate, light, _, _ = _checker_masks(rgb)
    edge = _edge_indexes(width, height)
    hits = [i for i in edge if candidate[i]]
    whites = sum(light[i] for i in hits)
    return (len(hits) >= CHECKER_EDGE_SHARE * len(edge)
            and whites >= CHECKER_MIX * len(hits) and len(hits) - whites >= CHECKER_MIX * len(hits))


def _neighbors(index, width, total):
    x = index % width
    if index >= width:
        yield index - width
    if index + width < total:
        yield index + width
    if x > 0:
        yield index - 1
    if x < width - 1:
        yield index + 1


def cut_checker(image):
    """그려 넣은 체크무늬 배경을 투명하게 만든다. (RGBA 그림, 경고 문장 또는 None)을 돌려준다."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    total = width * height
    candidate, light, low, spread = _checker_masks(rgb)
    background = bytearray(total)

    # 1. 위, 왼쪽, 오른쪽 테두리에서 이어지는 체크무늬 점
    stack = [i for i in _edge_indexes(width, height) if candidate[i] and not background[i]]
    for index in stack:
        background[index] = 1
    while stack:
        index = stack.pop()
        for near in _neighbors(index, width, total):
            if candidate[near] and not background[near]:
                background[near] = 1
                stack.append(near)

    # 2. 머리카락 사이에 갇힌 체크무늬 조각. 흰 칸과 회색 칸이 섞여 있어야 한다(셔츠의 흰 부분은 흰색만이다)
    seen = bytearray(background)
    for start in range(total):
        if not candidate[start] or seen[start]:
            continue
        seen[start] = 1
        piece = [start]
        stack = [start]
        while stack:
            index = stack.pop()
            for near in _neighbors(index, width, total):
                if candidate[near] and not seen[near]:
                    seen[near] = 1
                    piece.append(near)
                    stack.append(near)
        whites = sum(light[i] for i in piece)
        if (len(piece) >= CHECKER_HOLE_MIN and whites >= CHECKER_MIX * len(piece)
                and len(piece) - whites >= CHECKER_MIX * len(piece)):
            for index in piece:
                background[index] = 1

    # 3. 가장자리에 남은 밝은 무채색 점(체크무늬와 섞인 점)을 벗겨 낸다
    for _ in range(FRINGE_PASSES):
        peel = [i for i in range(total) if not background[i] and low[i] >= FRINGE_LOW and spread[i] <= FRINGE_SAT
                and any(background[n] for n in _neighbors(i, width, total))]
        for index in peel:
            background[index] = 1

    if sum(background) >= total * 0.98:
        return rgb.convert("RGBA"), "체크무늬를 지우고 나니 남은 것이 없음"
    alpha = Image.frombytes("L", (width, height), bytes(0 if b else 255 for b in background))
    result = rgb.convert("RGBA")
    result.putalpha(alpha)
    return result, None


def normalize_sprite(image, size, *, top_margin=0.04, max_scale=1.5):
    """사람만 잘라 정해진 크기의 판에 아래 가운데로 맞춰 놓는다. 표정끼리 크기가 같아진다."""
    width, height = size
    solid = image.getchannel("A").point([255 if v > 24 else 0 for v in range(256)])
    box = solid.getbbox()
    if box is None:
        return None
    figure = image.crop(box)
    scale = min(width / figure.width, height * (1 - top_margin) / figure.height, max_scale)
    new_size = (max(1, round(figure.width * scale)), max(1, round(figure.height * scale)))
    if new_size != figure.size:
        figure = figure.resize(new_size, Image.LANCZOS)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(figure, ((width - figure.width) // 2, height - figure.height))
    return canvas


def has_transparency(image):
    """받은 그림이 이미 투명 배경인가. 위쪽과 양옆 테두리의 절반 이상이 투명하면 그렇다고 본다."""
    if image.mode not in ("RGBA", "LA") and "transparency" not in image.info:
        return False
    alpha = image.convert("RGBA").getchannel("A")
    width, height = alpha.size
    edge = list(alpha.crop((0, 0, width, 1)).getdata())
    edge += list(alpha.crop((0, 0, 1, height)).getdata())
    edge += list(alpha.crop((width - 1, 0, width, height)).getdata())
    clear = sum(1 for value in edge if value < 16)
    return clear * 2 >= len(edge)


def finish_sprite(raw_path, out_path, cfg, char_id):
    """받은 그림에서 배경을 지워 투명 PNG로 저장한다. 경고 문장 또는 None을 돌려준다."""
    cut = cfg.get("cut", {})
    with Image.open(raw_path) as source:
        if has_transparency(source):
            # 직접 그렸거나 다른 도구로 뽑은 그림. 이미 투명 배경이면 지울 것이 없다
            image, warning = source.convert("RGBA"), None
        elif looks_like_checker(source):
            # 투명 배경 대신 체크무늬를 그려 넣은 그림 (ChatGPT에서 가끔 나온다)
            image, warning = cut_checker(source)
        else:
            image, warning = cut_background(
                source, cfg["characters"][char_id]["key"],
                low=cut.get("low", 40), high=cut.get("high", 0.75),
            )
    if warning is None and cut.get("normalize", True):
        size = (cfg["sprite"]["width"], cfg["sprite"]["height"])
        placed = normalize_sprite(
            image, size,
            top_margin=cut.get("top_margin", 0.04), max_scale=cut.get("max_scale", 1.5),
        )
        if placed is None:
            warning = "배경을 지우고 나니 남은 것이 없음"
        else:
            image = placed
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)
    return warning


def finish_background(raw_path, out_path, cfg):
    """배경을 16:9로 가운데를 잘라 정해진 크기의 JPEG로 저장한다."""
    width, height = cfg["background"]["width"], cfg["background"]["height"]
    with Image.open(raw_path) as source:
        image = source.convert("RGB")
    ratio = width / height
    if image.width / image.height > ratio:
        new_width = round(image.height * ratio)
        left = (image.width - new_width) // 2
        image = image.crop((left, 0, left + new_width, image.height))
    else:
        new_height = round(image.width / ratio)
        top = (image.height - new_height) // 2
        image = image.crop((0, top, image.width, top + new_height))
    image = image.resize((width, height), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, quality=90)
    return None


def finish(out, key, cfg):
    """받은 그림(raw)에서 게임에 쓸 그림을 만든다. 경고 문장 또는 None."""
    raw = find_raw(out, key)
    if raw is None or Image is None:
        return None
    if is_bg(key):
        return finish_background(raw, final_path(out, key), cfg)
    return finish_sprite(raw, final_path(out, key), cfg, split_key(key)[0])


def reference_image(raw_path, max_side):
    """기준 그림을 참고 그림으로 보낼 크기로 줄인다. (확장자, 바이트)를 돌려준다."""
    data = raw_path.read_bytes()
    if Image is None:
        return sniff_image(data) or "png", data
    with Image.open(io.BytesIO(data)) as source:
        image = source.convert("RGB")
    image.thumbnail((max_side, max_side), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return "jpg", buffer.getvalue()


# ---------------------------------------------------------------- 미리보기

def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except Exception:  # 옛 Pillow이거나 글꼴 기능이 빠진 설치
        return ImageFont.load_default()


def _checker(size, cell=10):
    width, height = size
    board = Image.new("RGB", size, (236, 236, 236))
    draw = ImageDraw.Draw(board)
    for y in range(0, height, cell):
        for x in range((y // cell % 2) * cell, width, cell * 2):
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(205, 205, 205))
    return board


def _fit(image, box):
    copy = image.copy()
    copy.thumbnail(box, Image.LANCZOS)
    return copy


def make_preview(out, cfg, note=""):
    """지금까지 만든 그림을 한 장에 모은다. 이 한 장만 보내면 전체를 볼 수 있다."""
    if Image is None:
        return None
    out = pathlib.Path(out)
    chars = list(cfg["characters"])
    places = list(cfg["backgrounds"])
    pad, label_w, cell_w, cell_h = 8, 110, 200, 300
    columns = max(len(faces_for(cfg, c)) for c in chars) if chars else len(FACES)
    width = label_w + columns * (cell_w + pad) + pad
    head_h, line_h = 44, 22
    bg_cols = 4
    bg_w = (width - pad * (bg_cols + 1)) // bg_cols
    bg_h = bg_w * 9 // 16
    bg_rows = -(-len(places) // bg_cols)
    scene_cols = 3
    scene_w = (width - pad * (scene_cols + 1)) // scene_cols
    scene_h = scene_w * 9 // 16
    scene_rows = -(-len(chars) // scene_cols)

    sprites_top = head_h + line_h
    scenes_top = sprites_top + len(chars) * (cell_h + pad) + line_h + pad
    bgs_top = scenes_top + scene_rows * (scene_h + pad) + line_h + pad
    total = bgs_top + bg_rows * (bg_h + line_h + pad) + pad

    sheet = Image.new("RGB", (width, total), (248, 248, 248))
    draw = ImageDraw.Draw(sheet)
    big, small = _font(18), _font(14)
    ink, faint = (30, 30, 30), (120, 120, 120)
    draw.text((pad, 12), f"make_art preview   {note}", fill=ink, font=big)

    # 캐릭터 표정
    board = _checker((cell_w, cell_h))
    for column in range(columns):
        name = FACES[column] if column < len(FACES) else "extra"
        draw.text((label_w + column * (cell_w + pad) + 4, head_h + 2), name, fill=ink, font=small)
    for row, char_id in enumerate(chars):
        top = sprites_top + row * (cell_h + pad)
        draw.text((pad, top + 6), char_id, fill=ink, font=small)
        draw.text((pad, top + 26), f"key: {cfg['characters'][char_id]['key']}", fill=faint, font=small)
        for column, face in enumerate(faces_for(cfg, char_id)):
            left = label_w + column * (cell_w + pad)
            sheet.paste(board, (left, top))
            path = final_path(out, f"{char_id}:{face}")
            if path.is_file():
                with Image.open(path) as source:
                    sprite = _fit(source.convert("RGBA"), (cell_w, cell_h))
                sheet.paste(sprite, (left + (cell_w - sprite.width) // 2, top + cell_h - sprite.height), sprite)
            else:
                draw.text((left + 8, top + 8), "missing", fill=faint, font=small)
            if face not in FACES:      # 캐릭터만의 표정은 칸 아래에 이름을 적는다. 그림 위에 쓰므로 바탕을 깐다
                box = draw.textbbox((left + 6, top + cell_h - 22), face, font=small)
                draw.rectangle((box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2), fill=(255, 255, 255))
                draw.text((left + 6, top + cell_h - 22), face, fill=ink, font=small)

    # 배경 위에 세워 본 모습
    draw.text((pad, scenes_top - line_h), "scene check (sprite on background, with a dialogue box)",
              fill=ink, font=small)
    for index, char_id in enumerate(chars):
        left = pad + index % scene_cols * (scene_w + pad)
        top = scenes_top + index // scene_cols * (scene_h + pad)
        scene = Image.new("RGBA", (scene_w, scene_h), (170, 176, 186, 255))
        bg_file = final_path(out, f"bg:{places[index % len(places)]}") if places else None
        if bg_file is not None and bg_file.is_file():
            with Image.open(bg_file) as source:
                scene.paste(source.convert("RGB").resize((scene_w, scene_h), Image.LANCZOS))
        sprite_file = final_path(out, f"{char_id}:{BASE_FACE}")
        if sprite_file.is_file():
            with Image.open(sprite_file) as source:
                sprite = _fit(source.convert("RGBA"), (scene_w, int(scene_h * 0.96)))
            scene.alpha_composite(sprite, ((scene_w - sprite.width) // 2, scene_h - sprite.height))
        box = Image.new("RGBA", (scene_w - 24, scene_h * 26 // 100), (20, 24, 40, 190))
        ImageDraw.Draw(box).rectangle((0, 0, box.width - 1, box.height - 1), outline=(255, 255, 255, 220), width=2)
        scene.alpha_composite(box, (12, scene_h - box.height - 8))
        sheet.paste(scene.convert("RGB"), (left, top))

    # 배경
    draw.text((pad, bgs_top - line_h), "backgrounds", fill=ink, font=small)
    for index, place in enumerate(places):
        left = pad + index % bg_cols * (bg_w + pad)
        top = bgs_top + index // bg_cols * (bg_h + line_h + pad)
        path = final_path(out, f"bg:{place}")
        if path.is_file():
            with Image.open(path) as source:
                sheet.paste(source.convert("RGB").resize((bg_w, bg_h), Image.LANCZOS), (left, top))
        else:
            draw.rectangle((left, top, left + bg_w - 1, top + bg_h - 1), fill=(225, 225, 225))
            draw.text((left + 8, top + 8), "missing", fill=faint, font=small)
        draw.text((left + 2, top + bg_h + 2), place, fill=ink, font=small)

    out.mkdir(parents=True, exist_ok=True)
    target = out / "preview.png"
    sheet.save(target)
    return target


# ---------------------------------------------------------------- 실행

def _load_manifest(out):
    path = pathlib.Path(out) / "manifest.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {}


def _save_manifest(out, manifest):
    path = pathlib.Path(out) / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_raw(out, key, data):
    stem = raw_stem(out, key)
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in RAW_EXTS:  # 예전 것이 다른 형식으로 남아 있으면 지운다
        stem.with_name(f"{stem.name}.{ext}").unlink(missing_ok=True)
    path = stem.with_name(f"{stem.name}.{sniff_image(data)}")
    path.write_bytes(data)
    return path


def build_parser():
    parser = argparse.ArgumentParser(
        description="소개팅 그림(캐릭터 표정, 배경)을 한꺼번에 뽑는다.",
        epilog="예: python tools/make_art.py --only astra",
    )
    parser.add_argument("--only", nargs="*", default=[], metavar="이름",
                        help="이것만 만든다. 캐릭터, 캐릭터:표정, sprites, bg, 배경 이름")
    parser.add_argument("--backend", default="auto",
                        choices=("auto", "cloudflare", "schnell", "gemini"),
                        help="그림을 만들 곳 (기본: 키가 있는 쪽, Cloudflare 먼저)")
    parser.add_argument("--model", help="모델 이름을 직접 정한다")
    parser.add_argument("--force", action="store_true", help="이미 있어도 다시 만든다")
    parser.add_argument("--seed", type=int, default=0, help="다른 그림을 보고 싶을 때 바꾸는 숫자")
    parser.add_argument("--dry-run", action="store_true", help="요청문만 보여 주고 끝낸다")
    parser.add_argument("--recut", action="store_true",
                        help="새로 받지 않고, 받아 둔 그림으로 배경 지우기와 미리보기만 다시 한다")
    parser.add_argument("--list", action="store_true", help="이름과 진행 상황을 보여 준다")
    parser.add_argument("--gpt-doc", nargs="?", const=str(GPT_DOC_PATH), metavar="파일",
                        help="ChatGPT 같은 도구에 붙여 넣을 요청문 문서를 만들고 끝낸다 "
                             "(기본: docs/art-prompts-gpt.md)")
    parser.add_argument("--out", default=str(ROOT / "art"), help="그림을 둘 폴더 (기본: art)")
    return parser


def _show_list(out, cfg):
    say("캐릭터 (이름: 받은 표정)")
    for char_id, char in cfg["characters"].items():
        have = [face for face in FACES if find_raw(out, f"{char_id}:{face}")]
        say(f"  {char_id:8} {char.get('name', '')}: {', '.join(have) or '없음'}")
    say("배경")
    for place, info in cfg["backgrounds"].items():
        mark = "있음" if find_raw(out, f"bg:{place}") else "없음"
        say(f"  {place:12} {info.get('seed', '')}: {mark}")


def _show_plan(keys, cfg):
    for key in keys:
        left, right = split_key(key)
        if is_bg(key):
            size = f"{cfg['background']['width']}x{cfg['background']['height']}"
            prompt = bg_prompt(cfg, right)
        else:
            size = f"{cfg['sprite']['width']}x{cfg['sprite']['height']}"
            prompt = sprite_prompt(cfg, left, right, variant=right != BASE_FACE)
        say(f"[{key}] {size}, {len(prompt)}자")
        say(f"  {prompt}")
    say(f"모두 {len(keys)}장. 실제 요청은 보내지 않았습니다.")


def run(args, cfg):
    out = pathlib.Path(args.out)
    try:
        selected = parse_only(args.only, cfg)
    except ValueError as err:
        say(str(err))
        return 2

    if args.gpt_doc:
        target = pathlib.Path(args.gpt_doc)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(gpt_doc(cfg), encoding="utf-8")
        say(f"요청문 문서: {target}")
        return 0
    if args.list:
        _show_list(out, cfg)
        return 0
    if args.dry_run:
        _show_plan(selected, cfg)
        return 0
    if Image is None:
        say("알림: Pillow가 없어서 배경 지우기와 미리보기는 건너뜁니다. (pip install pillow)")

    warnings = {}
    failed = {}
    made = 0
    skipped = 0
    stopped = None
    note = "recut"

    if not args.recut:
        try:
            backend = pick_backend(args.backend, args.model)
        except ArtError as err:
            say(str(err))
            return 2
        note = f"{backend.name} {backend.model}"
        say(f"그림 만들 곳: {backend.name} ({backend.model})")
        use_refs = backend.uses_reference
        ref_side = cfg.get("reference", {}).get("max_side", 512)
        if backend.ref_max_side:
            ref_side = min(ref_side, backend.ref_max_side)
        if not use_refs:
            say("알림: 이 모델은 참고 그림을 받지 않습니다. 표정마다 얼굴이 조금 달라질 수 있습니다.")
        elif Image is None and backend.ref_max_side:
            use_refs = False
            say(f"알림: 이 모델은 참고 그림을 {backend.ref_max_side}픽셀 이하로 줄여 보내야 하는데 "
                "Pillow가 없어 줄일 수 없습니다. 참고 그림 없이 뽑으므로 표정마다 얼굴이 달라질 수 있습니다.")

        # 표정을 만들려면 기준 그림이 먼저 있어야 한다.
        todo = []
        for key in selected:
            if is_bg(key) or split_key(key)[1] == BASE_FACE:
                continue
            base = f"{split_key(key)[0]}:{BASE_FACE}"
            if base not in selected and base not in todo and find_raw(out, base) is None:
                todo.append(base)
        order = all_keys(cfg)
        jobs = sorted(set(selected) | set(todo), key=order.index)
        pending = [
            k for k in jobs
            if (args.force and k in selected) or find_raw(out, k) is None
        ]
        skipped = len(jobs) - len(pending)
        say(f"만들 그림 {len(pending)}장" + (f" (이미 있는 {skipped}장은 건너뜀)" if skipped else ""))

        manifest = _load_manifest(out)
        fresh_bases = set()
        count = 0
        for key in jobs:
            left, right = split_key(key)
            sprite = not is_bg(key)
            variant = sprite and right != BASE_FACE
            needed = key in pending or (variant and left in fresh_bases and key in selected)
            if not needed:
                continue
            count += 1
            say(f"[{count:2}] {key} ... ", end="")
            refs = []
            if variant:
                base_raw = find_raw(out, f"{left}:{BASE_FACE}")
                if base_raw is None:
                    failed[key] = "기준 그림이 없어서 건너뜀"
                    say("건너뜀 (기준 그림 없음)")
                    continue
                if use_refs:
                    refs = [reference_image(base_raw, ref_side)]
            if sprite:
                prompt = sprite_prompt(cfg, left, right, variant=bool(refs))
                size = cfg["sprite"]
                seed = seed_for(left, args.seed)
            else:
                prompt = bg_prompt(cfg, right)
                size = cfg["background"]
                seed = seed_for(key, args.seed)
            started = time.monotonic()
            try:
                data, used_seed = generate(
                    backend, prompt, seed=seed, refs=refs,
                    width=size["width"], height=size["height"], aspect=size["aspect"],
                )
            except ArtError as err:
                failed[key] = str(err)
                say(f"실패\n     {err}")
                if err.stop:
                    stopped = key
                    break
                continue
            _save_raw(out, key, data)
            made += 1
            if sprite and right == BASE_FACE:
                fresh_bases.add(left)
            warning = finish(out, key, cfg)
            if warning:
                warnings[key] = warning
            manifest[key] = {
                "backend": backend.name, "model": backend.model, "seed": used_seed,
                "prompt": prompt, "at": datetime.datetime.now().isoformat(timespec="seconds"),
                "warning": warning,
            }
            _save_manifest(out, manifest)
            say(f"됨 ({time.monotonic() - started:.1f}초)" + (f", 주의: {warning}" if warning else ""))
            _sleep(PAUSE_SEC)

        # 기준 그림만 새로 뽑으면 예전 표정들과 얼굴이 어긋난다.
        for char_id in sorted(fresh_bases):
            stale = [
                face for face in FACES
                if face != BASE_FACE and f"{char_id}:{face}" not in selected
                and find_raw(out, f"{char_id}:{face}")
            ]
            if stale:
                say(f"알림: {char_id}의 기준 그림이 바뀌었습니다. 예전 표정({', '.join(stale)})과 "
                    f"맞추려면: python tools/make_art.py --only {char_id} --force")

    # 받아 둔 그림으로 게임용 그림을 만든다. 빠진 것만, --recut이면 전부.
    if Image is not None:
        for key in selected:
            raw = find_raw(out, key)
            if raw is None:
                continue
            target = final_path(out, key)
            if args.recut or not target.is_file():
                warning = finish(out, key, cfg)
                if warning:
                    warnings[key] = warning
        preview = make_preview(out, cfg, f"{note}   {datetime.date.today().isoformat()}")
        say(f"미리보기: {preview}")

    say(f"끝: 새로 {made}장, 실패 {len(failed)}장.")
    for key, warning in warnings.items():
        say(f"  주의 {key}: {warning}")
    if stopped:
        say("위의 문제 때문에 멈췄습니다. 고친 뒤 같은 명령을 다시 실행하면 남은 것부터 이어집니다.")
    elif failed:
        say("실패한 것만 다시: python tools/make_art.py --only " + " ".join(failed))
    return 1 if failed else 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    load_dotenv(ROOT / ".env")
    load_dotenv(pathlib.Path.cwd() / ".env")
    try:
        cfg = load_config()
    except (OSError, ValueError, KeyError) as err:
        say(f"tools/art_prompts.json을 읽지 못했습니다: {err}")
        return 2
    try:
        return run(args, cfg)
    except KeyboardInterrupt:
        say("\n멈췄습니다. 같은 명령을 다시 실행하면 남은 것부터 이어집니다.")
        return 130


if __name__ == "__main__":
    sys.exit(main())

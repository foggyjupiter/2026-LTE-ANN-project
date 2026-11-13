"""모델 호출 계층.

"대화 기록(messages)을 넣으면 답 문자열이 나오는 함수" 하나로 감싼다.
제공자 목록을 위에서부터 차례로 시도하고, 실패하면 다음으로 넘어간다.
표준 라이브러리만 쓴다.
"""
import json
import os
import time
import urllib.error
import urllib.request

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# 위에서부터 차례로 시도한다. 키가 없는 제공자는 건너뛴다.
#
# 순서의 근거 (2026-11-13 오전, 무료 등급 키로 실제 지시문을 보내 잰 값):
#   gemini-3.5-flash-lite  68번 중 68번 성공, 0.9-2.5초 (평균 1.5초)
#   gemini-3.1-flash-lite  1번 중 1번 성공, 2.4초
#   gemini-3.8-flash       12번 중 0번 성공. 10초에서 30초 넘게 무응답 7번, 503 4번, 429 1번
#                          (20분 뒤에 다시 재도 같았다)
#   gemini-3.6-flash       1번 중 1번 성공, 16.7초
#   gemini-3.5-flash, gemini-3.7-flash, gemini-flash-latest, gemini-4-hydrogen  각 1번 중 0번 성공
# 503의 본문은 "This model is currently experiencing high demand"였다. reasoning_effort를
# 빼도 같았다. flash 급 모델은 무료 등급에서 과부하로 못 쓰는 상태였고 flash-lite만 빠르고
# 안 죽었다. 부스에서는 한 턴이 몇 초 안에 나와야 하므로 flash-lite를 맨 앞에 둔다.
# 유료 등급 키로 바꾸거나 과부하가 풀리면 gemini-flash 를 다시 재 보고, 빠르면 맨 위로 올린다.
#
# 칸 설명
#   timeout      이 시간(초) 안에 답이 없으면 다음 제공자로 넘어간다
#   temperature  False면 temperature를 보내지 않는다. Gemini 3.6 이후 모델은 이 값을 무시하고
#                문서가 요청에서 빼라고 한다 (ai.google.dev/gemini-api/docs/whats-new-gemini-3.6)
#   extra        요청에 그대로 덧붙일 칸. gemini-3.8-flash의 reasoning_effort는 low, medium, high만
#                되고 minimal은 오류다. flash-lite는 기본값이 minimal(가장 빠름)이라 비워 둔다
PROVIDERS = [
    {
        "name": "gemini-flash-lite",
        "url": GEMINI_URL,
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-3.5-flash-lite",
        "extra": {},
        "timeout": 6,
        "temperature": False,
    },
    {
        "name": "gemini-flash-lite-3.1",  # 모델이 달라서 한도가 따로 잡힌다
        "url": GEMINI_URL,
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-3.1-flash-lite",
        "extra": {},
        "timeout": 6,
        "temperature": False,
    },
    {
        "name": "gemini-flash",
        "url": GEMINI_URL,
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-3.8-flash",
        "extra": {"reasoning_effort": "low"},  # 생각 단계를 낮춰 응답을 빠르게
        "timeout": 8,
        "temperature": False,
    },
    {
        "name": "groq",
        "url": GROQ_URL,
        "key_env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b",
        "extra": {"reasoning_effort": "low"},
        "timeout": 8,
    },
]
TIMEOUT_SEC = 6          # 제공자에 timeout 칸이 없을 때 쓰는 값
COOLDOWN_SEC = 60        # 한도 초과(429)가 난 제공자는 이만큼 쉬게 둔다
BUSY_COOLDOWN_SEC = 20   # 과부하(5xx)나 시간 초과가 난 제공자를 쉬게 두는 시간. 연달아 나면 두 배씩 는다
BUSY_COOLDOWN_MAX_SEC = 120
RETRY_AFTER_MAX_SEC = 600  # 서버가 알려 준 대기 시간을 믿는 상한

_blocked_until = {}   # 제공자 이름 -> 다시 써도 되는 시각
_busy_streak = {}     # 제공자 이름 -> 과부하나 시간 초과가 연달아 난 횟수
_no_json_mode = set()  # JSON 강제 옵션을 거부한 제공자 이름
stats = {"calls": 0, "failures": 0, "last_provider": None, "last_sec": None}


class AllProvidersDown(Exception):
    """쓸 수 있는 제공자가 하나도 없을 때."""


def load_dotenv(path=".env"):
    """`.env` 파일의 KEY=VALUE 줄을 환경변수로 읽는다. 이미 있는 값은 덮어쓰지 않는다."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _post(provider, key, messages, temperature, json_mode):
    body = {"model": provider["model"], "messages": messages, **provider["extra"]}
    if provider.get("temperature", True):
        body["temperature"] = temperature
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        provider["url"],
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
            "User-Agent": "sogaeting-booth/1.0",  # 기본 UA는 차단되는 경우가 있음
        },
    )
    with urllib.request.urlopen(req, timeout=provider.get("timeout", TIMEOUT_SEC)) as res:
        data = json.load(res)
    return data["choices"][0]["message"]["content"]


def _error_detail(error, key):
    """HTTP 오류 본문에서 사람이 읽을 한 줄을 꺼낸다. 키가 섞여 있으면 가린다."""
    try:
        raw = error.read(4000).decode("utf-8", "replace")
    except Exception:
        return ""
    text = raw
    try:
        data = json.loads(raw)
        if isinstance(data, list) and data:  # Gemini는 목록에 싸서 준다
            data = data[0]
        inner = data.get("error") if isinstance(data, dict) else None
        if isinstance(inner, dict):
            text = " ".join(str(inner[k]) for k in ("status", "message") if inner.get(k))
        elif isinstance(inner, str):
            text = inner
    except ValueError:
        pass
    text = " ".join(text.split())
    if key:
        text = text.replace(key, "***")
    return text[:300]


def _retry_after(error):
    """429 응답의 Retry-After 헤더(초). 없거나 이상하면 None. Groq는 429에 이 헤더를 붙인다."""
    try:
        value = float(error.headers.get("Retry-After", ""))
    except (AttributeError, TypeError, ValueError):
        return None
    return value if 0 < value <= RETRY_AFTER_MAX_SEC else None


def _rest(name, seconds):
    _blocked_until[name] = time.time() + seconds


def _rest_busy(name):
    """과부하나 시간 초과: 연달아 날수록 오래 쉬게 둔다."""
    streak = _busy_streak.get(name, 0) + 1
    _busy_streak[name] = streak
    _rest(name, min(BUSY_COOLDOWN_SEC * 2 ** (streak - 1), BUSY_COOLDOWN_MAX_SEC))


def _try_provider(p, key, messages, temperature, json_mode):
    """제공자 하나에 요청한다. (답 문자열 또는 None, 실패 사유 또는 None)"""
    name = p["name"]
    use_json = json_mode and name not in _no_json_mode
    try:
        try:
            text = _post(p, key, messages, temperature, use_json)
        except urllib.error.HTTPError as e:
            if e.code == 400 and use_json:
                # JSON 강제 옵션을 못 받는 제공자: 기억해 두고 옵션 없이 한 번 더
                _no_json_mode.add(name)
                text = _post(p, key, messages, temperature, False)
            else:
                raise
        if text and text.strip():
            _busy_streak.pop(name, None)
            return text.strip(), None
        print(f"[{name}] 빈 응답")
        return None, "빈 응답"
    except urllib.error.HTTPError as e:
        detail = _error_detail(e, key)
        if e.code == 429:
            _rest(name, _retry_after(e) or COOLDOWN_SEC)
        elif e.code >= 500:
            _rest_busy(name)
        # 400, 401, 403, 404는 키나 모델명이 틀렸다는 뜻이니 리허설 때 이 로그를 확인할 것
        print(f"[{name}] HTTP {e.code}" + (f" {detail}" if detail else ""))
        return None, f"HTTP {e.code}" + (f" {detail}" if detail else "")
    except Exception as e:  # 시간 초과, 인터넷 끊김, 응답 형식 이상
        _rest_busy(name)
        reason = f"{type(e).__name__}: {e}"
        if key:
            reason = reason.replace(key, "***")
        print(f"[{name}] {reason}")
        return None, reason


def call_llm(messages, temperature=0.9, json_mode=False, trace=None):
    """대화 기록 전체를 보내고 답 문자열을 받는다. 모든 제공자가 실패하면 AllProvidersDown.

    trace에 목록을 주면 시도마다 {"provider", "model", "ok", "sec", "error"}를 덧붙인다.
    키와 요청 헤더는 담지 않는다.
    """
    for p in PROVIDERS:
        key = os.environ.get(p["key_env"], "")
        if not key or time.time() < _blocked_until.get(p["name"], 0):
            continue
        stats["calls"] += 1
        started = time.monotonic()
        text, error = _try_provider(p, key, messages, temperature, json_mode)
        sec = round(time.monotonic() - started, 2)
        if trace is not None:
            trace.append({"provider": p["name"], "model": p["model"],
                          "ok": text is not None, "sec": sec, "error": error})
        if text is not None:
            stats["last_provider"] = p["name"]
            stats["last_sec"] = sec
            return text
        stats["failures"] += 1
    raise AllProvidersDown()


def seconds_until_ready():
    """키가 있는 제공자 가운데 가장 먼저 풀리는 것까지 남은 시간(초).

    지금 바로 쓸 수 있는 제공자가 있으면 0, 키가 하나도 없으면 None.
    """
    waits = [
        max(0.0, _blocked_until.get(p["name"], 0) - time.time())
        for p in PROVIDERS if os.environ.get(p["key_env"], "")
    ]
    return min(waits) if waits else None


def status_line():
    """운영자가 터미널에서 보는 한 줄 상태."""
    line = f"모델 호출 {stats['calls']}회, 실패 {stats['failures']}회, 최근 제공자 {stats['last_provider']}"
    if stats.get("last_sec") is not None:
        line += f" ({stats['last_sec']:.1f}초)"
    return line

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

# 위에서부터 차례로 시도한다. 키가 없는 제공자는 건너뛴다.
PROVIDERS = [
    {
        "name": "gemini-flash",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-3.8-flash",
        "extra": {"reasoning_effort": "low"},  # 생각 단계를 낮춰 응답을 빠르게
    },
    {
        "name": "gemini-flash-lite",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-3.5-flash-lite",
        "extra": {},
    },
    {
        "name": "groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b",
        "extra": {"reasoning_effort": "low"},
    },
]
TIMEOUT_SEC = 10   # 이 시간 안에 답이 없으면 다음 제공자로
COOLDOWN_SEC = 60  # 한도 초과(429)가 난 제공자는 이만큼 쉬게 둔다

_blocked_until = {}   # 제공자 이름 -> 다시 써도 되는 시각
_no_json_mode = set()  # JSON 강제 옵션을 거부한 제공자 이름
stats = {"calls": 0, "failures": 0, "last_provider": None}


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
    body = {
        "model": provider["model"],
        "messages": messages,
        "temperature": temperature,
        **provider["extra"],
    }
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
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
        data = json.load(res)
    return data["choices"][0]["message"]["content"]


def _try_provider(p, key, messages, temperature, json_mode):
    """제공자 하나에 요청한다. 답 문자열 또는 None."""
    use_json = json_mode and p["name"] not in _no_json_mode
    try:
        try:
            text = _post(p, key, messages, temperature, use_json)
        except urllib.error.HTTPError as e:
            if e.code == 400 and use_json:
                # JSON 강제 옵션을 못 받는 제공자: 기억해 두고 옵션 없이 한 번 더
                _no_json_mode.add(p["name"])
                text = _post(p, key, messages, temperature, False)
            else:
                raise
        if text and text.strip():
            return text.strip()
        print(f"[{p['name']}] 빈 응답")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            _blocked_until[p["name"]] = time.time() + COOLDOWN_SEC
        # 400, 401, 403은 키나 모델명이 틀렸다는 뜻이니 리허설 때 이 로그를 확인할 것
        print(f"[{p['name']}] HTTP {e.code}")
    except Exception as e:  # 시간 초과, 인터넷 끊김, 응답 형식 이상
        print(f"[{p['name']}] {type(e).__name__}: {e}")
    return None


def call_llm(messages, temperature=0.9, json_mode=False):
    """대화 기록 전체를 보내고 답 문자열을 받는다. 모든 제공자가 실패하면 AllProvidersDown."""
    for p in PROVIDERS:
        key = os.environ.get(p["key_env"], "")
        if not key or time.time() < _blocked_until.get(p["name"], 0):
            continue
        stats["calls"] += 1
        text = _try_provider(p, key, messages, temperature, json_mode)
        if text is not None:
            stats["last_provider"] = p["name"]
            return text
        stats["failures"] += 1
    raise AllProvidersDown()


def status_line():
    """운영자가 터미널에서 보는 한 줄 상태."""
    return f"모델 호출 {stats['calls']}회, 실패 {stats['failures']}회, 최근 제공자 {stats['last_provider']}"

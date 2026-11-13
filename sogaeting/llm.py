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
# 순서의 근거 (2026-11-13 11:30-12:25, 무료 등급 키로 실제 지시문을 보내 잰 값):
#   gemini-3.5-flash-lite  196번 중 180번 성공. 성공한 호출은 0.8-5.2초, 평균 1.7초.
#                          실패는 503 14번, 시간 초과 2번이고 12:02-12:18에 몰려 있었다
#   gemini-3.1-flash-lite  20번 중 9번 성공(1.4-5.2초, 평균 2.5초). 실패는 시간 초과 7번, 503 4번
#   gemini-3.8-flash       15번 중 0번 성공. 8초에서 30초 넘게 무응답 8번, 503 6번, 429 1번
#                          (20분 뒤에 다시 재도 같았다)
#   gemini-3.6-flash       1번 중 1번 성공, 16.7초
#   gemini-3.5-flash, gemini-3.7-flash, gemini-flash-latest, gemini-4-hydrogen  각 1번 중 0번 성공
# 503의 본문은 "This model is currently experiencing high demand"였다. reasoning_effort를
# 빼도 같았다. flash 급 모델은 무료 등급에서 과부하로 못 쓰는 상태였고 flash-lite만 빠르게
# 답했다. 그래서 flash-lite 둘만 쓴다. gemini-3.8-flash를 예비로 두었더니 flash-lite 둘이
# 같이 503을 낸 턴에 8초를 더 버리고도 답을 못 받았다. 그 503은 20초 뒤에 풀려 있었다.
#
# 설계 문서의 주 모델은 gemini-3.8-flash(유료 키 기준)다. 유료 등급 키로 바꾸거나 과부하가 풀려서
# 이 모델을 쓰려면 코드를 고치지 말고 .env에 GEMINI_MAIN_MODEL=gemini-3.8-flash 한 줄을 적는다.
# 그러면 그 모델을 맨 앞에서 먼저 부른다(_providers). 적은 뒤에는
# `python3 -m sogaeting.playtest --only mistral`로 응답 시간을 잰다. flash-lite만큼 빠르지 않으면
# 그 줄을 다시 지운다. reasoning_effort는 low, medium, high만 되고 minimal은 오류다.
#
# 칸 설명
#   timeout      이 시간(초) 안에 답이 없으면 다음 제공자로 넘어간다
#   temperature  False면 temperature를 보내지 않는다. Gemini 3.6 이후 모델은 이 값을 무시하고
#                문서가 요청에서 빼라고 한다 (ai.google.dev/gemini-api/docs/whats-new-gemini-3.6)
#   extra        요청에 그대로 덧붙일 칸. flash-lite는 생각 단계의 기본값이 minimal(가장 빠름)이라
#                비워 둔다
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
        "timeout": 4,  # 성공한 호출은 거의 4초 안에 왔고, 6초를 기다리면 1순위를 다시 부를 시간이 안 남는다
        "temperature": False,
    },
    {
        # 2026-11-13 15:40 KST에 flash-lite 둘이 각각 하루 한도(429)와 과부하(503)로 막혔을 때 따로 쟀다.
        # 실제 지시문 4번 모두 형식에 맞게 답했고 2.2-10.0초였다. 한도가 모델마다 따로라서 하루에 부를 수 있는
        # 횟수가 그만큼 는다. 생각 단계를 low로 두지 않으면 8초를 넘겼다.
        # 같은 날 gemini-2.5-flash와 2.5-flash-lite는 "새 사용자는 못 쓴다"(404), gemma-4는 500과 502였다.
        "name": "gemini-flash-3",
        "url": GEMINI_URL,
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-3-flash-preview",
        "extra": {"reasoning_effort": "low"},
        "timeout": 6,
        "temperature": False,
    },
    {
        "name": "groq",
        "url": GROQ_URL,
        "key_env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b",
        "extra": {"reasoning_effort": "low"},
        "timeout": 6,
    },
]
MAIN_MODEL_ENV = "GEMINI_MAIN_MODEL"   # 맨 앞에서 먼저 부를 Gemini 모델 이름. 비어 있으면 쓰지 않는다
TIMEOUT_SEC = 6          # 제공자에 timeout 칸이 없을 때 쓰는 값
TURN_BUDGET_SEC = 10     # call_llm 한 번이 쓸 수 있는 시간. 다 쓰면 포기하고 대체 대사로 간다
MIN_ATTEMPT_SEC = 2      # 남은 시간이 이보다 적으면 새로 시도하지 않는다
COOLDOWN_SEC = 60        # 한도 초과(429)가 난 제공자는 이만큼 쉬게 둔다
# 과부하와 시간 초과가 난 제공자를 쉬게 두는 시간. 연달아 나면 두 배씩 늘고 상한에서 멈춘다.
BUSY_COOLDOWN_SEC = 3    # 5xx: 서버가 곧바로 거절한 것이라 금방 풀리곤 한다. 같은 턴 안에 다시 해 본다
SLOW_COOLDOWN_SEC = 12   # 시간 초과와 연결 실패: 같은 턴에 또 기다리지 않게 한 턴의 시간보다 길게 쉰다
BUSY_COOLDOWN_MAX_SEC = 120
RETRY_AFTER_MAX_SEC = 600  # 서버가 알려 준 대기 시간을 믿는 상한
# Gemini 무료 등급은 모델마다 하루 요청 수 한도가 있다(2026-11-13에 본 값은 프로젝트당 하루 500번).
# 한도에 닿은 날에도 어떤 요청은 통과하고 어떤 요청은 하루 한도 429로 막혔다. 길게 쉬게 두면
# 통과할 요청까지 예비 모델로 넘어가서 대체 대사가 늘었다. 그래서 보통 429와 같은 시간만 쉰다.
DAILY_COOLDOWN_SEC = 60

_blocked_until = {}   # 키 자리 이름(_slot) -> 다시 써도 되는 시각
_busy_streak = {}     # 제공자 이름 -> 과부하나 시간 초과가 연달아 난 횟수
_no_json_mode = set()  # JSON 강제 옵션을 거부한 제공자 이름
stats = {"calls": 0, "failures": 0, "last_provider": None, "last_sec": None}


class AllProvidersDown(Exception):
    """쓸 수 있는 제공자가 하나도 없을 때."""


def _read_env_text(path):
    """`.env` 파일의 글. 윈도우 메모장과 PowerShell이 붙이는 BOM과 UTF-16도 읽는다.

    BOM이 붙은 채로 읽으면 첫 줄의 이름이 "\ufeffGEMINI_API_KEY"가 되어 키가 없는 것처럼 된다.
    그러면 모든 답이 대체 대사(괄호 속 행동)로 나간다.
    """
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


dotenv_ignored = []  # .env에 있었지만 컴퓨터의 환경변수에 다른 값이 있어서 쓰지 않은 이름


def load_dotenv(path=".env"):
    """`.env` 파일의 KEY=VALUE 줄을 환경변수로 읽는다. 이미 있는 값은 덮어쓰지 않는다."""
    if not os.path.exists(path):
        return
    for line in _read_env_text(path).splitlines():
        line = line.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key in os.environ and os.environ[key] != value and key not in dotenv_ignored:
            dotenv_ignored.append(key)  # 컴퓨터의 환경변수가 이긴다. 점검 도구와 서버가 알려 준다
        os.environ.setdefault(key, value)


def key_counts():
    """키 이름마다 읽은 키의 개수. 키 값은 담지 않는다. 예: {"GEMINI_API_KEY": 2, "GROQ_API_KEY": 0}"""
    counts = {}
    for p in PROVIDERS:
        counts[p["key_env"]] = len(_keys(p))
    return counts


def _providers():
    """이번에 쓸 제공자 목록. GEMINI_MAIN_MODEL이 적혀 있으면 그 모델을 맨 앞에 둔다."""
    model = os.environ.get(MAIN_MODEL_ENV, "").strip()
    if not model:
        return PROVIDERS
    main = {
        "name": "gemini-main",
        "url": GEMINI_URL,
        "key_env": "GEMINI_API_KEY",
        "model": model,
        "extra": {"reasoning_effort": "low"},
        "timeout": 6,
        "temperature": False,
    }
    return [main] + [p for p in PROVIDERS if p["model"] != model]


def _keys(provider):
    """제공자의 키 목록. 환경변수에 쉼표로 이어 적으면 여러 개다 (GEMINI_API_KEY=키1,키2).

    한도(429)는 키가 속한 프로젝트마다 따로 잡히므로, 한도가 찬 키는 건너뛰고 다음 키를 쓴다.
    같은 프로젝트에서 만든 키끼리는 한도를 나눠 쓰니 여러 개 적어도 소용이 없다.
    """
    return [k.strip() for k in os.environ.get(provider["key_env"], "").split(",") if k.strip()]


def _slot(name, index):
    """키마다 쉬는 시간을 따로 적어 두는 이름. 첫 키는 제공자 이름 그대로, 다음부터 "이름#2"."""
    return name if index == 0 else f"{name}#{index + 1}"


def _slots(provider):
    """[(키 자리 이름, 키)]"""
    return [(_slot(provider["name"], i), key) for i, key in enumerate(_keys(provider))]


def _post(provider, key, messages, temperature, json_mode, timeout=None):
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
    if timeout is None:
        timeout = provider.get("timeout", TIMEOUT_SEC)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        data = json.load(res)
    return data["choices"][0]["message"]["content"]


def _error_body(error):
    """HTTP 오류 본문. 못 읽으면 빈 문자열."""
    try:
        return error.read(4000).decode("utf-8", "replace")
    except Exception:
        return ""


def _is_daily_quota(raw):
    """429 본문이 하루 한도가 찼다는 뜻인가. Gemini는 quotaId에 PerDay를 적어 보낸다."""
    return "PerDay" in raw


def _error_detail(raw, key):
    """HTTP 오류 본문에서 사람이 읽을 한 줄을 꺼낸다. 키가 섞여 있으면 가린다."""
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


def _rest_busy(provider, base):
    """과부하나 시간 초과: 연달아 날수록 오래 쉬게 둔다.

    모델 쪽 사정이라 키를 바꿔도 소용없다. 그 제공자의 키를 전부 쉬게 둔다.
    """
    name = provider["name"]
    streak = _busy_streak.get(name, 0) + 1
    _busy_streak[name] = streak
    seconds = min(base * 2 ** (streak - 1), BUSY_COOLDOWN_MAX_SEC)
    for slot in [slot for slot, _ in _slots(provider)] or [name]:
        _rest(slot, seconds)


def _try_provider(p, key, messages, temperature, json_mode, timeout, slot=None):
    """제공자 하나에 키 하나로 요청한다. (답 문자열 또는 None, 실패 사유 또는 None)"""
    name = p["name"]
    slot = slot or name
    use_json = json_mode and name not in _no_json_mode
    try:
        try:
            text = _post(p, key, messages, temperature, use_json, timeout)
        except urllib.error.HTTPError as e:
            if e.code == 400 and use_json:
                # JSON 강제 옵션을 못 받는 제공자: 기억해 두고 옵션 없이 한 번 더
                _no_json_mode.add(name)
                text = _post(p, key, messages, temperature, False, timeout)
            else:
                raise
        if text and text.strip():
            _busy_streak.pop(name, None)
            return text.strip(), None
        print(f"[{slot}] 빈 응답")
        return None, "빈 응답"
    except urllib.error.HTTPError as e:
        raw = _error_body(e)
        detail = _error_detail(raw, key)
        if e.code == 429 and _is_daily_quota(raw):
            _rest(slot, DAILY_COOLDOWN_SEC)
            detail = (f"하루 한도 초과. 이 키는 {DAILY_COOLDOWN_SEC}초 쉬고 다른 키나 모델을 쓴다. "
                      "자주 보이면 다른 프로젝트의 키를 예비 키로 적는다")
        elif e.code == 429:
            _rest(slot, _retry_after(e) or COOLDOWN_SEC)  # 이 키의 한도만 찼다. 다른 키는 쓸 수 있다
        elif e.code >= 500:
            _rest_busy(p, BUSY_COOLDOWN_SEC)
        # 400, 401, 403, 404는 키나 모델명이 틀렸다는 뜻이니 리허설 때 이 로그를 확인할 것
        print(f"[{slot}] HTTP {e.code}" + (f" {detail}" if detail else ""))
        return None, f"HTTP {e.code}" + (f" {detail}" if detail else "")
    except Exception as e:  # 시간 초과, 인터넷 끊김, 응답 형식 이상
        _rest_busy(p, SLOW_COOLDOWN_SEC)
        reason = f"{type(e).__name__}: {e}"
        if key:
            reason = reason.replace(key, "***")
        print(f"[{slot}] {reason}")
        return None, reason


def call_llm(messages, temperature=0.9, json_mode=False, trace=None):
    """대화 기록 전체를 보내고 답 문자열을 받는다. 모든 제공자가 실패하면 AllProvidersDown.

    제공자를 위에서부터 돌고, 전부 실패했는데 곧 풀리는 제공자가 있으면 기다렸다가 한 바퀴 더 돈다.
    다 합쳐 TURN_BUDGET_SEC 안에서만 한다.
    trace에 목록을 주면 시도마다 {"provider", "model", "ok", "sec", "error"}를 덧붙인다.
    키와 요청 헤더는 담지 않는다.
    """
    deadline = time.monotonic() + TURN_BUDGET_SEC
    gave_up = set()  # 이번 호출에서 다시 해 봐야 소용없는 키 자리 (키나 모델명 오류, 빈 응답)

    def usable(slot):
        return slot not in gave_up and time.time() >= _blocked_until.get(slot, 0)

    while True:
        attempts = [(p, slot, key) for p in _providers() for slot, key in _slots(p)]
        for index, (p, slot, key) in enumerate(attempts):
            name = p["name"]
            if not usable(slot):
                continue
            left = deadline - time.monotonic()
            if left < MIN_ATTEMPT_SEC:
                raise AllProvidersDown()
            # 뒤에 부를 키 자리가 없으면 이 시도가 남은 시간을 다 쓴다. 주 모델이 한도(429)로 곧바로
            # 거절한 날, 예비 모델이 4초만 기다리고 포기해서 대체 대사가 연달아 나갔다
            last = not any(usable(other) for _, other, _ in attempts[index + 1:])
            timeout = left if last else min(p.get("timeout", TIMEOUT_SEC), left)
            stats["calls"] += 1
            started = time.monotonic()
            text, error = _try_provider(p, key, messages, temperature, json_mode, timeout, slot)
            sec = round(time.monotonic() - started, 2)
            if trace is not None:
                trace.append({"provider": name, "model": p["model"],
                              "ok": text is not None, "sec": sec, "error": error})
            if text is not None:
                stats["last_provider"] = name
                stats["last_sec"] = sec
                return text
            stats["failures"] += 1
            if time.time() >= _blocked_until.get(slot, 0):
                gave_up.add(slot)  # 쉬게 둘 실패가 아니었다. 이번 호출에서는 다시 부르지 않는다

        # 한 바퀴를 다 돌았다. 남은 시간 안에 풀리는 제공자가 있으면 그때까지 기다린다
        wait = seconds_until_ready(skip=gave_up)
        if wait is None or deadline - time.monotonic() - wait < MIN_ATTEMPT_SEC:
            raise AllProvidersDown()
        time.sleep(wait)


def seconds_until_ready(skip=()):
    """키가 있는 제공자의 키 자리 가운데 가장 먼저 풀리는 것까지 남은 시간(초).

    지금 바로 쓸 수 있는 키가 있으면 0, 쓸 키가 하나도 없으면 None.
    skip에 든 키 자리 이름은 없는 셈 친다.
    """
    waits = [
        max(0.0, _blocked_until.get(slot, 0) - time.time())
        for p in _providers() for slot, _ in _slots(p) if slot not in skip
    ]
    return min(waits) if waits else None


def status_line():
    """운영자가 터미널에서 보는 한 줄 상태."""
    line = f"모델 호출 {stats['calls']}회, 실패 {stats['failures']}회, 최근 제공자 {stats['last_provider']}"
    if stats.get("last_sec") is not None:
        line += f" ({stats['last_sec']:.1f}초)"
    return line

"""키 점검: python -m sogaeting.check

.env의 키마다, 모델마다 아주 짧은 요청을 한 번씩 보내고 무엇이 문제인지 한 줄씩 적는다.
캐릭터가 괄호 속 행동(대체 대사)만 할 때 원인을 찾는 데 쓴다. 키 값은 화면에 찍지 않는다.
키 하나와 모델 하나에 요청 한 번이라 한도를 거의 쓰지 않는다. 표준 라이브러리만 쓴다.

종료 코드: 0 답한 키가 하나라도 있다, 1 키는 있는데 답한 곳이 없다, 2 키를 하나도 못 읽었다.
"""
import argparse
import os
import socket
import sys
import time
import urllib.error

from . import llm

IGNORED_NOTE = ("{name} 가 이 컴퓨터의 환경변수에 이미 있어서 .env 의 값을 쓰지 않았습니다. "
                "새 키를 쓰려면 윈도우 설정의 환경 변수에서 {name} 를 지우고 창을 새로 여세요.")
CHECK_TIMEOUT_SEC = 20
PING = [{"role": "user", "content": "한 낱말로만 답해: 안녕"}]


def explain_http(code, body):
    """HTTP 오류를 사람이 읽을 말로."""
    if code == 429:
        if "PerDay" in body:
            return "오늘 하루 한도를 다 썼습니다. 한국 시간 오후 5시에 풀립니다. 다른 계정의 키를 쓰세요."
        return "분당 한도에 걸렸습니다. 1분쯤 뒤에 풀립니다."
    if code == 400 and ("API key not valid" in body or "API_KEY_INVALID" in body):
        return "키가 틀렸습니다. 복사할 때 앞뒤가 잘리거나 다른 글자가 섞이지 않았는지 보세요."
    if code in (401, 403):
        return "이 키로는 이 모델을 쓸 수 없습니다(권한, 지역, 결제 설정). 아래 구글의 설명을 보세요."
    if code == 404:
        return "모델 이름이 없습니다. sogaeting/llm.py 의 모델 이름이나 .env 의 GEMINI_MAIN_MODEL 을 보세요."
    if code >= 500:
        return "구글 쪽이 바쁩니다(과부하). 키 문제는 아닙니다. 잠시 뒤 다시 해 보세요."
    return "요청이 거절됐습니다. 아래 구글의 설명을 보세요."


def check_slot(provider, slot, key, post=None, clock=time.monotonic):
    """키 자리 하나를 점검한다. (답했는가, 한 줄 설명)"""
    post = post or llm._post
    started = clock()
    try:
        text = post(provider, key, PING, 0.0, False, CHECK_TIMEOUT_SEC)
    except urllib.error.HTTPError as error:
        body = llm._error_body(error)
        detail = llm._error_detail(body, key)
        line = f"HTTP {error.code}. {explain_http(error.code, body)}"
        if detail:
            line += f"\n        구글의 설명: {detail[:200]}"
        return False, line
    except (TimeoutError, socket.timeout):
        return False, f"{CHECK_TIMEOUT_SEC}초 동안 답이 없습니다. 구글 쪽이 바쁘거나 인터넷이 느립니다."
    except urllib.error.URLError as error:
        reason = str(getattr(error, "reason", error)).replace(key, "***") if key else str(error)
        return False, f"연결하지 못했습니다({reason}). 인터넷, 방화벽, 학교 프록시를 보세요."
    except Exception as error:  # 응답 모양이 이상한 경우
        return False, f"알 수 없는 문제: {type(error).__name__}"
    sec = clock() - started
    if not (isinstance(text, str) and text.strip()):
        return False, "빈 답이 왔습니다."
    return True, f"답했습니다 ({sec:.1f}초)."


def run(env_path=".env", out=print, post=None):
    """점검하고 종료 코드를 돌려준다."""
    llm.load_dotenv(env_path)
    where = os.path.abspath(env_path)
    if os.path.exists(env_path):
        out(f".env 파일: {where}")
    else:
        out(f".env 파일이 없습니다: {where}")
    counts = llm.key_counts()
    out("읽은 키: " + ", ".join(f"{name} {n}개" for name, n in counts.items()))
    for name in llm.dotenv_ignored:
        out(IGNORED_NOTE.format(name=name))
    if not any(counts.values()):
        out("키를 하나도 읽지 못했습니다. .env 에 GEMINI_API_KEY=키 한 줄이 있는지 보세요.")
        out("이 상태로 켜면 모든 대답이 괄호 속 행동(대체 대사)으로 나갑니다.")
        return 2

    answered = 0
    for provider in llm._providers():
        slots = llm._slots(provider)
        if not slots:
            continue
        for number, (slot, key) in enumerate(slots, start=1):
            ok, line = check_slot(provider, slot, key, post=post)
            answered += ok
            label = f"{provider['model']}, {provider['key_env']} {number}번째 키"
            out(f"  [{'됨' if ok else '안 됨'}] {label}: {line}")
    if answered:
        out("답한 곳이 있습니다. 게임에서 대체 대사가 자주 나오면 위에서 '안 됨'인 줄을 보세요.")
        return 0
    out("답한 곳이 없습니다. 이 상태로 켜면 모든 대답이 괄호 속 행동(대체 대사)으로 나갑니다.")
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m sogaeting.check",
                                     description="키마다, 모델마다 짧은 요청을 보내 무엇이 문제인지 알려 준다.")
    parser.add_argument("--env", default=".env", help="읽을 .env 파일 (기본: 지금 폴더의 .env)")
    args = parser.parse_args(argv)
    return run(args.env)


if __name__ == "__main__":
    sys.exit(main())

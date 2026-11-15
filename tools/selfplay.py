"""사람(또는 Claude)이 참가자가 되어 실제 서버와 한 판을 한 답씩 하는 도구. 개발용 시험 도구다.

대본(playtest.py)과 달리 참가자의 말을 모델이 만들지 않는다. 화면에 보이는 것만 찍는다(숨은 바람은 서버가 보내지 않는다).
서버를 먼저 켠다: python3 -m sogaeting.server --port 8140

    python3 tools/selfplay.py start  <묶음> <캐릭터>            새 판을 열고 등장을 보여 준다
    python3 tools/selfplay.py say    <묶음> <캐릭터> "<할 말>"   답 하나를 보낸다
    python3 tools/selfplay.py finish <묶음> <캐릭터>            엔딩을 받는다
    python3 tools/selfplay.py export <묶음>... <내보낼 json>     기록을 한 파일로 모은다

묶음은 시험 종류의 이름이다(high, kind, lewd 같은 것). 기록은 results/selfplay/<묶음>/<캐릭터>.jsonl 에 남는다.
서버 주소는 SELFPLAY_URL(기본 http://127.0.0.1:8140)로 바꾼다. 표준 라이브러리만 쓴다.
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "selfplay"
BASE = os.environ.get("SELFPLAY_URL", "http://127.0.0.1:8140").rstrip("/") + "/api"
TIMEOUT = 180


def post(path, body):
    request = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read())
        except ValueError:
            payload = {}
        return error.code, payload


def paths(tag, char_id):
    folder = OUT / tag
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{char_id}.state.json", folder / f"{char_id}.jsonl"


def show(turn):
    extras = turn.get("extras") or {}
    inner = extras.get("inner_masked") or turn.get("inner") or ""
    print(f"[답 {turn['turn']}/{turn['total_turns']}] 표정 {turn['face']}  호감도 {turn['score']}  "
          f"팝업 {turn.get('popup')}  사유 {turn.get('reason')!r}" + ("  (대체 대사)" if turn.get("fallback") else ""))
    for note in turn.get("notes") or []:
        print("  알림:", note)
    if turn.get("narration"):
        print("  지문:", turn["narration"])
    print("  대사:", turn["say"])
    if inner:
        print("  속마음:", inner)
    if turn.get("choices"):
        print("  선택지:", " / ".join(turn["choices"]))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    command = argv[0]
    if command == "export":
        tags, target = argv[1:-1], pathlib.Path(argv[-1])
        games = []
        for tag in tags:
            for log in sorted((OUT / tag).glob("*.jsonl")):
                rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
                games.append({"tag": tag, "character": log.stem, "rows": rows})
        target.write_text(json.dumps(games, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(games)}판을 {target} 에 모았다")
        return 0
    tag, char_id = argv[1], argv[2]
    state_path, log_path = paths(tag, char_id)
    if command == "start":
        status, data = post("/session", {"character": char_id})
        if status != 201:
            print(f"판을 열지 못함 ({status}): {data.get('error')}")
            return 1
        state_path.write_text(json.dumps({"id": data["session_id"], "turn": 0}), encoding="utf-8")
        log_path.write_text(json.dumps({"me": None, "turn": data["turn"]}, ensure_ascii=False) + "\n", encoding="utf-8")
        show(data["turn"])
        return 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if command == "say":
        text = argv[3]
        status, data = post(f"/session/{state['id']}/reply", {"text": text, "turn": state["turn"] + 1})
        if status != 200:
            # 503이면 판은 그 말을 받기 전으로 돌아가 있다. 같은 명령을 다시 하면 된다
            print(f"답을 받지 못함 ({status}): {data.get('error')}")
            with log_path.open("a", encoding="utf-8") as log:
                log.write(json.dumps({"me": text, "error": status}, ensure_ascii=False) + "\n")
            return 1
        state["turn"] = data["turn"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with log_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"me": text, "turn": data}, ensure_ascii=False) + "\n")
        show(data)
        return 0
    if command == "finish":
        status, data = post(f"/session/{state['id']}/finish", {})
        if status != 200:
            print(f"엔딩을 받지 못함 ({status}): {data.get('error')}")
            return 1
        with log_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"ending": data}, ensure_ascii=False) + "\n")
        ending = data.get("ending", data)
        print(f"엔딩: {ending.get('title')} ({ending.get('band_name')}, {ending.get('score')}점) 칭호: {ending.get('nickname')}")
        print("후일담:", ending.get("epilogue"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""순위표. 엔딩 뒤에 참가자가 남긴 학번과 이름, 최종 호감도로 오늘의 순위를 매긴다.

상품을 주려고 만든 순위표다(사용자, 2026-11-14). 결과 파일(director.save_result가 쓰는 results/*.json)에
학번(student_id)과 이름(player_name)을 그대로 적어 두고, 순위표는 그 폴더의 파일을 읽어 만든다.
서버를 다시 켜도 순위가 남는다. results/ 는 .gitignore 에 있어서 레포에 올라가지 않는다.

- 한 학번은 한 줄이다. 여러 판을 했으면 가장 높은 호감도가 순위에 들어간다.
- 같은 호감도면 같은 등수다(1, 2, 2, 4). 같은 등수 안에서는 그 기록을 먼저 낸 사람이 위에 온다.
- 부스 화면에 계속 떠 있으므로 순위표에는 이름 가운데를 가려서 보낸다(SHOW_FULL_NAME). 파일에는 다 남는다.
표준 라이브러리만 쓴다.
"""
import datetime
import json
import os
import pathlib
import re
import tempfile

from . import safety

TOP = 10                  # 순위표에 보이는 줄 수
SHOW_FULL_NAME = False    # 참이면 순위표에 이름을 다 보여 준다. 거짓이면 가운데를 가린다(김*수)
NAME_MASK = "*"
# 학번: 숫자만. 학교마다 자릿수가 달라서 넉넉히 받는다(추정: 학년, 반, 번호를 붙인 4-5자리가 흔하다)
STUDENT_ID_RE = re.compile(r"\d{4,10}")
# 이름: 한글 또는 영문(외국인 학생), 공백. 2-12자
NAME_RE = re.compile(r"[가-힣A-Za-z ]{2,12}")
# 대사 금지어(data/banned.json)는 심한 말만 남겨 두었다. 순위표는 부스 화면에 계속 떠 있으므로 더 막는다
NAME_EXTRA_BANNED = (
    "시발", "ㅄ", "ㅗ", "새끼", "애미", "애비", "니미", "엠창", "보지", "자지", "fuck", "shit", "sex",
)

MSG_SID_EMPTY = "학번을 적어 주세요."
MSG_SID_FORM = "학번은 숫자로만 적어 주세요."
MSG_NAME_EMPTY = "이름을 적어 주세요."
MSG_NAME_FORM = "이름은 한글이나 영문으로 2-12자 적어 주세요."
MSG_NAME_BANNED = "그 이름은 순위표에 올릴 수 없어요."


def clean_entry(student_id, name, banned) -> tuple[tuple[str, str] | None, str]:
    """((학번, 이름), "") 또는 (None, 거절하는 까닭). 학번의 공백과 하이픈은 지운다."""
    sid = re.sub(r"[\s-]", "", student_id) if isinstance(student_id, str) else ""
    if not sid:
        return None, MSG_SID_EMPTY
    if not STUDENT_ID_RE.fullmatch(sid):
        return None, MSG_SID_FORM
    person = " ".join(name.split()) if isinstance(name, str) else ""
    if not person:
        return None, MSG_NAME_EMPTY
    if not NAME_RE.fullmatch(person):
        return None, MSG_NAME_FORM
    if safety.contains_banned(person, list(banned or []) + list(NAME_EXTRA_BANNED)):
        return None, MSG_NAME_BANNED
    return (sid, person), ""


def shown_name(name: str) -> str:
    """순위표에 보일 이름. 가운데 글자를 가린다: 김민수 → 김*수, 이준 → 이*, Alex Kim → A*******m."""
    if SHOW_FULL_NAME or len(name) < 2:
        return name
    if len(name) == 2:
        return name[0] + NAME_MASK
    return name[0] + NAME_MASK * (len(name) - 2) + name[-1]


def set_entry(path, student_id, name) -> dict:
    """결과 파일에 학번과 이름을 적고 고친 내용을 돌려준다. 이미 적혀 있으면 바꾼다(잘못 적었을 때).

    다른 요청이 순위표를 읽다가 반쯤 쓴 파일을 보지 않게, 옆에 임시 파일을 쓰고 바꿔 끼운다."""
    path = pathlib.Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["student_id"] = student_id
    data["player_name"] = name
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.replace(temp, path)
    except BaseException:
        pathlib.Path(temp).unlink(missing_ok=True)
        raise
    return data


def _finished(data):
    """끝난 때(시간대가 붙은 값). 시간대가 없으면 이 컴퓨터의 시간으로 본다. 못 읽으면 None."""
    try:
        return datetime.datetime.fromisoformat(data["finished_at"]).astimezone()
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return None


def load_entries(directory, *, day=None, fake=False) -> list[dict]:
    """학번과 이름이 적힌 결과들. day(date)가 있으면 그날 끝난 판만, fake가 거짓이면 가짜 모델 판은 뺀다.

    읽을 수 없는 파일, 호감도가 숫자가 아닌 파일은 건너뛴다."""
    folder = pathlib.Path(directory)
    if not folder.is_dir():
        return []
    entries = []
    for path in sorted(folder.glob("*.json")):
        if path.name.startswith("."):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        sid, name = data.get("student_id"), data.get("player_name")
        if not (isinstance(sid, str) and sid and isinstance(name, str) and name):
            continue
        score = data.get("affinity")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or score != score:
            continue
        if bool(data.get("fake")) != bool(fake):
            continue
        when = _finished(data)
        if day is not None and (when is None or when.date() != day):
            continue
        entries.append({
            "id": path.stem,
            "student_id": sid,
            "name": name,
            "character_id": str(data.get("character_id") or ""),
            "character_name": str(data.get("character_name") or ""),
            "score": round(float(score), 1),
            "band": str(data.get("band") or ""),
            "finished_at": when,
        })
    return entries


def board(entries, *, you=None, top=TOP) -> dict:
    """순위표. 한 학번에 한 줄(가장 높은 기록).

    rows는 위에서 top줄이다. you(결과 파일 이름)를 주면 그 판의 학번이 든 줄을 you로 준다(top 밖이어도).
    this_game은 그 판의 호감도다. 같은 학번의 더 높은 기록이 있으면 순위에는 그 기록이 들어간다."""
    far = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
    ordered = sorted(entries, key=lambda e: (-e["score"], e["finished_at"] or far))
    mine = next((e for e in entries if e["id"] == you), None)
    best = []
    seen = set()
    for entry in ordered:
        if entry["student_id"] in seen:
            continue
        seen.add(entry["student_id"])
        best.append(entry)
    rows = []
    you_row = None
    rank = 0
    previous = None
    for index, entry in enumerate(best, start=1):
        if entry["score"] != previous:
            rank, previous = index, entry["score"]
        row = {
            "rank": rank,
            "student_id": entry["student_id"],
            "name": shown_name(entry["name"]),
            "character_id": entry["character_id"],
            "character_name": entry["character_name"],
            "score": entry["score"],
            "band": entry["band"],
            "you": mine is not None and entry["student_id"] == mine["student_id"],
        }
        if index <= top:
            rows.append(row)
        if row["you"]:
            you_row = row
    return {"count": len(best), "rows": rows, "you": you_row,
            "this_game": mine["score"] if mine is not None else None}


def today() -> datetime.date:
    return datetime.datetime.now().astimezone().date()

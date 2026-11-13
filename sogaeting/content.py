"""내용 데이터 불러오기.

캐릭터, 씨앗, 연출 목록, 진행표, 금지어, 엔딩 등급을 sogaeting/data/ 안의 JSON에서 읽는다.
내용을 고치거나 더할 때는 코드를 건드리지 않고 JSON 파일만 바꾼다.
표준 라이브러리만 쓴다.
"""
import json
import pathlib

# 이 파일이 있는 자리를 기준으로 찾는다. 어디서 실행해도 같은 폴더를 읽는다.
DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"

# 캐릭터 파일에 반드시 있어야 하는 키
CHARACTER_KEYS = (
    "id", "name", "attribute", "motif", "call", "attitude", "by_affinity",
    "speech", "never", "reactions", "examples", "likes", "dislikes",
    "max_brain", "gimmick", "color", "fallback_lines",
)
# 그 가운데 dict인 칸이 안에 반드시 갖춰야 하는 키
NESTED_KEYS = {
    "motif": ("name", "explain"),
    "by_affinity": ("low", "mid", "high"),
}


def _read_json(path: pathlib.Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# 2026-11-13에 바꾸기 전의 캐릭터 id. 예전 주소(?character=haru)나 예전 결과를 읽는 쪽에서 불러도 되게 받아 준다
OLD_IDS = {"giulhee": "astra", "oeun": "gemma", "anna": "sora", "relu": "nova", "haru": "mistral", "boxhyun": "haiku"}


def list_character_ids() -> list[str]:
    """캐릭터 식별자 목록. 파일 이름 순서다."""
    return sorted(p.stem for p in (DATA_DIR / "characters").glob("*.json"))


def load_character(char_id: str) -> dict:
    """캐릭터 한 명의 설정. 없는 식별자면 KeyError, 필수 키가 빠졌으면 ValueError."""
    # 목록에 있는 이름만 받는다. 주소로 넘어온 값이 다른 폴더의 파일을 가리키지 못하게 한다.
    char_id = OLD_IDS.get(char_id, char_id) if isinstance(char_id, str) else char_id
    if char_id not in list_character_ids():
        raise KeyError(char_id)
    data = _read_json(DATA_DIR / "characters" / f"{char_id}.json")
    if not isinstance(data, dict):
        raise ValueError(f"{char_id}.json: 내용이 객체가 아니다")
    missing = [key for key in CHARACTER_KEYS if key not in data]
    for parent, keys in NESTED_KEYS.items():
        if parent not in data:
            continue
        inner = data[parent] if isinstance(data[parent], dict) else {}
        missing += [f"{parent}.{key}" for key in keys if key not in inner]
    if missing:
        raise ValueError(f"{char_id}.json: 빠진 키 {', '.join(missing)}")
    return data


def load_seeds() -> dict:
    """씨앗 낱말. {"entrance": [...], "event": [...], "event_places": {사건: [그 사건이 일어날 수 있는 장소]}}

    event_places에 없는 사건은 어느 장소에서나 일어날 수 있다.
    """
    return _read_json(DATA_DIR / "seeds.json")


def load_fx() -> dict:
    """연출 이름. {"light": [...], "heavy": [...]}"""
    return _read_json(DATA_DIR / "fx.json")


def load_schedule() -> dict:
    """한 판의 진행표. 등장, 답 목록, 강도별 뜻."""
    return _read_json(DATA_DIR / "schedule.json")


def load_banned() -> list[str]:
    """금지어 목록."""
    return _read_json(DATA_DIR / "banned.json")


def load_endings() -> list[dict]:
    """엔딩 등급 목록. min이 큰 것부터 나온다."""
    return sorted(_read_json(DATA_DIR / "endings.json"), key=lambda e: e["min"], reverse=True)

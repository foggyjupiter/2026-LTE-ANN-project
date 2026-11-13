"""터미널 실행기: python3 -m sogaeting [캐릭터 id] [--fake]

화면 없이 한 판을 끝까지 돌려 본다. 모델이 실제로 웃기게 치는지 보는 용도다.
"""
import argparse
import os

from . import content, llm
from .director import Session, save_result
from .fake_llm import fake_llm

LINE = "-" * 44
BAND_NAMES = {"low": "낮음", "mid": "보통", "high": "높음"}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python3 -m sogaeting", description="소개팅 한 판을 터미널에서 돌린다.")
    parser.add_argument("character", nargs="?", help="캐릭터 id. 없으면 목록에서 고른다")
    parser.add_argument("--fake", action="store_true", help="실제 모델 대신 가짜 모델을 쓴다")
    args = parser.parse_args(argv)

    llm.load_dotenv()
    try:
        return _run(args.character, args.fake)
    except (KeyboardInterrupt, EOFError):
        print()  # 입력이 끊기면 조용히 끝낸다. 결과는 남기지 않는다
        return 0


def _run(character_id, use_fake):
    ids = content.list_character_ids()
    if character_id is None:
        character_id = _choose_character(ids)
    elif character_id not in ids:
        print(f"모르는 캐릭터입니다: {character_id}")
        print("고를 수 있는 id: " + ", ".join(ids))
        return 2

    if use_fake:
        print("가짜 모델로 진행합니다.")
    elif not any(os.environ.get(p["key_env"]) for p in llm.PROVIDERS):
        print("API 키가 없어서 대체 대사만 나옵니다. 흐름만 보려면 --fake를 붙이세요.")

    session = Session(character_id, llm=fake_llm if use_fake else None)
    name = session.character["name"]
    out = session.start()
    _print_turn(name, out)
    masked = "inner_masked" in out["extras"]
    while not out["finale"]:
        text = _ask(out["choices"])
        if text is None:  # q: 곧장 엔딩으로
            break
        try:
            out = session.reply(text)
        except ValueError:
            print("빈 입력은 보낼 수 없어요.")
            continue
        _print_turn(name, out)
        masked = masked or "inner_masked" in out["extras"]

    _print_ending(session.finish(), reveal_inners=masked)
    path = save_result(session.result())
    print(f"결과 저장: {path}")
    print(llm.status_line())
    return 0


def _choose_character(ids):
    """여섯 명을 보여 주고 번호로 고르게 한다."""
    print("소개팅 상대를 고르세요.")
    for number, char_id in enumerate(ids, start=1):
        character = content.load_character(char_id)
        print(f"  {number}. {character['name']} [{character['attribute']}]")
    while True:
        index = _number(input(f"번호 (1-{len(ids)}) > ").strip(), len(ids))
        if index is not None:
            return ids[index]
        print("목록에 있는 번호를 쳐 주세요.")


def _ask(choices):
    """참가자 입력을 받는다. 번호를 치면 그 선택지, q를 치면 None."""
    for number, choice in enumerate(choices, start=1):
        print(f"  {number}) {choice}")
    hint = "번호 또는 직접 입력" if choices else "직접 입력"
    while True:
        text = input(f"[{hint}, q는 엔딩으로] > ").strip()
        if not text:
            print("빈 입력은 보낼 수 없어요.")
            continue
        if text.lower() == "q":
            return None
        index = _number(text, len(choices))
        if index is not None:
            text = choices[index]
        print(f"나: {text}")
        return text


def _number(text, count):
    """text가 1부터 count까지의 번호면 0부터 세는 자리를, 아니면 None을 돌려준다."""
    if text.isascii() and text.isdigit() and 1 <= int(text) <= count:
        return int(text) - 1
    return None


def _print_turn(name, out):
    extras = out["extras"]
    head = "등장" if out["turn"] == 0 else f"답 {out['turn']}/{out['total_turns']}"
    print(LINE)
    print(f"[{head}]" + (" (대체 대사)" if out["fallback"] else ""))
    if out["heard"]:
        print(f"들은 말: {out['heard']}")
    if out["narration"]:
        print(f"지문: {out['narration']}")
    print(f"{name}: {extras.get('say_marked', out['say'])}")
    inner = extras.get("inner_masked", out["inner"])
    if inner:
        print(f"속마음: {inner}")
    if extras.get("highlights"):
        print("형광펜: " + ", ".join(extras["highlights"]))
    if out["fx"]:
        print("연출: " + ", ".join(out["fx"]))
    if out["popup"] is not None:
        reason = f" (사유: {out['reason']})" if out["reason"] else ""
        print(f"팝업: {out['popup']}{reason}")
    for note in out["notes"]:
        print(f"알림: {note}")
    print(f"호감도: {out['score']}/100 ({BAND_NAMES[out['band']]})")


def _print_ending(ending, *, reveal_inners):
    print("=" * 44)
    print(f"[엔딩] {ending['character_name']} / {ending['band_name']}")
    print(ending["title"])
    if ending["epilogue"]:
        print(ending["epilogue"])
    if ending["nickname"]:
        print(f"칭호: {ending['nickname']}")
    print(f"최종 호감도: {ending['score']}/100")
    if ending["best_line"]:
        print(f"이번 판의 명대사: {ending['best_line']}")
    if ending["early"]:
        print("(답을 다 채우기 전에 끝낸 판입니다)")
    if reveal_inners:  # 속마음을 가리던 캐릭터는 엔딩에서 전부 공개한다
        print("가려져 있던 속마음:")
        for turn, inner in enumerate(ending["inners"]):
            if inner:
                label = "등장" if turn == 0 else f"답 {turn}"
                print(f"  {label}: {inner}")
    print("=" * 44)

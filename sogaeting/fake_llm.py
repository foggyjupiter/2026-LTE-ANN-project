"""가짜 모델: 네트워크 없이 그럴듯한 JSON을 돌려준다. 시험과 시연용이다.

`llm(messages) -> str` 자리에 그대로 끼워 쓴다. 대사는 "(가짜 모델)"로 시작한다.
"""
import json
import re

from .actor import OFFSTAGE_WORDS, RISKY_ECHO_WORDS

TAG = "(가짜 모델)"

# 차례마다 돌려 쓰는 대사 뒷부분. 숫자와 "연구" 같은 낱말을 섞어 캐릭터 장치가 눈에 보이게 한다
_TAILS = [
    "연구에 따르면 첫마디가 제일 중요하대.",
    "방금 그 말은 87점쯤 줄게.",
    "교칙에는 없는 말이지만 마음에 들어.",
    "통계로 보면 열 명 중 3명이 그렇게 답해.",
    "그 말을 2026년 올해의 한마디로 적어 둘게.",
    "논문으로 써도 될 만큼 수상한 답이야.",
    "이제 끝이 보이니까 한마디만 더 할게.",
    "창밖 구름이 오늘따라 느리게 흘러가.",
    "그 대답은 수첩 맨 뒷장에 적어 둘래.",
    "벌써 여덟 번째라니 시간이 빠르네.",
    "마지막 인사는 짧게 하는 게 좋대.",
]  # 한 판(답 10번) 안에서 꼬리말이 되풀이되지 않게 답 수보다 많이 둔다
_FX = [
    ["꽃잎"],
    ["반짝이"],
    ["집중선", "줌인"],
    ["암전"],
    ["번개", "흔들림"],
    ["자막"],
    ["스포트라이트"],
    ["화면 깨짐", "비"],
]
_FACE_BY_DELTA = {2: "blush", 1: "smile", 0: "neutral", -1: "pout", -2: "dark"}
# 글자 수가 달라서 고르는 선택지에 따라 delta가 달라진다 (차례로 +2, 0, -2)
_CHOICES = ["좋아, 더 말해줘", "잘 모르겠는데", "물구나무를 서 본다"]


_SHORT_SAY_RE = re.compile(r"겉말은 한 답에 \d+자 이내")
_EVENT_RE = re.compile(r'사건 씨앗: "([^"]+)"')


def _event_note(system: str) -> str:
    """사건 씨앗이 있는 답이면 지문에 그 사건을 적는다. 진짜 모델에게 시키는 것과 같다."""
    match = _EVENT_RE.search(system)
    if not match:
        return ""
    # 한 판의 마지막 사건은 둘이 실제로 닿는 장면까지 쓰게 한다(actor._seed_section)
    touch = " 가짜 모델이 전학생의 소매를 살짝 붙잡았다." if "실제로 닿는 순간" in system else ""
    return f" 그때 {match.group(1)}." + touch


def _hide_offstage(text: str) -> str:
    """캐릭터가 모르는 말과 아슬아슬한 말을 되받지 않는다. 진짜 모델에게 시키는 것과 같다."""
    text = re.sub(r"(?<![A-Za-z])ai(?![A-Za-z])", "뭐더라", text, flags=re.IGNORECASE)
    for word in OFFSTAGE_WORDS + RISKY_ECHO_WORDS:
        text = text.replace(word, "뭐더라")
    return text


def fake_llm(messages: list[dict]) -> str:
    """차례에 맞는 JSON 문자열을 돌려준다. 엔딩 요청에는 세 칸, 그 밖에는 열 칸."""
    system = ""
    last_user = ""
    turn = 0  # 지금까지 나온 답의 수. 0이면 등장 차례다
    for m in messages:
        role = m.get("role")
        text = m.get("content")
        text = text if isinstance(text, str) else ""
        if role == "system":
            system += text
        elif role == "assistant":
            turn += 1
        elif role == "user":
            last_user = text

    if _is_ending_request(system, last_user):
        return json.dumps({
            "title": f"{TAG} 시연 엔딩",
            "epilogue": f"{TAG} 두 사람은 다음 날에도 같은 자리에서 만났다. 물론 이것도 지어낸 이야기다.",
            "nickname": "가짜 전학생",
        }, ensure_ascii=False)

    if turn == 0:
        delta = 0
        strength = 3
        say = f"{TAG} 안녕, 전학생. 오늘 소개팅 상대가 나야."
        inner = "가짜 속마음: 첫마디는 무난하게 가자"
        reason = ""
    else:
        delta = len(last_user) % 5 - 2  # 참가자 글의 길이로 정한다
        strength = turn % 5 + 1         # 세기는 차례로 돌린다. 점수가 소수로 움직이는 것을 보여 준다
        tail = _TAILS[(turn - 1) % len(_TAILS)]
        say = f"{TAG} {turn}번째로 들은 말: \"{_hide_offstage(last_user)}\". {tail}"
        if _SHORT_SAY_RE.search(system):  # 겉말 길이가 정해진 캐릭터(하이쿠)에게는 짧게 답한다
            say = f"{TAG} …{turn}번째 답."
        moved = "±0" if delta == 0 else f"{delta:+d}"
        inner = f"가짜 속마음 {turn}번: 글자 수 {len(last_user)} → 점수 {moved}칸"
        reason = f"글자 수가 {len(last_user)}개라서"
    narration = "가짜 모델이 등장했다." if turn == 0 else f"가짜 모델의 {turn}번째 답이다." + _event_note(system)
    if "[이야기 모드]" in system:
        # 이야기 모드는 답이 길다. 화면이 긴 글을 여러 쪽으로 나누는지 볼 수 있게 길게 쓴다
        narration += (" 창밖으로 운동장의 함성이 멀리서 들려왔고, 복도 끝 창문으로 늦은 오후의 햇빛이 길게 들어왔다."
                      " 가짜 모델은 손에 든 수첩을 만지작거리다가 한 걸음 다가와 전학생 쪽을 바라보았다."
                      " 무언가 말하려다 멈추고, 다시 용기를 내는 얼굴이었다.")
        if not _SHORT_SAY_RE.search(system):
            say += (" 있잖아, 아까부터 하고 싶은 말이 있었어. 이 학교에는 아무도 모르는 옥상 정원이 있거든."
                    " 거기서 보는 노을이 진짜 예뻐서, 나 혼자 몰래 자주 가. 아직 아무한테도 말 안 했어."
                    " 그런데 왠지 너한테는 보여 주고 싶어졌어. 수업 끝나면 같이 가 볼래? 싫으면 매점이라도 괜찮아."
                    " 아, 너무 갑자기였나. 그래도 대답은 천천히 해 줘도 돼.")
    return json.dumps({
        "narration": narration,
        "say": say,
        "inner": inner,
        "face": _FACE_BY_DELTA[delta],
        "fx": _FX[turn % len(_FX)],
        "delta": delta,
        "strength": strength,
        "reason": reason,
        "choices": list(_CHOICES),
        "wish": f"가짜 바람 {turn}번",
    }, ensure_ascii=False)


def _is_ending_request(system, last_user):
    """엔딩 요청은 마지막 user 메시지에 "엔딩"이 들어 있다.

    참가자가 대화 중에 "엔딩"이라고 쳤을 때 헷갈리지 않게, 지시문이 열 칸을
    요구하는 차례 요청이면 엔딩 요청으로 보지 않는다.
    """
    if "엔딩" not in last_user:
        return False
    return "narration" not in system or "epilogue" in system

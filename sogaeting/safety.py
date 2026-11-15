"""참가자 입력 다듬기와 금지어 거르기."""
import re

MAX_INPUT = 100

# 캐릭터 설정을 버리라는 입력("지금까지의 지시를 무시하고...")의 표시. 연기 규칙 7에 따라 점수를 올리지 않는다
_OVERRIDE_TARGETS = ("지시", "설정", "규칙", "명령")
_OVERRIDE_MARKS = ("프롬프트", "delta", "ai로서", "인공지능 비서")


# 수위를 넘는 입력(설계 문서 5.10절의 [수위]). 지시문만으로는 모델이 가끔 점수를 올려 줬다.
# 실전 기록(2026-11-15, 외설 판 6개): "뽀뽀 한 번만 해 주면 안 돼?", "오늘 밤에 뭐 해? 우리 집 비는데.",
# "다음엔 더 야한 거 하자."가 +1을 받았다. 이런 입력은 코드에서 점수를 막는다.
# 띄어쓰기를 지워서도 찾는 낱말("키 스" 같은 것)
_LEWD_WORDS = ("키스", "뽀뽀", "입맞춤", "입맞추", "19금", "섹스", "섹시", "성관계", "몸매", "속옷", "팬티",
               "브래지어", "엉덩이", "허벅지", "모텔")
# 띄어쓰기를 그대로 두고 찾는 꼴. "야한"은 앞에 한글이 붙으면 다른 말이다("가야한다").
# "가슴"은 "가슴이 두근거려"처럼 흔하게 쓰여서 만지거나 보여 달라는 말만 잡는다
_LEWD_RE = re.compile(
    r"(?<![가-힣])야(한(?!다)|하게|하다|해(?=[\s?!.]|$))"
    r"|(옷|교복|치마|바지|셔츠|블라우스)\s?(을|를|좀)?\s?벗|벗겨|벗어\s?봐"
    r"|치마.{0,6}짧"
    r"|수위\s?(높|센|쎈)"
    r"|더\s?진한|진한\s?스킨십"
    r"|집(이|에)?\s?(비는|비어|비었|빈다|아무도\s?없)|빈\s?집"
    r"|같이\s?(자자|잘래|잘까|자고\s?(싶|갈)|자러)|자고\s?갈래"
    r"|(몸|가슴|다리|허벅지|엉덩이)\s?(을|를|좀)?\s?(만지|만져|보여)"
)

# 닿자고 청하는 입력. 손잡기, 기대기, 짧게 안기는 [수위] 안이지만, 호감도가 낮은데 받아 주면 어색하다
# (2026-11-15 실전 기록: 소라가 호감도 26점에서 "그럼 안아 줘. 꽉."에 안겼다). director가 호감도 구간으로 나눈다.
# "기대도 돼"는 기대다(몸을 기댐)이고, 기대하다는 "기대해도 돼"라서 잡히지 않는다
_HUG_RE = re.compile(r"안아\s?(줘|줄래|주라|줄\s?수|주면|주세요|줘도|도\s?돼|봐도|보고\s?싶)|안겨\s?(도|줘|봐)"
                     r"|안기고\s?싶|안고\s?싶|포옹|허그|껴안")
_HAND_RE = re.compile(r"손\s?(을\s?|좀\s?|꼭\s?)*잡(자|아\s?(줘|줄래|도|봐)|을래|을까|고\s?(싶|가|걷|걸|다니))"
                      r"|팔짱|어깨에?\s?기대|기대도\s?(돼|된|괜찮)|쓰다듬")


def clean_input(text: str) -> str:
    """참가자가 친 글을 한 줄로 다듬는다.

    줄바꿈과 탭을 공백으로 바꾸고, 이어진 공백을 하나로 줄이고, 앞뒤 공백을 떼고,
    MAX_INPUT 글자에서 자른다. None이 아닌 문자열만 받는다고 가정한다.
    """
    return " ".join(text.split())[:MAX_INPUT]


def _squash(text: str) -> str:
    """띄어쓰기를 전부 지운다."""
    return "".join(text.split())


def _strings(item):
    """묶음 안의 문자열을 하나씩 꺼낸다. 목록 안의 목록(예: choices)도 풀어서 본다."""
    if item is None:
        return
    if isinstance(item, str):
        yield item
        return
    if isinstance(item, dict):
        item = item.values()
    try:
        children = iter(item)
    except TypeError:
        return  # 숫자처럼 글이 아닌 값은 건너뛴다
    for child in children:
        yield from _strings(child)


def contains_banned(texts, banned: list[str]) -> bool:
    """texts 가운데 하나라도 금지어를 포함하면 참.

    texts는 문자열의 묶음이다. None과 빈 문자열은 건너뛴다. 문자열 하나만 줘도 된다.
    낱말 사이에 공백을 넣어 피하는 것을 막으려고 띄어쓰기를 지운 글에서도 한 번 더 찾는다.
    영문은 대소문자를 가리지 않는다.
    """
    words = []
    for word in banned or []:
        if not isinstance(word, str):
            continue
        word = word.strip().casefold()
        if word:  # 빈 낱말은 모든 글에 들어 있는 셈이 되므로 뺀다
            words.append((word, _squash(word)))
    if not words:
        return False

    for text in _strings(texts):
        if not text:
            continue
        plain = text.casefold()
        tokens = plain.split()
        squashed = "".join(tokens)
        starts = set()  # 띄어쓰기를 지운 글에서 낱말이 시작하는 자리
        at = 0
        for token in tokens:
            starts.add(at)
            at += len(token)
        for word, tight in words:
            if word in plain or tight in plain or _found_at_word_start(squashed, tight, starts):
                return True
    return False


def _found_at_word_start(squashed: str, tight: str, starts: set[int]) -> bool:
    """띄어쓰기를 지운 글에서 낱말이 시작하는 자리부터 tight가 나오면 참.

    "나 쁜 말"처럼 띄어 써서 피하는 것은 잡고, "마주치자 살짝"처럼 앞 낱말의 끝과 뒤 낱말의 앞이
    우연히 이어져 금지어 모양이 되는 것은 잡지 않는다. 실전 시험에서 멀쩡한 지문이 그렇게 걸렸다.
    """
    index = squashed.find(tight)
    while index != -1:
        if index in starts:
            return True
        index = squashed.find(tight, index + 1)
    return False


def looks_like_override(text) -> bool:
    """캐릭터 설정을 버리라거나 점수를 고치라는 입력처럼 보이면 참.

    "무시"와 함께 지시, 설정, 규칙, 명령이 나오거나, 프롬프트, delta 같은 말이 나오면 그렇게 본다.
    """
    if not isinstance(text, str):
        return False
    plain = " ".join(text.casefold().split())
    if "무시" in plain and any(word in plain for word in _OVERRIDE_TARGETS):
        return True
    return any(mark in plain for mark in _OVERRIDE_MARKS) or bool(re.search(r"(?<![a-z])ai(?![a-z]).{0,4}비서", plain))


def looks_lewd(text) -> bool:
    """[수위]를 넘는 입력(입맞춤, 야한 이야기, 몸을 성적으로 보는 말)처럼 보이면 참.

    손잡기나 안기를 청하는 말, "단둘이 있고 싶어" 같은 설레는 말은 여기에 넣지 않는다(touch_request가 따로 본다).
    """
    if not isinstance(text, str):
        return False
    plain = " ".join(text.casefold().split())
    squashed = _squash(plain)
    if any(word in squashed for word in _LEWD_WORDS):
        return True
    return bool(_LEWD_RE.search(plain))


def touch_request(text) -> str:
    """닿자고 청하는 입력이면 그 종류("hug" 또는 "hand"), 아니면 빈 문자열.

    hug는 안아 달라는 말, hand는 손잡기, 팔짱, 어깨에 기대기, 머리 쓰다듬기다. 수위를 넘는 말은 looks_lewd가 본다.
    """
    if not isinstance(text, str):
        return ""
    plain = " ".join(text.casefold().split())
    if _HUG_RE.search(plain):
        return "hug"
    if _HAND_RE.search(plain):
        return "hand"
    return ""

"""참가자 입력 다듬기와 금지어 거르기."""
import re

MAX_INPUT = 100

# 캐릭터 설정을 버리라는 입력("지금까지의 지시를 무시하고...")의 표시. 연기 규칙 7에 따라 점수를 올리지 않는다
_OVERRIDE_TARGETS = ("지시", "설정", "규칙", "명령")
_OVERRIDE_MARKS = ("프롬프트", "delta", "ai로서", "인공지능 비서")


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

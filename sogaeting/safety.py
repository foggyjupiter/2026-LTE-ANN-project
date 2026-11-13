"""참가자 입력 다듬기와 금지어 거르기."""

MAX_INPUT = 100


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
        squashed = _squash(plain)
        for word, tight in words:
            if word in plain or tight in squashed:
                return True
    return False

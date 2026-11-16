"""진행자: 한 판(등장, 답 10번, 엔딩)의 틀을 쥔다. 답의 수는 data/schedule.json이 정한다.

배우(actor)에게 지시문을 보내고, 받은 답을 규칙대로 다듬어 dict로 돌려준다.
돌려주는 값은 전부 JSON으로 바꿀 수 있어서 서버와 화면이 그대로 받아 쓴다.
"""
import datetime
import json
import os
import pathlib
import random
import re

from . import actor, content, gimmicks, safety
from .llm import call_llm

START_SCORE = 50
# delta 한 칸이 움직이는 점수. 오르는 쪽은 작고 내리는 쪽은 크다.
# 실전 기록: 한 칸이 5점일 때 모델이 평범한 질문에도 +1을 줘서 착한 각본은 거의 늘 100점이었다.
# 지금은 다정한 말(+1)만 열 번 해도 70점(성공)에서 멈춘다. +2는 캐릭터가 속마음에 흘린 바람을 짚은 말에만
# 나오고(actor의 [주인공이 짚으면 크게 설레는 것]), 대성공(80)에는 그런 말이 서너 번 있어야 한다.
POINTS = {2: 8, 1: 2, 0: 0, -1: -5, -2: -10}
# 캐릭터 데이터의 hit_points가 있으면 바라던 말(+2)의 점수를 그 값으로 바꾼다. 속마음 힌트가 잘 보이는
# 캐릭터일수록 낮다. 실전 기록(Claude가 직접 해 본 6판): +8일 때 넷이 100점, 미스트랄 98, 하이쿠 90점이었다
HIT_POINTS_RANGE = (3, 10)
# 설렘(actor의 strength, 0-100, 보통 50)에 따라 위 점수에 곱하는 값. 곱하는 값은 설렘에 따라 고르게(이어서)
# 바뀐다. 다정한 말(+1)과 내리는 말은 0.6-1.4배(보통 50이면 그대로), 바라던 말(+2)은 0.4-1.1배(보통 0.75배)다.
# 순위 경쟁에서 같은 점수가 덜 나오게 하려고 더했다(사용자, 2026-11-14). 처음에는 1-5 다섯 단계였는데
# "아직 이산적"이라는 의견에 0-100으로 바꿨다. 두 범위의 끝값은 1-5 때 실전 시험으로 맞춘 값이다:
# 바라던 말의 5를 1.25배로 두면 속마음을 읽는 참가자가 평균 89.0점이라 1.1배로 낮췄다(86.3점)
STRENGTH_RANGE = (0.6, 1.4)
HIT_STRENGTH_RANGE = (0.4, 1.1)
# 바라던 말이라도 글자(한글, 영문, 숫자)가 이만큼 이하이면("필통 예쁘네") 설렘을 30까지로 둔다
SHORT_HIT_LETTERS = 10
SHORT_HIT_STRENGTH_MAX = 30
# 선택지를 고른 말의 설렘 상한. 직접 쓴 말이 더 높게 나올 수 있게 한다
CHOICE_STRENGTH_MAX = 50
# 점수가 높을수록 덜 오른다. 오르는 점수에 max(바닥, (100 - 지금 점수) / (100 - 시작점))를 곱한다:
# 60점까지는 그대로, 80점이면 절반, 90점이면 0.25배, 98점부터는 0.05배. 내리는 점수는 그대로다.
# Claude가 속마음을 읽고 한 6판이 평균 93점, 3판이 100점이라 너무 쉬웠다(2026-11-14). 같은 대화를 이 규칙으로
# 다시 매기면 평균 84.7점, 100점 0판이고 다정한 참가자는 66.9 → 66.4점으로 거의 그대로다.
# 바닥은 처음에 0.3이었다. 2026-11-15에 바라던 말(+2)을 무겁게 하면서(진행표의 points_scale) 바람을 열두 번 다
# 가장 세게 짚으면 100점에 닿아서 0.05로 낮췄다. 실전 기록 12판을 다시 매긴 점수는 바닥이 0.3이어도 0.05여도 같다
SLOWDOWN_FROM = 60
SLOWDOWN_FLOOR = 0.05
SCORE_DIGITS = 1
# 호감도가 이만큼부터 캐릭터가 먼저 안기고 싶어 하게 한다(actor.CLOSE_MOMENT_NOTE). 사용자 요청(2026-11-15).
# 처음에는 대성공 커트와 같은 80이었는데, 대성공을 75로 낮추면서 사용자가 "80 도달은 쉽지 않다"며 77로 정했다.
# 같은 날 대성공을 다시 80으로 올렸지만(사용자: 노력하면 75는 쉽다) 이 값은 77로 둔다
# 한 판에 한 번이고, 답에 그런 마음이 안 보이면 다음 답에서 한 번 더 시킨다(CLOSE_TRIES)
JUDGE_BUDGET_SEC = 5      # 바람 판정(judge_wish_hit)을 기다리는 상한. 넘으면 낱말로만 가른다
CLOSE_SCORE = 77
WEATHERS = ("rain", "storm")   # 화면이 아는 날씨
# 지문에서 둘이 가까워진 것과 다시 떨어진 것. 화면은 가까워진 동안 스탠딩을 조금 크게 둔다(사용자, 2026-11-15).
# 실제 모델 347답 가운데 가까워짐이 10%, 떨어짐이 5%였다. 한 지문에 둘 다 있으면 뒤에 나온 것을 따른다
CLOSE_IN_RE = re.compile(r"다가앉|다가서|바짝 다가|가까이 (다가|붙|앉)|어깨에 (머리를 |고개를 )?(살짝 )?기대|기대어|기대었|기댄"
                         r"|품에|품으로|안겼|안기|손을 (꼭 |살며시 |조심스럽게 )?(잡|맞잡|쥐|포개)|손을 맞|팔짱|어깨가 (닿|맞닿)|붙어 (앉|서)")
CLOSE_OUT_RE = re.compile(r"떨어지|떨어졌|떨어져|물러서|물러섰|물러난|손을 (놓|빼|거두)|몸을 (떼|뺐|빼)|거리를 (두|벌)"
                          r"|뒤로 (한 걸음|물러|몸을)")
CLOSE_TRIES = 2
# 엔딩 작가에게 넘기는 기록에서 [수위]를 넘는 참가자의 말 대신 넣는 글
ENDING_MASKED_INPUT = "(주인공이 선을 넘는 말을 했다. 그 말은 옮기지 않는다.)"
# 글자(한글, 영문, 숫자)가 이만큼 이하인 말("응", "별로", "ㅋㅋ")은 호감도를 올리지 않는다
SHORT_INPUT = 2
# 점수 사유에서 바람(wish)을 가리키는 말. 날씨의 바람("바람이 불어서")은 건드리지 않는다
WISH_REASON_RE = re.compile(r"바람(을|대로|에\s?맞|이\s?이루)|wish", re.IGNORECASE)
BLUSH_LIMIT = 4  # 한 판에 붉어진 얼굴(blush)을 이만큼까지만 낸다. 그 뒤는 smile
# 지문이나 겉말이 웃음, 붉어짐을 그리고 있는지. 그렇다면 표정 고르기(_balance_face)가 그 표정을 바꾸지 않는다
SMILE_WORDS_RE = re.compile(r"웃|미소|후훗|싱긋|빙긋|방긋")
BLUSH_WORDS_RE = re.compile(r"빨개|빨갛|붉어|붉게|붉은|달아오|화끈|홍조")
# 얼굴(볼, 귀, 목)이 빨개졌다고 쓴 글. "붉은 노을", "빨간 우산"은 잡지 않는다
RED_FACE_RE = re.compile(r"(얼굴|볼|뺨|귀|귓|목덜미|목까지)[^.!?…]{0,12}(빨개|빨갛|붉어|붉게|붉히|붉힌|달아오|화끈|새빨)|홍조")
# 바람을 짚은 말(+2)의 설렘이 이만큼 이상이면 웃는 얼굴 대신 붉어진 얼굴을 보인다(사용자, 2026-11-15)
BLUSH_STRENGTH = 90
# 이야기 모드(실험, 2026-11-14): 이 환경변수가 비어 있지 않고 0이 아니면 답을 길게 쓰고 캐릭터가 이야기를 끌고
# 가는 진행표(data/schedule_story.json, 답 12번)를 쓴다. 친구의 의견("노잼, Zeta처럼 대화가 길었으면")으로 만든 실험이다
STORY_ENV = "SOGAETING_STORY"
# 이야기 모드에서 답마다 움직이는 점수에 곱하는 값. 답이 12번이고(지금 10번) 캐릭터가 꺼낸 제안을 받아 주다가
# 바람을 짚는 일이 많아서 점수가 더 올랐다. 실전 시험(2026-11-14, 평범한 참가자 역할, 3캐릭터씩): 지금 방식
# 평균 73.9점, 이야기 모드 82.8점(같은 표로 다시 매긴 값). 오른 몫(23.9점과 32.8점)의 비가 0.73이라 0.75로 둔다.
# 3판씩이라 어림값이다
STORY_POINTS_SCALE = 0.75
# 진행표의 points_scale로 받을 수 있는 값의 범위
POINTS_SCALE_RANGE = (0.3, 1.5)


def story_mode_on() -> bool:
    return os.environ.get(STORY_ENV, "").strip() not in ("", "0")


def band_of(score: float) -> str:
    """배우에게 알려 줄 호감도 구간."""
    if score >= 65:
        return "high"
    if score >= 40:
        return "mid"
    return "low"


def _step_scale(scale, step: int) -> float:
    """진행표의 points_scale에서 delta 한 칸(step)에 곱할 값. 못 읽거나 POINTS_SCALE_RANGE 밖이면 1."""
    if isinstance(scale, dict):
        scale = scale.get(str(step), 1.0)
    if not isinstance(scale, (int, float)) or isinstance(scale, bool):
        return 1.0
    if not POINTS_SCALE_RANGE[0] <= scale <= POINTS_SCALE_RANGE[1]:
        return 1.0
    return scale


def _quotable_input(text) -> bool:
    """엔딩 작가에게 그대로 넘겨도 되는 참가자의 말인가."""
    return not (safety.looks_lewd(text) or safety.looks_like_override(text))


def is_short_input(text: str) -> bool:
    """성의 없는 단답인가. 한글 자모만 있는 말("ㅋㅋ", "ㅇㅇ")은 글자가 없는 것으로 친다."""
    return len(re.findall(r"[0-9A-Za-z가-힣]", text or "")) <= SHORT_INPUT


def _signed(n: float) -> str:
    """팝업에 띄울 숫자: "+2.4", "-6.0", "±0". 소수 한 자리까지."""
    return "±0" if round(n, SCORE_DIGITS) == 0 else f"{n:+.{SCORE_DIGITS}f}"


def strength_scale(strength: float, hit: bool = False) -> float:
    """설렘(0-100)에 따라 곱하는 값. hit이면 바라던 말(+2)의 범위를 쓴다."""
    low, high = HIT_STRENGTH_RANGE if hit else STRENGTH_RANGE
    s = max(actor.STRENGTH_MIN, min(actor.STRENGTH_MAX, strength))
    return low + (high - low) * (s - actor.STRENGTH_MIN) / (actor.STRENGTH_MAX - actor.STRENGTH_MIN)


def points_for(step: float, strength: float, hit: bool = False) -> float:
    """칸의 점수(step)에 설렘을 곱한 점수. 소수 한 자리로 반올림한다. hit이면 바라던 말(+2)의 범위를 쓴다."""
    return round(step * strength_scale(strength, hit), SCORE_DIGITS)


def slowdown(score: float) -> float:
    """지금 점수에서 오르는 점수에 곱하는 값. 60점까지 1, 높을수록 작아지고 SLOWDOWN_FLOOR 밑으로는 안 간다."""
    return max(SLOWDOWN_FLOOR, min(1.0, (100 - score) / (100 - SLOWDOWN_FROM)))


def gain_for(score: float, points: float) -> float:
    """지금 점수에서 실제로 움직이는 점수. 오르는 점수만 줄어든다."""
    if points <= 0:
        return points
    return round(points * slowdown(score), SCORE_DIGITS)


class ModelUnavailable(Exception):
    """모델이 이번 답을 주지 못했다(과부하 503, 한도, 시간 초과, 못 읽는 답).

    판의 상태는 그 말을 받기 전으로 되돌려 두었으니 다시 보내면 된다. 서버는 503으로 알리고
    화면은 "다시 시도"를 띄운다."""


class Session:
    """한 판. start() → reply() 여러 번 → finish() → result() 순서로 부른다."""

    def __init__(self, character_id: str, *, llm=None, rng: random.Random | None = None, story: bool | None = None):
        self.character = content.load_character(character_id)  # 없으면 KeyError
        self.llm = llm if llm is not None else (lambda m: call_llm(m, json_mode=True))
        # 바람을 짚었는지 묻는 판정은 짧게 기다린다. 못 받으면 낱말로만 가른다. 구글이 느린 날에 판정 때문에
        # 손님이 한 답에 15초를 더 기다리지 않게 한다
        self.judge_llm = llm if llm is not None else (lambda m: call_llm(m, json_mode=True, budget=JUDGE_BUDGET_SEC))
        self.rng = rng if rng is not None else random.Random()
        self.gimmick = gimmicks.get_gimmick(self.character.get("gimmick"))

        self.seeds = content.load_seeds()
        self.fx = content.load_fx()
        self.story = story_mode_on() if story is None else bool(story)
        self.schedule = content.load_schedule("schedule_story" if self.story else "schedule")
        self.banned = content.load_banned()
        self.endings = content.load_endings()
        self.total_turns = len(self.schedule["replies"])

        self.score = float(START_SCORE)
        self.turn = 0            # 지금까지 한 답의 수
        self.started = False
        self.done = False        # 엔딩까지 끝났는가
        self.history = []        # 배우와 주고받은 기록
        self.past_inputs = []    # 참가자가 친 글 (다듬은 원문)
        self._used_seeds = set()
        self._last_fx = []       # 바로 앞 답에서 실제로 내보낸 연출
        self._fallback_count = 0
        self._inners = []        # 속마음 전부 (등장 포함)
        self._faces = []         # 화면에 낸 표정 전부 (등장 포함, 대체 대사 제외)
        self._place = ""         # 지금 장소. 등장 장소였다가 진행표의 move 답에서 한 번 바뀐다
        self._moved_from = ""    # 옮겨 오기 전 장소(등장 장소). 아직 안 옮겼으면 빈 문자열
        self._move_pending = False  # 옮길 차례가 왔는데 아직 못 옮겼다(정전, 사건, 대체 대사)
        self._events = []        # 지금까지 일어난 사건 ("답 3 소나기와 우산 하나")
        # 날씨. 비나 천둥 사건(seeds.json의 event_weather)이 일어난 뒤로 판이 끝날 때까지 "rain" 또는 "storm"이다.
        # 화면은 이 값으로 배경을 어둡게 두고 비를 계속 내린다(사용자, 2026-11-15: 비가 오는데 배경이 밝으면 어색하다)
        self._weather = None
        # 정전(seeds.json의 event_lights_out): 사건 답부터 적힌 답 수만큼 불이 꺼져 있고, 그다음 답에서 다시 들어온다.
        # 화면은 그동안 무대를 어둡게 둔다(사용자, 2026-11-15: 암전 연출은 다 가려서 어색하다, 해결될 때까지 어둡게)
        self._lights_out_left = 0     # 이번 답 뒤로 불이 더 꺼져 있을 답의 수
        self._lights_back_next = False  # 다음 답에서 불이 다시 들어온다
        self._close = False              # 지문에서 둘이 가까워진 채인가
        self._petals_left = 0            # 꽃잎이 더 날릴 답의 수(seeds.json의 event_petals)
        self._best = None        # (delta 절댓값, 속마음)
        self._last_choices = []  # 바로 앞 답에서 화면에 보인 선택지
        self.points = dict(POINTS)
        hit = self.character.get("hit_points")
        if isinstance(hit, int) and not isinstance(hit, bool) and HIT_POINTS_RANGE[0] <= hit <= HIT_POINTS_RANGE[1]:
            self.points[2] = hit
        # 답이 10번보다 많은 진행표는 한 답의 점수 움직임을 바꿔서 점수 범위를 맞춘다(진행표의 points_scale).
        # 숫자 하나면 모든 칸에, {"2": 1.2, "1": 0.6, ...}처럼 주면 칸마다 곱한다. 이야기 모드는 STORY_POINTS_SCALE을 쓴다
        scale = STORY_POINTS_SCALE if self.story else self.schedule.get("points_scale", 1.0)
        self.points = {step: points * _step_scale(scale, step) for step, points in self.points.items()}
        self._from_choice = False  # 이번 입력이 그 선택지 가운데 하나와 같은가
        self._close_tries = CLOSE_TRIES  # 캐릭터가 먼저 안기고 싶어 하게 시킬 수 있는 남은 횟수
        self._ending = None
        self._finished_at = None

    # ---- 바깥에서 부르는 것 ----

    def start(self) -> dict:
        """등장. 한 번만 부른다. 모델이 답을 못 주면 ModelUnavailable이고, 그때는 다시 불러도 된다."""
        if self.started:
            raise RuntimeError("start()는 한 번만 부를 수 있다")
        self.started = True
        self.history = [{"role": "user", "content": actor.OPENING_CUE}]
        try:
            return self._play(self.schedule["opening"], opening=True, heard=None)
        except ModelUnavailable:
            self.started = False
            self.history = []
            raise

    def reply(self, user_text: str) -> dict:
        """참가자의 입력 하나에 캐릭터가 답한다."""
        if not isinstance(user_text, str):
            raise ValueError("입력은 문자열이어야 한다")
        text = safety.clean_input(user_text)
        if not text:
            raise ValueError("빈 입력은 보낼 수 없다")
        if not self.started:
            raise RuntimeError("start()를 먼저 불러야 한다")
        if self.done or self.turn >= self.total_turns:
            raise RuntimeError("이 판은 더 답을 받지 않는다")

        self._from_choice = text in self._last_choices
        sent, heard = self.gimmick.transform_input(text, self.rng)
        self.history.append({"role": "user", "content": sent})
        self.past_inputs.append(text)
        self.turn += 1
        try:
            return self._play(self.schedule["replies"][self.turn - 1], opening=False, heard=heard)
        except ModelUnavailable:
            # 이번 말은 없던 일로 한다. 참가자가 같은 말이나 다른 말을 다시 보내면 같은 차례로 다시 한다
            self.history.pop()
            self.past_inputs.pop()
            self.turn -= 1
            raise

    def finish(self) -> dict:
        """엔딩 카드. 여러 번 불러도 같은 값을 돌려준다."""
        if not self.started:
            raise RuntimeError("start()를 먼저 불러야 한다")
        if self._ending is not None:
            return self._ending

        grade = self._grade()
        # [수위]를 넘는 말과 설정을 버리라는 말은 엔딩 작가에게 넘기지 않는다. 실전 기록: 외설 판의 젬마 엔딩
        # 칭호가 "생각보다 몸매 좋은"이었다(2026-11-15)
        history = [
            {"role": "user", "content": ENDING_MASKED_INPUT}
            if message.get("role") == "user" and not _quotable_input(message.get("content")) else dict(message)
            for message in self.history
        ]
        messages = actor.build_ending_messages(
            self.character, history, band_name=grade["name"], score=self.score)
        ending = actor.ask_ending(self.llm, messages)
        if ending is not None:
            texts = [ending.title, ending.epilogue, ending.nickname]
            if (safety.contains_banned(texts, self.banned) or actor.offstage_words(texts)
                    or any(safety.looks_lewd(text) for text in texts)):
                ending = None
        if ending is None:
            title, epilogue, nickname = f"{grade['name']} 엔딩", "", ""
        else:
            title, epilogue, nickname = ending.title, ending.epilogue, ending.nickname

        self._finished_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        self._ending = {
            "kind": "ending",
            "character_id": self.character["id"],
            "character_name": self.character["name"],
            "band_id": grade["id"],
            "band_name": grade["name"],
            "title": title,
            "epilogue": epilogue,
            "nickname": nickname,
            "score": self.score,
            "best_line": self._best[1] if self._best else "",
            "inners": list(self._inners),
            "early": self.turn < self.total_turns,
        }
        self.done = True
        return self._ending

    def result(self) -> dict:
        """3단계로 넘길 값. 대화 원문은 넣지 않는다."""
        if self._ending is None:
            raise RuntimeError("finish()를 먼저 불러야 한다")
        return {
            "character_id": self._ending["character_id"],
            "character_name": self._ending["character_name"],
            "affinity": self._ending["score"],
            "band": self._ending["band_name"],
            "ending_title": self._ending["title"],
            "nickname": self._ending["nickname"],
            "finished_at": self._finished_at,
        }

    # ---- 안에서만 쓰는 것 ----

    def _play(self, slot, *, opening, heard):
        """등장 또는 답 하나를 만든다. history는 user로 끝나 있어야 한다."""
        intensity = slot["intensity"]
        finale = (not opening) and self.turn == self.total_turns
        seed_kind = slot.get("seed")
        # 한 판의 마지막 두 사건은 손잡기나 기대기 같은 순간의 계기가 되는 사건(event_hints)에서 고르고,
        # 마지막 사건에서는 실제로 닿는 장면까지 쓰게 한다(없으면 한 번 고쳐 쓰게 한다). 사용자가 그런 순간이
        # 거의 늘 나오기를 바랐다(2026-11-14)
        later_events = sum(1 for r in self.schedule["replies"][self.turn:] if r.get("seed") == "event")
        is_event = seed_kind == "event" and not opening
        seed = self._pick_seed(seed_kind, close=is_event and later_events <= 1)
        seed_hint = (self.seeds.get("event_hints") or {}).get(seed, "") if seed_kind == "event" else ""
        must_touch = is_event and later_events == 0 and bool(seed_hint)
        fx_allowed = list(self.fx["light"])
        if intensity > 2:
            fx_allowed += self.fx["heavy"]
        # 이번 답의 불: 정전이 시작되는 답(start), 아직 꺼져 있는 답(dark), 다시 들어오는 답(back), 아니면 빈 값
        lights_off_for = (self.seeds.get("event_lights_out") or {}).get(seed) if seed_kind == "event" else None
        if opening:
            lights = ""
        elif isinstance(lights_off_for, int) and lights_off_for > 0:
            lights = "start"
        elif self._lights_out_left > 0:
            lights = "dark"
        elif self._lights_back_next:
            lights = "back"
        else:
            lights = ""
        # 장소 옮기기: 진행표의 move 답(6번째)에서 한 번 옮긴다. 정전 중이거나 사건 답이면 다음 답으로 미룬다
        # (친구 의견, 2026-11-16: 한 장소에서 12답은 늘어진다)
        if slot.get("move") and not opening and not self._moved_from:
            self._move_pending = True
        move = None
        if (self._move_pending and not opening and not finale and self._place and not lights
                and seed_kind != "event"):
            move = self._pick_move()
        # 방금 들은 말이 [수위]를 넘거나, 설정을 버리라거나, 닿자고 청하는 말인가. 지시문에 한 줄을 더하고
        # 점수도 아래에서 막는다(2026-11-15 실전 기록: 지시문만으로는 외설 입력 19번이 점수를 올렸다)
        said = "" if opening else self.past_inputs[-1]
        lewd = safety.looks_lewd(said)
        override = safety.looks_like_override(said)
        touch = "" if lewd else safety.touch_request(said)
        confession = not lewd and safety.looks_like_confession(said)
        band = band_of(self.score)  # 이번 답을 반영하기 전 점수의 구간
        # 호감도가 낮으면 손잡기도 안기도 받아 주지 않는다. 중간이면 손잡기까지만 받아 준다
        touch_refused = bool(touch) and (band == "low" or (band == "mid" and touch == "hug"))
        extra = "" if opening else self.gimmick.extra_instruction(list(self.past_inputs))
        guard = actor.input_guard_note(lewd=lewd, touch=touch, band=band) if not opening else ""
        # 호감도가 아주 높으면 캐릭터가 먼저 안기고 싶어 한다. 수위를 넘는 말을 들은 답에서는 하지 않는다
        close_moment = (not opening and not lewd and not override and self._close_tries > 0
                        and self.score >= CLOSE_SCORE)
        for note in (guard, actor.CLOSE_MOMENT_NOTE if close_moment else ""):
            if note:
                extra = (extra + "\n\n" + note) if extra else note

        messages = actor.build_turn_messages(
            self.character, list(self.history),
            band=band,
            intensity=intensity,
            intensity_meaning=self._intensity_meaning(intensity, band),
            fx_allowed=fx_allowed,
            seed=seed,
            seed_kind=seed_kind if seed else None,
            opening=opening,
            finale=finale,
            extra=extra,
            place=move[1] if move else self._place,
            moved_from=move[0] if move else self._moved_from,
            move_reason=move[2] if move else "",
            events_so_far=tuple(self._events),
            seed_hint=seed_hint,
            story=self.story,
            beat=str(slot.get("beat") or "") if self.story else "",
            must_touch=must_touch,
            weather="" if opening else (self._weather or ""),
            lights=lights,
        )
        fx_names = set(self.fx["light"]) | set(self.fx["heavy"])
        event_seed = seed if seed_kind == "event" else None
        used, tomorrow = actor._used_phrases(self.history)
        wishes = actor._recent_wishes(self.history)  # 앞 답들이 속마음에 흘린 바람 (이번 답의 +2를 가른다)
        wish_words = actor._recent_wish_words(self.history, wishes)  # 바람과 함께 적어 둔 돌려 말할 낱말
        stuck_wish = wishes[0] if wishes and actor._wish_streak(self.history) >= 2 else ""
        previous = actor._previous_lines(self.history)
        reply = actor.ask_turn(self.llm, messages, fx_names, faces=actor.faces_for(self.character),
                               review=lambda r: actor.review_reply(r, self.character, banned=self.banned,
                                                                   event_seed=event_seed, used_phrases=used,
                                                                   tomorrow=tomorrow, finale=finale,
                                                                   previous=previous, stuck_wish=stuck_wish,
                                                                   touch_hint=seed_hint if must_touch else "",
                                                                   moved_to=move[1] if move else "",
                                                                   overused=actor.overused_catchphrases(
                                                                       r, self.character, self.history,
                                                                       swappable=False)))

        # 모델이 답을 못 줬으면(과부하 503, 한도, 시간 초과, 못 읽는 답) 대체 대사로 넘기지 않고 참가자가
        # 다시 보내게 한다(사용자, 2026-11-14: "넘어가는 건 금지어 걸릴 때만, 503은 다시 기회"). 뽑아 둔 씨앗은 돌려놓는다
        if reply is None:
            if seed is not None:
                self._used_seeds.discard(seed)
            raise ModelUnavailable()
        # 금지어가 걸리거나, 고쳐 쓰게 했는데도 캐릭터가 모르는 말("AI" 같은 것)이 남았으면 대체 대사로 바꾼다
        fallback = safety.contains_banned(actor.reply_texts(reply), self.banned) or actor.must_drop(reply)
        if fallback:
            reply = actor.Reply(say=self._next_fallback_line())
        elif actor.wish_hidden(reply, actor.name_words(self.character)):
            # 고쳐 쓰게 했는데도 바람의 낱말이 지문, 겉말, 속마음 어디에도 없으면 그 바람은 버린다.
            # 참가자가 볼 수 없는 바람으로 +2를 가르지 않는다
            reply.wish = ""

        if not fallback:
            # 모델이 지시문을 "주인공"이라는 말 그대로 옮겨 쓸 때가 있다. 이야기 속 이름으로 바꾼다
            for name in ("narration", "say", "inner", "reason"):
                setattr(reply, name, getattr(reply, name).replace("주인공", "전학생"))
            reply.narration = actor.plain_narration(reply.narration)
            # 점수 사유는 화면에 뜬다. 숨은 칸(wish)의 이름인 "바람"이 새면 흔한 사유로 바꾼다.
            # 실전 기록: "바람대로 손끝이 닿았음", "소나기와 함께 기대고 싶다는 바람을 짚어줘서"
            if WISH_REASON_RE.search(reply.reason):
                reply.reason = "마음을 알아줘서"
            # 소라는 대사에서 호칭을 일부러 틀리게 부르는데(정학생, 전학새, 전화생), 지문에까지 옮겨 썼다
            for slip in ("정학생", "전학새", "전화생"):
                reply.narration = reply.narration.replace(slip, "전학생")
            # 바로 앞 답에서도 썼거나 한도만큼 쓴 말끝("…것뿐이거든")은 코드가 바꾼다. 고쳐 쓰게 해도 남았다
            reply.say = actor.swap_catchphrases(
                reply.say, actor.overused_catchphrases(reply, self.character, self.history))
            reply.say = actor.fix_stretched_vowels(reply.say)
            reply.inner = actor.fix_stretched_vowels(reply.inner)
            # 설정을 버리라는 입력과 [수위]를 넘는 입력에는 점수를 내린다 (연기 규칙 7, 설계 문서 5.10절).
            # 모델이 올려도 여기서 내린다. 호감도가 모자란데 닿자고 청한 말은 올리지 않는다
            if override or lewd:
                reply.delta = min(reply.delta, -1)
            elif touch_refused:
                reply.delta = min(reply.delta, 0)
            # 고백은 [수위] 안의 말이다. 실전 기록(2026-11-16, 사용자): 80점을 넘겨 안긴 뒤 "사랑한다"에 -2(8점)가
            # 나왔다. 어느 구간에서도 -1 밑으로 내리지 않고, 호감도가 높을 때는 깎지 않는다
            if confession and not override:
                reply.delta = max(reply.delta, 0 if band == "high" else -1)
            if not opening:
                # 단답에는 올리지 않는다. 실전 기록: 젬마가 "응"에 +1을 줬다(사유는 자기가 꺼낸 우산)
                if is_short_input(self.past_inputs[-1]):
                    reply.delta = min(reply.delta, 0)
                # 선택지를 고른 말은 +1까지다. +2는 참가자가 직접 쓴 말에만 준다.
                # 선택지는 모델이 다정한 답을 하나 넣어 두므로, 그것만 골라도 +2가 나왔다
                if self._from_choice:
                    reply.delta = min(reply.delta, 1)
                    if reply.delta > 0:
                        reply.strength = min(reply.strength, CHOICE_STRENGTH_MAX)
                # +2는 앞 답들이 속마음에 흘린 바람을 참가자가 짚었을 때만 남긴다. 바람의 낱말이나, 바람과 함께
                # 적어 둔 돌려 말할 낱말이 있어야 한다. 다정한 말만으로는 대성공이 안 되게 하려는 것이다.
                # 실전 기록: 모델이 "반가워. 여기 자주 와?"에도 2를 줬다
                # 모델이 2를 주면 판정을 한 번 더 묻는다(actor.judge_wish_hit). 돌려 말한 말은 낱말이 안 맞아도 인정하고,
                # 바람의 낱말을 스치기만 한 말이나 캐릭터가 겉말로 먼저 제안한 것에 대답만 한 말은 1로 줄인다.
                # 판정을 못 받으면 예전처럼 바람의 낱말과 돌려 말할 낱말로만 가른다
                if reply.delta == 2:
                    judged = actor.judge_wish_hit(self.judge_llm, wishes, self.past_inputs[-1],
                                                  actor.last_say(self.history))
                    if judged is None:
                        related = [word for wish in wishes for word in wish_words.get(wish, [])]
                        judged = actor.wish_hit(self.past_inputs[-1], wishes, related,
                                                actor.name_words(self.character))
                    if not judged:
                        reply.delta = 1
                # 바람의 낱말만 짧게 던진 말은 크게 설레게 하지 못한다
                if reply.delta == 2 and len(re.findall(r"[0-9A-Za-z가-힣]", self.past_inputs[-1])) <= SHORT_HIT_LETTERS:
                    reply.strength = min(reply.strength, SHORT_HIT_STRENGTH_MAX)
            if close_moment:
                # 그 마음이 드러났으면 이 판에서는 다시 시키지 않는다. 안 보이면 남은 횟수만큼 다음 답에서 또 시킨다
                self._close_tries = 0 if actor.shows_hug(reply) else self._close_tries - 1
            # 표정은 점수를 다 고친 뒤에 고른다(점수가 그대로인 답을 알아야 한다)
            reply.face = self._balance_face(reply, opening=opening, finale=finale, event=bool(event_seed))
            # 캐릭터 설정의 face_swaps에 적힌 표정은 다른 표정으로 바꿔 보인다. 노바는 dark 그림이 예전 색으로만 있고,
            # 호감도가 내려가지 않아 거의 안 쓰여서 다시 뽑지 않고 pout을 쓴다(사용자, 2026-11-16)
            reply.face = actor.swap_face(reply.face, self.character)
            self._faces.append(reply.face)

        # 불이 꺼져 있는 동안에는 무대 전체를 덮었다가 밝아지는 "암전"을 쓰지 않는다. 화면이 어둡게 두고 있다
        fx = self._filter_fx([n for n in reply.fx if n != "암전"] if lights in ("start", "dark") else reply.fx, intensity)

        # 점수. 등장과 대체 대사에서는 움직이지 않는다
        notes = []
        delta, reason = 0, ""
        if not opening and not fallback:
            if lewd or override:
                # 기믹(노바의 ReLU는 음수를 0으로 바꾼다)이 이 감점을 지우지 않게 한다. 실전 기록: 외설 판의
                # 노바가 감점을 한 번도 받지 않아 52.0점으로 끝났다(2026-11-15)
                delta, note = reply.delta, None
            else:
                delta, note = self.gimmick.adjust_delta(reply.delta)
            reason = reply.reason
            if note:
                notes.append(note)
        old_score = self.score
        step = self.points[max(-2, min(2, delta))]
        strength = reply.strength if step else actor.STRENGTH_DEFAULT
        hit = max(-2, min(2, delta)) == 2
        moved = gain_for(old_score, points_for(step, strength, hit))
        self.score = round(max(0.0, min(100.0, old_score + moved)), SCORE_DIGITS)
        change = round(self.score - old_score, SCORE_DIGITS)

        eight = {
            "narration": reply.narration,
            "say": reply.say,
            "inner": reply.inner,
            "face": reply.face,
            "fx": list(fx),
            "delta": delta,
            "reason": reason,
            "choices": [] if finale else list(reply.choices),
        }
        ctx = {
            "turn": self.turn,
            "total_turns": self.total_turns,
            "score": self.score,
            "change": change,
            "past_inputs": list(self.past_inputs),
        }
        extras = dict(self.gimmick.decorate(dict(eight), ctx) or {})
        if opening or fallback:
            popup = None
        else:
            popup = extras["popup"] if "popup" in extras else _signed(change)

        # 화면에 보일 선택지. 모델이 세 개를 못 줬거나 대체 대사면 기본 선택지를 준다.
        # 기록(history)에는 모델이 실제로 준 것만 남긴다.
        shown_choices = eight["choices"]
        if not finale and len(shown_choices) != 3:
            shown_choices = list(self.schedule.get("default_choices") or [])
        self._last_choices = list(shown_choices)

        # 기록에는 화면에 안 나오는 바람(wish)도 남긴다. 다음 답의 지시문이 그것을 읽는다
        wish = "" if fallback or finale else reply.wish
        record = dict(eight, wish=wish, wish_words=list(reply.wish_words) if wish else [], strength=strength)
        self.history.append({"role": "assistant", "content": json.dumps(record, ensure_ascii=False)})
        # 지금 장면: 등장 장소와 실제로 일어난 사건을 적어 두고 다음 답들의 지시문에 알려 준다
        if opening and seed_kind == "entrance" and seed:
            self._place = seed
        if seed_kind == "event" and seed and not fallback:
            self._events.append(f"답 {self.turn} {seed}")
            weather = (self.seeds.get("event_weather") or {}).get(seed)
            if weather in WEATHERS:
                self._weather = weather
        # 장소를 옮긴 답: 다음 답부터 새 장소다. 대체 대사가 되면 옮기지 않은 것이라 다음 답으로 미룬다.
        # 옮겨 오면 떨어져 있던 거리와 꽃잎은 처음부터 다시 시작한다
        moved_to = None
        if move and not fallback:
            old, moved_to, _ = move
            self._moved_from, self._place, self._move_pending = old, moved_to, False
            self._events.append(f"답 {self.turn} {old}에서 {moved_to}(으)로 옮겨 옴")
            self._close = False
            self._petals_left = 0
        # 정전의 남은 답 수를 센다. 대체 대사는 아무 일도 없던 답이라 세지 않는다
        # 꽃잎: 사건 답부터 적힌 답 수만큼 날린다
        petals_for = (self.seeds.get("event_petals") or {}).get(seed) if seed_kind == "event" else None
        if not fallback and isinstance(petals_for, int) and petals_for > 0:
            self._petals_left = petals_for
        petals = self._petals_left > 0
        if petals:
            self._petals_left -= 1
        # 가까워짐: 지문에 가까워진 장면이나 떨어진 장면이 있으면 바꾸고, 없으면 그대로 둔다
        if not opening and not fallback:
            near = [m.end() for m in CLOSE_IN_RE.finditer(reply.narration)]
            away = [m.end() for m in CLOSE_OUT_RE.finditer(reply.narration)]
            if near or away:
                self._close = max(near or [-1]) > max(away or [-1])
        # 정전이 시작될 답이 대체 대사가 되면 정전은 일어나지 않은 것이다
        lights_out = lights == "dark" or (lights == "start" and not fallback)
        if not fallback:
            if lights == "start":
                self._lights_out_left = lights_off_for - 1
                self._lights_back_next = self._lights_out_left == 0
            elif lights == "dark":
                self._lights_out_left -= 1
                self._lights_back_next = self._lights_out_left == 0
            elif lights == "back":
                self._lights_back_next = False
        self._inners.append(eight["inner"])
        # 명대사 후보: delta 절댓값이 가장 큰 답. 같으면 뒤쪽. 대체 대사는 속마음이 없어서 뺀다
        if not opening and not fallback and (self._best is None or (abs(delta), strength) >= self._best[0]):
            self._best = ((abs(delta), strength), eight["inner"])

        return {
            "kind": "turn",
            "turn": self.turn,
            "total_turns": self.total_turns,
            **eight,
            "choices": shown_choices,
            "change": change,
            "strength": strength,
            "score": self.score,
            "band": band_of(self.score),
            "popup": popup,
            "notes": notes,
            "heard": heard,
            "extras": extras,
            "fallback": fallback,
            "finale": finale,
            # 장소. 화면이 배경을 고를 때 쓴다. 등장 답과 장소를 옮긴 답에만 오고, 나머지 답에서는 None이다
            "place": seed if opening and seed_kind == "entrance" else moved_to,
            # 표정(face)이 기본 여섯 가지 가운데 어느 자리인지. 화면은 캐릭터만의 표정 그림이 없으면 이 그림을 쓰고,
            # 연출(기호, 움직임)도 이것으로 고른다
            "face_base": actor.face_base(self.character, reply.face),
            # 날씨: None, "rain", "storm". 비나 천둥 사건이 있은 답부터 판이 끝날 때까지 같은 값이다
            "weather": self._weather,
            # 정전으로 불이 꺼져 있는 답이면 True. 화면은 그동안 무대를 어둡게 둔다
            "lights_out": lights_out,
            # 지문에서 둘이 가까워진 채이면 True. 화면은 그동안 스탠딩을 조금 크게 둔다
            "close": self._close,
            # 꽃잎이 날리는 답이면 True(벚꽃잎 사건 답부터 몇 답)
            "petals": petals,
        }

    def _balance_face(self, reply, *, opening, finale, event):
        """모델이 고른 표정이 한쪽으로 쏠리지 않게 고친다. 고친 표정을 돌려준다.

        실제 모델 36판(답 373개)에서 웃음 44%, 붉어짐 38%였고 평소 얼굴은 11%였다(2026-11-14).
        평소 얼굴(neutral)의 그림은 캐릭터마다 그 캐릭터다운 얼굴이다(아스트라는 시큰둥, 노바는 활짝 웃음,
        미스트랄은 의기양양). 그래서 바꿀 곳은 평소 얼굴로 한다."""
        face = reply.face
        # 캐릭터만의 표정은 하나를 한 판에 EXTRA_FACE_LIMIT번(설정에 limit이 있으면 그만큼)까지 낸다.
        # 넘으면 그 자리의 기본 표정으로 바꾼다. 실제 모델 기록: 하이쿠가 flushed를 판마다 세 번씩 냈다
        if face not in actor.FACES and self._faces.count(face) >= actor.extra_face_limit(self.character, face):
            face = actor.face_base(self.character, face)
        bases = [actor.face_base(self.character, f) for f in self._faces]
        base = actor.face_base(self.character, face)
        # 글이 얼굴이 빨개졌다고 하거나, 바람을 짚은 말에 아주 크게 설렜으면 붉어진 얼굴을 보인다. 아래의 횟수 제한도
        # 받지 않는다. 사용자(2026-11-15): "누가 봐도 얼굴이 빨개야 할 것 같은데 그냥 웃으니 어색하다".
        # 실제 모델 215답 가운데 14답은 글에 "얼굴이 새빨개졌다"가 있는데 그림은 웃는 얼굴이었다
        red = bool(RED_FACE_RE.search(" ".join([reply.narration, reply.say, reply.inner])))
        big = reply.delta == 2 and reply.strength >= BLUSH_STRENGTH
        if red or big:
            if base in ("smile", "neutral"):
                return "blush"
            if base == "blush":
                return face
        # 붉어진 얼굴이 세 번 연달아 나오면 웃는 얼굴로 바꾼다. 실제 모델은 답의 3분의 2를 blush로 냈다.
        # blush 자리에 쓰는 캐릭터만의 표정(아스트라의 denial 같은 것)도 blush로 센다
        if base == "blush" and (bases[-2:] == ["blush", "blush"] or bases.count("blush") >= BLUSH_LIMIT):
            face, base = "smile", "smile"
        # 아래 두 가지는 지문과 겉말이 그 표정을 그리고 있으면 하지 않는다. 글과 그림이 어긋나지 않게 한다.
        # 실제 모델 기록에서 지문이 웃음이나 붉어짐을 직접 쓴 답은 5-8%였다
        text = reply.narration + " " + reply.say
        drawn = (base == "smile" and SMILE_WORDS_RE.search(text)) or (base == "blush" and BLUSH_WORDS_RE.search(text))
        if not drawn:
            # 웃는 얼굴(그 자리의 표정 포함)이 세 번 연달아 나오면 평소 얼굴로. 실제 모델 30판에서 27번 있었다
            if base == "smile" and bases[-2:] == ["smile", "smile"]:
                return "neutral"
            # 점수가 그대로인 답의 웃음과 붉어짐은 평소 얼굴로(실제 모델 21답 가운데 12답).
            # 등장, 결말, 사건이 일어난 답은 그대로 둔다. 사건 때문에 붉어지는 것은 자연스럽다
            if (reply.delta == 0 and base in ("smile", "blush")
                    and not opening and not finale and not event):
                return "neutral"
        return face

    def _intensity_meaning(self, intensity, band):
        """뇌절 강도의 뜻. 진행표의 intensities_by_band에 그 구간의 뜻이 있으면 그것을 쓴다.

        강도는 판의 차례를 따라 오르는데 기본 뜻은 설렘이 커지는 쪽이라, 호감도가 낮아도 고백에 가까운 말이 나왔다
        (사용자, 2026-11-15)."""
        by_band = (self.schedule.get("intensities_by_band") or {}).get(band) or {}
        return by_band.get(str(intensity)) or self.schedule["intensities"].get(str(intensity), "")

    def _pick_move(self):
        """옮겨 갈 곳과 까닭 (지금 장소, 새 장소, 까닭). 갈 곳이 없으면 None.

        새 장소는 등장 장소 목록에서 지금 장소가 아닌 곳이다. 비가 오고 있으면 실내만 고르고, 실외에 있었다면
        비를 피해 옮긴다. 까닭은 바깥 일(종소리, 선생님, 청소 당번)이라 지문이 전학생의 행동을 지어내지 않는다.
        """
        outdoor = set(self.seeds.get("outdoor_places") or [])
        places = [p for p in self.seeds.get("entrance", []) if p != self._place]
        if self._weather:
            places = [p for p in places if p not in outdoor]
        if not places:
            return None
        reasons = list(self.seeds.get("move_reasons") or []) or ["사람이 많아져서"]
        if self._weather and self._place in outdoor and self.seeds.get("move_reason_rain"):
            reason = self.seeds["move_reason_rain"]
        else:
            reason = self.rng.choice(reasons)
        return self._place, self.rng.choice(places), reason

    def _pick_seed(self, kind, close=False):
        """아직 안 쓴 씨앗 가운데 하나를 뽑는다. 종류가 없거나 다 썼으면 None.

        close가 참이면 사건 가운데 가까워지는 순간의 계기가 되는 것(event_hints에 있는 것)을 먼저 고른다.
        """
        if not kind:
            return None
        pool = [s for s in self.seeds.get(kind, []) if s not in self._used_seeds]
        if not pool:
            return None
        # 사건은 그 장소에서 일어날 수 있는 것만 고른다. 실전 기록: 도서관에서 "자리 바꾸기"가 나오자
        # "칠판이 잘 안 보여서", "수업 시간 내내"라며 교실처럼 말했다
        fits = self.seeds.get("event_places") or {}
        if kind == "event" and self._place:
            suitable = [s for s in pool if s not in fits or self._place in fits[s]]
            pool = suitable or pool
        # 한 묶음(event_groups)의 사건은 한 판에 하나만 쓴다. 실전 기록(2026-11-15, 18판): 천둥 번개와 소나기는
        # 어느 장소에나 맞아서 자주 뽑혔고, 8판에서 비와 천둥이 둘 다 나왔다(천둥이 나온 판은 12판)
        if kind == "event":
            groups = [members for members in (self.seeds.get("event_groups") or {}).values() if isinstance(members, list)]
            taken = {seed for members in groups if self._used_seeds.intersection(members) for seed in members}
            pool = [s for s in pool if s not in taken] or pool
        if kind == "event" and close:
            hints = self.seeds.get("event_hints") or {}
            pool = [s for s in pool if s in hints] or pool
        seed = self.rng.choice(pool)
        self._used_seeds.add(seed)
        return seed

    def _next_fallback_line(self):
        lines = self.character.get("fallback_lines") or ["(대답이 없다)"]
        line = lines[self._fallback_count % len(lines)]
        self._fallback_count += 1
        return line

    def _filter_fx(self, names, intensity):
        """센 연출은 강도 3부터, 바로 앞 답과 같은 연출은 버리고, 2개까지만."""
        heavy = set(self.fx["heavy"])
        kept = []
        for name in names:
            if intensity <= 2 and name in heavy:
                continue
            if name in self._last_fx or name in kept:
                continue
            kept.append(name)
        kept = kept[:2]
        self._last_fx = kept
        return kept

    def _grade(self):
        """최종 점수로 엔딩 등급을 정한다. endings는 min 내림차순이다."""
        for grade in self.endings:
            if self.score >= grade["min"]:
                return grade
        return self.endings[-1]


def save_result(result: dict, directory="results") -> pathlib.Path:
    """결과를 `시각_캐릭터.json`으로 저장하고 경로를 돌려준다."""
    folder = pathlib.Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        when = datetime.datetime.fromisoformat(result["finished_at"])
    except (KeyError, TypeError, ValueError):
        when = datetime.datetime.now()
    stem = f"{when:%Y%m%d-%H%M%S}_{result.get('character_id', 'unknown')}"
    path = folder / f"{stem}.json"
    n = 2
    while path.exists():  # 같은 초에 같은 캐릭터로 끝난 판이 있으면 번호를 붙인다
        path = folder / f"{stem}_{n}.json"
        n += 1
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path

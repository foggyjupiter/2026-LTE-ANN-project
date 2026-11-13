"""진행자: 한 판(등장, 답 10번, 엔딩)의 틀을 쥔다. 답의 수는 data/schedule.json이 정한다.

배우(actor)에게 지시문을 보내고, 받은 답을 규칙대로 다듬어 dict로 돌려준다.
돌려주는 값은 전부 JSON으로 바꿀 수 있어서 서버와 화면이 그대로 받아 쓴다.
"""
import datetime
import json
import pathlib
import random
import re

from . import actor, content, gimmicks, safety
from .llm import call_llm

START_SCORE = 50
# delta 한 칸이 움직이는 점수. 오르는 쪽은 작고 내리는 쪽은 크다.
# 실전 기록: 한 칸이 5점일 때 모델이 평범한 질문에도 +1을 줘서 착한 각본은 거의 늘 100점이었다.
# 지금은 다정한 말(+1)만 열 번 해도 70점(성공)에서 멈춘다. +2는 캐릭터가 속마음에 흘린 바람을 짚은 말에만
# 나오고(actor의 [주인공이 짚으면 크게 설레는 것]), 대성공(85)에는 그런 말이 서너 번 있어야 한다.
POINTS = {2: 8, 1: 2, 0: 0, -1: -5, -2: -10}
# 글자(한글, 영문, 숫자)가 이만큼 이하인 말("응", "별로", "ㅋㅋ")은 호감도를 올리지 않는다
SHORT_INPUT = 2
BLUSH_LIMIT = 4  # 한 판에 붉어진 얼굴(blush)을 이만큼까지만 낸다. 그 뒤는 smile


def band_of(score: int) -> str:
    """배우에게 알려 줄 호감도 구간."""
    if score >= 65:
        return "high"
    if score >= 40:
        return "mid"
    return "low"


def is_short_input(text: str) -> bool:
    """성의 없는 단답인가. 한글 자모만 있는 말("ㅋㅋ", "ㅇㅇ")은 글자가 없는 것으로 친다."""
    return len(re.findall(r"[0-9A-Za-z가-힣]", text or "")) <= SHORT_INPUT


def _signed(n: int) -> str:
    """팝업에 띄울 숫자: "+14", "-7", "±0"."""
    return "±0" if n == 0 else f"{n:+d}"


class Session:
    """한 판. start() → reply() 여러 번 → finish() → result() 순서로 부른다."""

    def __init__(self, character_id: str, *, llm=None, rng: random.Random | None = None):
        self.character = content.load_character(character_id)  # 없으면 KeyError
        self.llm = llm if llm is not None else (lambda m: call_llm(m, json_mode=True))
        self.rng = rng if rng is not None else random.Random()
        self.gimmick = gimmicks.get_gimmick(self.character.get("gimmick"))

        self.seeds = content.load_seeds()
        self.fx = content.load_fx()
        self.schedule = content.load_schedule()
        self.banned = content.load_banned()
        self.endings = content.load_endings()
        self.total_turns = len(self.schedule["replies"])

        self.score = START_SCORE
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
        self._place = ""         # 등장 장소. 판 내내 그곳이다
        self._events = []        # 지금까지 일어난 사건 ("답 3 소나기와 우산 하나")
        self._best = None        # (delta 절댓값, 속마음)
        self._last_choices = []  # 바로 앞 답에서 화면에 보인 선택지
        self._from_choice = False  # 이번 입력이 그 선택지 가운데 하나와 같은가
        self._ending = None
        self._finished_at = None

    # ---- 바깥에서 부르는 것 ----

    def start(self) -> dict:
        """등장. 한 번만 부른다."""
        if self.started:
            raise RuntimeError("start()는 한 번만 부를 수 있다")
        self.started = True
        self.history = [{"role": "user", "content": actor.OPENING_CUE}]
        return self._play(self.schedule["opening"], opening=True, heard=None)

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
        return self._play(self.schedule["replies"][self.turn - 1], opening=False, heard=heard)

    def finish(self) -> dict:
        """엔딩 카드. 여러 번 불러도 같은 값을 돌려준다."""
        if not self.started:
            raise RuntimeError("start()를 먼저 불러야 한다")
        if self._ending is not None:
            return self._ending

        grade = self._grade()
        messages = actor.build_ending_messages(
            self.character, list(self.history), band_name=grade["name"], score=self.score)
        ending = actor.ask_ending(self.llm, messages)
        if ending is not None:
            texts = [ending.title, ending.epilogue, ending.nickname]
            if safety.contains_banned(texts, self.banned) or actor.offstage_words(texts):
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
        seed = self._pick_seed(seed_kind)
        fx_allowed = list(self.fx["light"])
        if intensity > 2:
            fx_allowed += self.fx["heavy"]

        messages = actor.build_turn_messages(
            self.character, list(self.history),
            band=band_of(self.score),  # 이번 답을 반영하기 전 점수의 구간
            intensity=intensity,
            intensity_meaning=self.schedule["intensities"].get(str(intensity), ""),
            fx_allowed=fx_allowed,
            seed=seed,
            seed_kind=seed_kind if seed else None,
            opening=opening,
            finale=finale,
            extra="" if opening else self.gimmick.extra_instruction(list(self.past_inputs)),
            place=self._place,
            events_so_far=tuple(self._events),
        )
        fx_names = set(self.fx["light"]) | set(self.fx["heavy"])
        event_seed = seed if seed_kind == "event" else None
        used, tomorrow = actor._used_phrases(self.history)
        wishes = actor._recent_wishes(self.history)  # 앞 답들이 속마음에 흘린 바람 (이번 답의 +2를 가른다)
        previous = actor._previous_lines(self.history)
        reply = actor.ask_turn(self.llm, messages, fx_names,
                               review=lambda r: actor.review_reply(r, self.character, banned=self.banned,
                                                                   event_seed=event_seed, used_phrases=used,
                                                                   tomorrow=tomorrow, finale=finale,
                                                                   previous=previous))

        # 모델이 답을 못 줬거나, 금지어가 걸리거나, 고쳐 쓰게 했는데도 캐릭터가 모르는 말이
        # 남았으면 대체 대사로 바꾼다
        fallback = reply is None or safety.contains_banned(
            actor.reply_texts(reply), self.banned) or actor.must_drop(reply)
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
            reply.say = actor.fix_stretched_vowels(reply.say)
            reply.inner = actor.fix_stretched_vowels(reply.inner)
            # 붉어진 얼굴이 세 번 연달아 나오면 웃는 얼굴로 바꾼다. 실제 모델은 답의 3분의 2를 blush로 냈다
            if reply.face == "blush" and (self._faces[-2:] == ["blush", "blush"]
                                          or self._faces.count("blush") >= BLUSH_LIMIT):
                reply.face = "smile"
            self._faces.append(reply.face)
            # 설정을 버리라는 입력에는 점수를 올리지 않는다 (연기 규칙 7). 모델이 올려도 여기서 내린다
            if not opening and safety.looks_like_override(self.past_inputs[-1]):
                reply.delta = min(reply.delta, -1)
            if not opening:
                # 단답에는 올리지 않는다. 실전 기록: 젬마가 "응"에 +1을 줬다(사유는 자기가 꺼낸 우산)
                if is_short_input(self.past_inputs[-1]):
                    reply.delta = min(reply.delta, 0)
                # 선택지를 고른 말은 +1까지다. +2는 참가자가 직접 쓴 말에만 준다.
                # 선택지는 모델이 다정한 답을 하나 넣어 두므로, 그것만 골라도 +2가 나왔다
                if self._from_choice:
                    reply.delta = min(reply.delta, 1)
                # +2는 앞 답들이 속마음에 흘린 바람의 낱말을 참가자가 짚었을 때만 남긴다. 다정한 말만으로는
                # 대성공이 안 되게 하려는 것이다. 실전 기록: 모델이 "반가워. 여기 자주 와?"에도 2를 줬다
                if reply.delta == 2 and not actor.wish_touched(self.past_inputs[-1], wishes,
                                                                actor.name_words(self.character)):
                    reply.delta = 1

        fx = self._filter_fx(reply.fx, intensity)

        # 점수. 등장과 대체 대사에서는 움직이지 않는다
        notes = []
        delta, reason = 0, ""
        if not opening and not fallback:
            delta, note = self.gimmick.adjust_delta(reply.delta)
            reason = reply.reason
            if note:
                notes.append(note)
        old_score = self.score
        self.score = max(0, min(100, old_score + POINTS[max(-2, min(2, delta))]))
        change = self.score - old_score

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
        record = dict(eight, wish="" if fallback or finale else reply.wish)
        self.history.append({"role": "assistant", "content": json.dumps(record, ensure_ascii=False)})
        # 지금 장면: 등장 장소와 실제로 일어난 사건을 적어 두고 다음 답들의 지시문에 알려 준다
        if opening and seed_kind == "entrance" and seed:
            self._place = seed
        if seed_kind == "event" and seed and not fallback:
            self._events.append(f"답 {self.turn} {seed}")
        self._inners.append(eight["inner"])
        # 명대사 후보: delta 절댓값이 가장 큰 답. 같으면 뒤쪽. 대체 대사는 속마음이 없어서 뺀다
        if not opening and not fallback and (self._best is None or abs(delta) >= self._best[0]):
            self._best = (abs(delta), eight["inner"])

        return {
            "kind": "turn",
            "turn": self.turn,
            "total_turns": self.total_turns,
            **eight,
            "choices": shown_choices,
            "change": change,
            "score": self.score,
            "band": band_of(self.score),
            "popup": popup,
            "notes": notes,
            "heard": heard,
            "extras": extras,
            "fallback": fallback,
            "finale": finale,
            # 등장 장소. 화면이 배경을 고를 때 쓴다. 등장이 아닌 답에서는 None이다
            "place": seed if opening and seed_kind == "entrance" else None,
        }

    def _pick_seed(self, kind):
        """아직 안 쓴 씨앗 가운데 하나를 뽑는다. 종류가 없거나 다 썼으면 None."""
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

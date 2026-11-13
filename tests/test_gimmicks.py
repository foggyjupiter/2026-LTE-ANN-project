import inspect
import random
import unittest
from unittest import mock

from sogaeting import gimmicks, safety
from sogaeting.gimmicks import Gimmick, get_gimmick

TAG = " [출처 필요]"
gimmicks_default_limit = gimmicks.CITATION_LIMIT   # 시험이 한도를 바꾸기 전의 값


def make_reply(**fields):
    """Reply를 dict로 바꾼 모양. 필요한 칸만 덮어쓴다."""
    reply = {
        "narration": "", "say": "", "inner": "", "face": "neutral",
        "fx": [], "delta": 0, "reason": "", "choices": [],
    }
    reply.update(fields)
    return reply


def make_ctx(**fields):
    ctx = {"turn": 1, "total_turns": 7, "score": 50, "change": 0, "past_inputs": []}
    ctx.update(fields)
    return ctx


class ExplodingPopupTest(unittest.TestCase):
    def setUp(self):
        self.gimmick = get_gimmick("exploding_popup")

    def popup(self, **ctx):
        return self.gimmick.decorate(make_reply(), make_ctx(**ctx))

    def test_first_reply_shows_real_change(self):
        self.assertEqual(self.popup(turn=1, change=14), {"popup": "+14"})

    def test_third_reply_is_hundredfold_with_commas(self):
        self.assertEqual(self.popup(turn=3, change=-14), {"popup": "-1,400"})
        self.assertEqual(self.popup(turn=3, change=14), {"popup": "+1,400"})

    def test_second_reply_is_tenfold(self):
        self.assertEqual(self.popup(turn=2, change=7), {"popup": "+70"})

    def test_sixth_reply_is_hundred_thousandfold(self):
        self.assertEqual(self.popup(turn=6, change=14), {"popup": "+1,400,000"})

    def test_zero_change(self):
        self.assertEqual(self.popup(turn=2, change=0), {"popup": "±0"})

    def test_last_reply_is_nan(self):
        self.assertEqual(self.popup(turn=7, total_turns=7, change=14), {"popup": "NaN"})

    def test_opening_has_no_popup(self):
        self.assertEqual(self.popup(turn=0, change=0), {})

    def test_other_hooks_do_nothing(self):
        self.assertEqual(self.gimmick.transform_input("안녕", random.Random(1)), ("안녕", None))
        self.assertEqual(self.gimmick.extra_instruction(["안녕"]), "")
        self.assertEqual(self.gimmick.adjust_delta(-2), (-2, None))


class QuoteMemoryTest(unittest.TestCase):
    def setUp(self):
        self.gimmick = get_gimmick("quote_memory")

    def highlights(self, say, past_inputs):
        return self.gimmick.decorate(make_reply(say=say), make_ctx(past_inputs=past_inputs))

    def test_no_instruction_without_inputs(self):
        self.assertEqual(self.gimmick.extra_instruction([]), "")

    def test_instruction_lists_every_input_verbatim(self):
        inputs = ["떡볶이 좋아해", "사실 떡볶이는 그냥 그래", "응"]
        text = self.gimmick.extra_instruction(inputs)
        for raw in inputs:
            self.assertIn(raw, text)
        self.assertIn("1. 떡볶이 좋아해", text)
        self.assertIn("2. 사실 떡볶이는 그냥 그래", text)
        self.assertIn("3. 응", text)
        self.assertIn("say", text)
        self.assertIn("따옴표", text)
        self.assertEqual(text, text.strip())

    def test_instruction_does_not_change_the_list(self):
        inputs = ["떡볶이 좋아해", "응"]
        self.gimmick.extra_instruction(inputs)
        self.assertEqual(inputs, ["떡볶이 좋아해", "응"])

    def test_exact_quote_is_highlighted(self):
        say = "기록에 따르면 첫 번째 답에서는 '떡볶이 좋아해'라고 하셨는데요."
        self.assertEqual(
            self.highlights(say, ["떡볶이 좋아해", "오늘 날씨 좋다"]),
            {"highlights": ["떡볶이 좋아해"]},
        )

    def test_one_character_off_is_not_highlighted(self):
        say = "기록에 따르면 '떡볶이 좋아해요'라고 하셨는데요."
        self.assertEqual(self.highlights(say, ["떡볶이를 좋아해"]), {"highlights": []})
        self.assertEqual(self.highlights(say, ["떡볶이 좋아했"]), {"highlights": []})

    def test_single_character_input_is_skipped(self):
        say = "응, 이라고 하셨죠. '응'."
        self.assertEqual(self.highlights(say, ["응", " 응 "]), {"highlights": []})

    def test_order_follows_past_inputs_without_duplicates(self):
        say = "'나중에 한 말' 다음에 '먼저 한 말'을 인용합니다."
        self.assertEqual(
            self.highlights(say, ["먼저 한 말", "나중에 한 말", "먼저 한 말"]),
            {"highlights": ["먼저 한 말", "나중에 한 말"]},
        )

    def test_no_inputs_gives_empty_highlights(self):
        self.assertEqual(self.highlights("기록했습니다.", []), {"highlights": []})


class DropoutTest(unittest.TestCase):
    def setUp(self):
        self.gimmick = get_gimmick("dropout")
        self.words = ["나는", "오늘", "학교", "앞에서", "떡볶이를", "먹고", "집에", "가서", "숙제를", "했어"]

    def test_three_of_ten_words_are_masked(self):
        sent, heard = self.gimmick.transform_input(" ".join(self.words), random.Random(7))
        out = sent.split(" ")
        self.assertEqual(len(out), 10)
        self.assertEqual(out.count("■■"), 3)
        self.assertEqual(heard, sent)

    def test_unmasked_words_keep_their_places(self):
        sent, _ = self.gimmick.transform_input(" ".join(self.words), random.Random(7))
        out = sent.split(" ")
        for original, result in zip(self.words, out):
            self.assertIn(result, (original, "■■"))
        kept = [w for w in out if w != "■■"]
        self.assertEqual(kept, [w for w, r in zip(self.words, out) if r != "■■"])
        self.assertEqual(len(kept), 7)

    def test_same_seed_gives_same_mask(self):
        text = " ".join(self.words)
        first = self.gimmick.transform_input(text, random.Random(3))
        second = self.gimmick.transform_input(text, random.Random(3))
        self.assertEqual(first, second)

    def test_single_word_is_masked(self):
        self.assertEqual(self.gimmick.transform_input("안녕", random.Random(1)), ("■■", "■■"))

    def test_empty_text_is_untouched(self):
        self.assertEqual(self.gimmick.transform_input("", random.Random(1)), ("", None))
        self.assertEqual(self.gimmick.transform_input("   ", random.Random(1)), ("   ", None))

    def test_at_least_one_word_is_masked_for_short_text(self):
        for count in (2, 3, 4):
            text = " ".join(self.words[:count])
            sent, _ = self.gimmick.transform_input(text, random.Random(count))
            self.assertEqual(sent.split(" ").count("■■"), 1)

    def test_words_are_joined_with_single_spaces(self):
        sent, _ = self.gimmick.transform_input("  나는   오늘\t학교 ", random.Random(5))
        self.assertEqual(len(sent.split(" ")), 3)
        self.assertEqual(sent, sent.strip())


class ReluTest(unittest.TestCase):
    def setUp(self):
        self.gimmick = get_gimmick("relu")

    def test_negative_becomes_zero_with_note(self):
        self.assertEqual(self.gimmick.adjust_delta(-2), (0, "싫은 소리에도 기죽지 않는다"))
        self.assertEqual(self.gimmick.adjust_delta(-1), (0, "싫은 소리에도 기죽지 않는다"))

    def test_zero_passes_without_note(self):
        self.assertEqual(self.gimmick.adjust_delta(0), (0, None))

    def test_positive_passes_without_note(self):
        self.assertEqual(self.gimmick.adjust_delta(2), (2, None))


class CitationNeededTest(unittest.TestCase):
    def setUp(self):
        self.gimmick = get_gimmick("citation_needed")
        # 기본 한도는 한 답에 하나다. 여러 개가 붙는 동작은 한도를 3으로 올려 놓고 본다
        limit = mock.patch.object(gimmicks, "CITATION_LIMIT", 3)
        limit.start()
        self.addCleanup(limit.stop)

    def test_default_limit_is_one_tag_per_line(self):
        with mock.patch.object(gimmicks, "CITATION_LIMIT", gimmicks_default_limit):
            marked = self.mark("연구에 따르면 130%야")
        self.assertEqual(gimmicks_default_limit, 1)
        self.assertEqual(marked, "연구에 [출처 필요] 따르면 130%야")

    def mark(self, say):
        return self.gimmick.decorate(make_reply(say=say), make_ctx())["say_marked"]

    def test_keyword_and_percent_get_one_tag_each(self):
        marked = self.mark("연구에 따르면 130%야")
        self.assertEqual(marked.count("[출처 필요]"), 2)
        self.assertEqual(marked, "연구에 [출처 필요] 따르면 130%야 [출처 필요]")

    def test_at_most_three_tags(self):
        marked = self.mark("연구 논문 교칙 통계 연구")
        self.assertEqual(marked.count("[출처 필요]"), 3)
        self.assertEqual(marked, "연구 [출처 필요] 논문 [출처 필요] 교칙 [출처 필요] 통계 연구")

    def test_no_match_keeps_say(self):
        say = "허접 주제에 그것도 몰라? 상식이야, 상식."
        self.assertEqual(self.gimmick.decorate(make_reply(say=say), make_ctx()), {"say_marked": say})

    def test_number_with_unit_is_one_match(self):
        for token in ("130%", "100퍼센트", "2021년", "3배", "5명", "1위", "3.5배", "1,400명", "42"):
            with self.subTest(token=token):
                self.assertEqual(self.mark(f"알다시피 {token}이야"), f"알다시피 {token}이야{TAG}")

    def test_tags_never_double_up(self):
        marked = self.mark("2021년 통계로는 400% 올랐어")
        self.assertEqual(marked, "2021년 [출처 필요] 통계로는 [출처 필요] 400% [출처 필요] 올랐어")
        self.assertNotIn("[출처 필요] [출처 필요]", marked)

    def test_existing_tag_is_not_repeated(self):
        self.assertEqual(self.mark("연구 [출처 필요]에 따르면"), "연구 [출처 필요]에 따르면")
        self.assertEqual(self.mark("연구[출처 필요]에 따르면"), "연구[출처 필요]에 따르면")

    def test_empty_say(self):
        self.assertEqual(self.mark(""), "")

    def test_tag_has_one_leading_space(self):
        self.assertEqual(self.mark("논문"), "논문 [출처 필요]")


class BlackboxTest(unittest.TestCase):
    INNER = "가나다 라마바 사아자차"   # 공백이 아닌 글자 10개

    def setUp(self):
        self.gimmick = get_gimmick("blackbox")

    def mask(self, inner=INNER, **ctx):
        return self.gimmick.decorate(make_reply(inner=inner), make_ctx(**ctx))["inner_masked"]

    def test_full_score_shows_everything(self):
        self.assertEqual(self.mask(score=100), self.INNER)

    def test_zero_score_hides_everything_but_spaces(self):
        self.assertEqual(self.mask(score=0), "■■■ ■■■ ■■■■")

    def test_half_score_hides_half(self):
        masked = self.mask(score=50)
        self.assertEqual(masked.count("■"), 5)
        for original, result in zip(self.INNER, masked):
            self.assertIn(result, (original, "■"))

    def test_spaces_stay_in_place(self):
        inner = " 아 진짜\n왜 이래  큰일 "
        for score in (0, 30, 50, 80, 100):
            masked = self.mask(inner=inner, score=score)
            self.assertEqual(len(masked), len(inner))
            for original, result in zip(inner, masked):
                self.assertEqual(original.isspace(), result.isspace())
                if original.isspace():
                    self.assertEqual(result, original)

    def test_same_turn_gives_same_result(self):
        self.assertEqual(self.mask(score=50, turn=4), self.mask(score=50, turn=4))

    def test_mask_moves_between_turns(self):
        results = {self.mask(score=50, turn=turn) for turn in range(1, 8)}
        self.assertGreater(len(results), 1)

    def test_empty_inner(self):
        self.assertEqual(self.gimmick.decorate(make_reply(inner=""), make_ctx()), {"inner_masked": ""})

    def test_visible_count_follows_score(self):
        for score, hidden in ((10, 9), (30, 7), (70, 3), (90, 1)):
            with self.subTest(score=score):
                self.assertEqual(self.mask(score=score).count("■"), hidden)


class GetGimmickTest(unittest.TestCase):
    NAMES = {
        "exploding_popup": gimmicks.ExplodingPopup,
        "quote_memory": gimmicks.QuoteMemory,
        "dropout": gimmicks.Dropout,
        "relu": gimmicks.Relu,
        "citation_needed": gimmicks.CitationNeeded,
        "blackbox": gimmicks.Blackbox,
    }

    def test_six_names(self):
        for name, cls in self.NAMES.items():
            with self.subTest(name=name):
                gimmick = get_gimmick(name)
                self.assertIs(type(gimmick), cls)
                self.assertIsInstance(gimmick, Gimmick)
                self.assertEqual(gimmick.name, name)

    def test_unknown_and_none_are_base(self):
        for name in (None, "nobody", "", "RELU"):
            with self.subTest(name=name):
                self.assertIs(type(get_gimmick(name)), Gimmick)
        self.assertEqual(get_gimmick(None).name, "none")

    def test_base_changes_nothing(self):
        base = get_gimmick(None)
        self.assertEqual(base.transform_input("나는 떡볶이 좋아해", random.Random(1)),
                         ("나는 떡볶이 좋아해", None))
        self.assertEqual(base.extra_instruction(["나는 떡볶이 좋아해"]), "")
        self.assertEqual(base.adjust_delta(-2), (-2, None))
        self.assertEqual(base.adjust_delta(2), (2, None))
        reply = make_reply(say="연구에 따르면 130%야", inner="메모: 큰일")
        ctx = make_ctx(turn=3, change=14, score=64, past_inputs=["나는 떡볶이 좋아해"])
        self.assertEqual(base.decorate(reply, ctx), {})

    def test_decorate_does_not_touch_reply_or_ctx(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                reply = make_reply(say="연구에 따르면 '떡볶이 좋아해'는 130%야", inner="메모: 큰일 났다")
                ctx = make_ctx(turn=3, change=14, score=64, past_inputs=["떡볶이 좋아해"])
                before = (dict(reply), dict(ctx), list(ctx["past_inputs"]))
                get_gimmick(name).decorate(reply, ctx)
                self.assertEqual((reply, ctx, ctx["past_inputs"]), before)


class StringRuleTest(unittest.TestCase):
    def test_no_tilde_or_em_dash_in_source(self):
        for module in (gimmicks, safety):
            source = inspect.getsource(module)
            self.assertNotIn(chr(0x7E), source)
            self.assertNotIn(chr(0x2014), source)


class CitationSkipsNonStatNumbersTest(unittest.TestCase):
    """통합 때 더한 규칙: 아는 단위가 아닌 한글이 붙은 숫자에는 딱지를 붙이지 않는다."""

    def mark(self, say):
        from sogaeting.gimmicks import get_gimmick
        return get_gimmick("citation_needed").decorate({"say": say}, {})["say_marked"]

    def test_grade_and_class_numbers_are_skipped(self):
        self.assertEqual(self.mark("2학년 3반이야"), "2학년 3반이야")

    def test_cap_is_kept_for_real_stats(self):
        with mock.patch.object(gimmicks, "CITATION_LIMIT", 3):
            out = self.mark("2학년 3반 신입, 심박수가 400% 올라간다는 연구가 2019년 논문에 있어")
        self.assertEqual(out.count("[출처 필요]"), 3)
        self.assertIn("400% [출처 필요]", out)
        self.assertIn("연구가 [출처 필요]", out)
        self.assertIn("2019년 [출처 필요]", out)

    def test_rank_claim_is_tagged(self):
        self.assertEqual(self.mark("전교 1등인 나"), "전교 1등인 [출처 필요] 나")

    def test_unit_followed_by_particle(self):
        self.assertEqual(self.mark("흡수율이 130%야"), "흡수율이 130%야 [출처 필요]")

    def test_bare_number(self):
        self.assertEqual(self.mark("답은 42."), "답은 42 [출처 필요].")

    def test_tag_never_splits_a_word(self):
        # 실제 모델 대사에서 나온 꼴들. 딱지는 낱말이 끝난 자리에 붙는다
        self.assertEqual(self.mark("독서량이 987톤에 달해서"), "독서량이 987톤에 [출처 필요] 달해서")
        self.assertEqual(self.mark("그건 통계적으로…… 표본이"), "그건 통계적으로 [출처 필요]…… 표본이")
        self.assertEqual(self.mark("우리 연구소 말이야"), "우리 연구소 [출처 필요] 말이야")
        self.assertEqual(self.mark("2021년통계야"), "2021년통계야 [출처 필요]")

    def test_numbered_article_is_not_split_or_tagged(self):
        self.assertEqual(self.mark("조례 제5,100조에 있거든"), "조례 제5,100조에 있거든")
        self.assertEqual(self.mark("조례 제5조에 있거든"), "조례 제5조에 있거든")


if __name__ == "__main__":
    unittest.main()

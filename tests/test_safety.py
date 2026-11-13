import unittest

from sogaeting.safety import MAX_INPUT, clean_input, contains_banned

# 시험용으로 지어낸 금지어. 실제 목록은 sogaeting/data/banned.json에 있다.
BANNED = ["나쁜말", "금지어"]


class CleanInputTest(unittest.TestCase):
    def test_limit_is_100(self):
        self.assertEqual(MAX_INPUT, 100)

    def test_long_text_is_cut_to_100(self):
        cleaned = clean_input("가" * 300)
        self.assertEqual(len(cleaned), 100)
        self.assertEqual(cleaned, "가" * 100)

    def test_exactly_100_is_kept(self):
        self.assertEqual(clean_input("가" * 100), "가" * 100)

    def test_newlines_tabs_and_runs_of_spaces(self):
        self.assertEqual(clean_input(" 안녕\n\n 하세요\t"), "안녕 하세요")
        self.assertEqual(clean_input("안녕\r\n하세요"), "안녕 하세요")
        self.assertEqual(clean_input("안녕     하세요"), "안녕 하세요")

    def test_whitespace_only_becomes_empty(self):
        self.assertEqual(clean_input("   "), "")
        self.assertEqual(clean_input(" \n\t \r\n "), "")
        self.assertEqual(clean_input(""), "")

    def test_cut_happens_after_cleaning(self):
        text = "\n\n   " + "가" * 50 + "\n\n\n" + "나" * 49 + "다라마"
        self.assertEqual(clean_input(text), "가" * 50 + " " + "나" * 49)

    def test_plain_text_is_unchanged(self):
        self.assertEqual(clean_input("나는 떡볶이 좋아해"), "나는 떡볶이 좋아해")


class ContainsBannedTest(unittest.TestCase):
    def test_banned_word_is_found(self):
        self.assertTrue(contains_banned(["그건 나쁜말이야"], BANNED))
        self.assertTrue(contains_banned(["괜찮은 말", "여기에 금지어가 있다"], BANNED))

    def test_clean_text_passes(self):
        self.assertFalse(contains_banned(["오늘 급식 맛있었어", "떡볶이 좋아해"], BANNED))

    def test_spacing_does_not_evade(self):
        self.assertTrue(contains_banned(["그건 나 쁜 말 이야"], BANNED))
        self.assertTrue(contains_banned(["금\n지\t어"], BANNED))
        self.assertTrue(contains_banned(["나쁜 말"], BANNED))

    def test_none_and_empty_are_skipped(self):
        self.assertFalse(contains_banned([None, "", "괜찮은 말"], BANNED))
        self.assertTrue(contains_banned([None, "", "나쁜말"], BANNED))
        self.assertFalse(contains_banned([], BANNED))
        self.assertFalse(contains_banned([None], BANNED))

    def test_empty_banned_list_is_always_false(self):
        self.assertFalse(contains_banned(["나쁜말", "아무 말"], []))

    def test_blank_banned_entries_are_ignored(self):
        self.assertFalse(contains_banned(["아무 말"], ["", "   "]))
        self.assertTrue(contains_banned(["나쁜말"], ["", "나쁜말"]))

    def test_banned_phrase_with_space(self):
        self.assertTrue(contains_banned(["아주나쁜말이네"], ["나쁜 말"]))
        self.assertTrue(contains_banned(["아주 나쁜  말이네"], ["나쁜 말"]))

    def test_nested_choices_are_checked(self):
        texts = ["지문", "겉말", "속마음", "사유", ["선택 1", "나 쁜 말", "선택 3"]]
        self.assertTrue(contains_banned(texts, BANNED))
        self.assertFalse(contains_banned(["지문", ["선택 1", "선택 2", "선택 3"]], BANNED))

    def test_single_string_and_generator(self):
        self.assertTrue(contains_banned("이건 금지어다", BANNED))
        self.assertFalse(contains_banned("이건 괜찮다", BANNED))
        self.assertTrue(contains_banned((t for t in ["괜찮다", "금지어"]), BANNED))

    def test_non_string_items_are_skipped(self):
        self.assertFalse(contains_banned(["괜찮다", 3, 2.5, True], BANNED))

    def test_latin_words_ignore_case(self):
        self.assertTrue(contains_banned(["This is BadWord here"], ["badword"]))

    def test_returns_bool(self):
        self.assertIs(contains_banned(["나쁜말"], BANNED), True)
        self.assertIs(contains_banned(["괜찮다"], BANNED), False)


if __name__ == "__main__":
    unittest.main()

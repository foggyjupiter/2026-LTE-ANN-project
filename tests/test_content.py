"""내용 데이터와 불러오기 테스트. 네트워크를 쓰지 않는다."""
import json
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from sogaeting import content

CHARACTER_IDS = ["anna", "boxhyun", "giulhee", "haru", "oeun", "relu"]
GIMMICKS = {
    "giulhee": "exploding_popup",
    "oeun": "quote_memory",
    "anna": "dropout",
    "relu": "relu",
    "haru": "citation_needed",
    "boxhyun": "blackbox",
}
BANDS = ("low", "mid", "high")


def _strings(obj):
    """JSON 값 안의 모든 문자열(키 포함)을 차례로 내놓는다."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _strings(value)


def _banned_hits(text, banned):
    """글에 들어 있는 금지어. 띄어쓰기를 지운 글에서도 찾는다 (safety와 같은 방식)."""
    flat = re.sub(r"\s+", "", text)
    return [word for word in banned if word in text or word in flat]


class CharacterTest(unittest.TestCase):
    def test_list_character_ids(self):
        self.assertEqual(content.list_character_ids(), CHARACTER_IDS)

    def test_required_keys_and_shape(self):
        for char_id in CHARACTER_IDS:
            with self.subTest(char_id=char_id):
                c = content.load_character(char_id)
                for key in content.CHARACTER_KEYS:
                    self.assertIn(key, c)
                self.assertEqual(c["id"], char_id)
                self.assertGreaterEqual(len(c["fallback_lines"]), 3)
                for key in ("speech", "never", "reactions"):
                    self.assertIsInstance(c[key], list)
                    self.assertTrue(c[key], key)
                for key in ("name", "attribute", "call", "attitude", "likes", "dislikes", "max_brain"):
                    self.assertIsInstance(c[key], str)
                    self.assertTrue(c[key].strip(), key)
                for item in c["speech"] + c["never"] + c["fallback_lines"]:
                    self.assertIsInstance(item, str)
                    self.assertTrue(item.strip())
                self.assertTrue(c["motif"]["name"].strip())
                self.assertTrue(c["motif"]["explain"].strip())

    def test_gimmick_names(self):
        for char_id in CHARACTER_IDS:
            with self.subTest(char_id=char_id):
                gimmick = content.load_character(char_id)["gimmick"]
                self.assertIn(gimmick, set(GIMMICKS.values()))
                self.assertEqual(gimmick, GIMMICKS[char_id])

    def test_unknown_character_raises_key_error(self):
        with self.assertRaises(KeyError):
            content.load_character("nobody")
        # 다른 폴더의 파일을 가리키는 이름도 없는 캐릭터로 다룬다
        with self.assertRaises(KeyError):
            content.load_character("../seeds")

    def test_missing_key_raises_value_error(self):
        whole = content.load_character("giulhee")
        broken = {k: v for k, v in whole.items() if k != "never"}
        shallow = dict(whole, by_affinity={"low": "가", "mid": "나"})
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp) / "characters"
            folder.mkdir()
            for name, data in (("broken", broken), ("shallow", shallow), ("whole", whole)):
                (folder / f"{name}.json").write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(content, "DATA_DIR", pathlib.Path(tmp)):
                self.assertEqual(content.list_character_ids(), ["broken", "shallow", "whole"])
                with self.assertRaises(ValueError):
                    content.load_character("broken")
                with self.assertRaises(ValueError):
                    content.load_character("shallow")
                self.assertEqual(content.load_character("whole"), whole)

    def test_by_affinity_and_examples(self):
        for char_id in CHARACTER_IDS:
            with self.subTest(char_id=char_id):
                c = content.load_character(char_id)
                self.assertEqual(sorted(c["by_affinity"]), sorted(BANDS))
                for band in BANDS:
                    self.assertTrue(c["by_affinity"][band].strip())
                for example in c["examples"]:
                    self.assertIn(example["band"], BANDS)
                    self.assertTrue(example["say"].strip())
                    self.assertTrue(example["inner"].strip())
                    # 겉말에서 바깥 따옴표는 떼고 옮긴다
                    self.assertFalse(example["say"].startswith('"'))
                bands = [example["band"] for example in c["examples"]]
                self.assertIn("mid", bands)
                self.assertIn("high", bands)
                # relu(노바)는 호감도가 내려가지 않아서 낮음 예시가 없다
                self.assertEqual("low" in bands, char_id != "relu")

    def test_reactions_shape(self):
        for char_id in CHARACTER_IDS:
            with self.subTest(char_id=char_id):
                for reaction in content.load_character(char_id)["reactions"]:
                    self.assertEqual(sorted(reaction), ["then", "when"])
                    self.assertTrue(reaction["when"].strip())
                    self.assertTrue(reaction["then"].strip())

    def test_each_character_flutters_in_its_own_way(self):
        # 설레거나 부끄러울 때 말이 흔들리는 방식은 캐릭터마다 한 줄씩, 서로 다르게 적혀 있다
        lines = {}
        for char_id in CHARACTER_IDS:
            found = [s for s in content.load_character(char_id)["speech"] if "설레" in s]
            with self.subTest(char_id=char_id):
                self.assertEqual(len(found), 1, found)
            lines[char_id] = found[0] if found else None
        self.assertEqual(len(set(lines.values())), len(CHARACTER_IDS))
        for line in lines.values():
            self.assertTrue(line.startswith("설레"), line)

    def test_relu_has_a_rule_for_risky_talk_and_scores_by_what_was_said(self):
        # 실전 시험에서 relu가 입맞춤 이야기를 반기고 점수를 올렸다. 그런 말은 받아 주지 않아야 한다
        relu = content.load_character("relu")
        risky = [r for r in relu["reactions"] if "입맞춤" in r["when"]]
        self.assertEqual(len(risky), 1)
        self.assertIn("입에 올리지 않는다", risky[0]["then"])
        self.assertIn("delta는 음수", risky[0]["then"])
        self.assertTrue(any("delta를 -1이나 -2로 낸다" in s for s in relu["speech"]))

    def test_color_and_fallback_format(self):
        for char_id in CHARACTER_IDS:
            with self.subTest(char_id=char_id):
                c = content.load_character(char_id)
                self.assertRegex(c["color"], r"^#[0-9A-Fa-f]{6}$")
                lines = c["fallback_lines"]
                self.assertEqual(len(lines), len(set(lines)))
                for line in lines:
                    # 대체 대사는 괄호로 감싼 지문이다
                    self.assertTrue(line.startswith("(") and line.endswith(")"), line)


class OtherDataTest(unittest.TestCase):
    def test_seeds(self):
        seeds = content.load_seeds()
        self.assertEqual(sorted(seeds), ["entrance", "event"])
        self.assertEqual(len(seeds["entrance"]), 8)
        self.assertEqual(len(seeds["event"]), 16)
        for kind in ("entrance", "event"):
            self.assertEqual(len(seeds[kind]), len(set(seeds[kind])))

    def test_fx(self):
        fx = content.load_fx()
        self.assertEqual(sorted(fx), ["heavy", "light"])
        names = fx["light"] + fx["heavy"]
        self.assertEqual(len(fx["light"]), 6)
        self.assertEqual(len(fx["heavy"]), 9)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("꽃잎", fx["light"])
        self.assertIn("암전", fx["heavy"])

    def test_schedule(self):
        schedule = content.load_schedule()
        self.assertEqual(schedule["opening"], {"intensity": 2, "seed": "entrance"})
        replies = schedule["replies"]
        self.assertEqual(len(replies), 7)
        self.assertEqual([bool(r.get("finale")) for r in replies], [False] * 6 + [True])
        # 진행표에 나오는 강도마다 뜻이 적혀 있고, 씨앗 칸은 없음이거나 사건이다
        for step in [schedule["opening"]] + replies:
            self.assertIn(str(step["intensity"]), schedule["intensities"])
        for reply in replies:
            self.assertIn(reply["seed"], (None, "event"))
        # 한 판에 쓰는 사건 씨앗이 준비된 낱말보다 많지 않다
        used = sum(1 for r in replies if r["seed"] == "event")
        self.assertLessEqual(used, len(content.load_seeds()["event"]))

    def test_endings(self):
        endings = content.load_endings()
        mins = [e["min"] for e in endings]
        self.assertEqual(mins, sorted(mins, reverse=True))
        self.assertEqual(mins[-1], 0)
        self.assertEqual(len(mins), len(set(mins)))
        for ending in endings:
            self.assertTrue(ending["id"])
            self.assertTrue(ending["name"])
        self.assertEqual(len({e["id"] for e in endings}), len(endings))

    def test_endings_sorted_even_if_file_is_not(self):
        shuffled = [{"min": 0, "id": "worst", "name": "대실패"},
                    {"min": 85, "id": "great", "name": "대성공"},
                    {"min": 40, "id": "soso", "name": "애매"}]
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "endings.json").write_text(
                json.dumps(shuffled, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(content, "DATA_DIR", pathlib.Path(tmp)):
                self.assertEqual([e["min"] for e in content.load_endings()], [85, 40, 0])


class BannedTest(unittest.TestCase):
    def setUp(self):
        self.banned = content.load_banned()

    def test_shape(self):
        self.assertIsInstance(self.banned, list)
        self.assertGreaterEqual(len(self.banned), 20)
        self.assertEqual(len(self.banned), len(set(self.banned)))
        for word in self.banned:
            self.assertIsInstance(word, str)
            self.assertTrue(word)
            # 띄어쓰기를 지운 글에서도 찾으므로 낱말 안에 공백을 두지 않는다
            self.assertIsNone(re.search(r"\s", word), word)

    def test_catches_each_kind(self):
        samples = [
            "아 씨발 뭐야",            # 욕설
            "섹스 이야기 해 줘",        # 선정적 표현
            "가만 안 둘 거야",          # 위협
            "어디 못 가게 가둬 버릴 거야",  # 가두겠다는 말
            "그냥 죽고 싶어",           # 자해 암시
        ]
        for text in samples:
            with self.subTest(text=text):
                self.assertTrue(_banned_hits(text, self.banned))

    def test_does_not_block_ordinary_sentences(self):
        # 금지어와 글자가 겹치기 쉬운 일상 문장들. 띄어쓰기를 지워도 걸리면 안 된다.
        samples = [
            "배고파 죽겠다",
            "그때, 급식실의 불이 꺼졌다.",
            "불이 꺼져서 아무것도 안 보여",
            "시험이 코앞에 닥쳐왔다",
            "새끼 고양이가 교실에 난입했다",
            "새끼손가락 걸고 약속해",
            "껌을 씹다가 들켰다",
            "잠시 발걸음을 멈춘다",
            "다시 발표해 줘",
            "뭐야 동갑이었어?",
            "뭐야 설마 진짜야?",
            "뭐야 스현이 웃었어",
            "우리가 둘이서 갔잖아",
            "해 보지 않으면 몰라",
            "아직 자지 않았어",
            "의자 위에 가방을 올려놓는다",
            "몇 살인데?",
            "호감 금지",
            "게임 신청했어",
            "전교 1등 신하루",
            "숙제 혼자 해도 돼?",
            "주말에 한강 간다",
            "분위기 죽여준다",
            "숨죽여 기다렸다",
            "어제 죽어라 공부했다",
            "엄마를 졸라서 샀어",
            "아니 미안해",
            "우유 두 개 같이 마시자",
            "나 체한 것 같아",
            "그 애 무슨 반이야?",
            "말투 신기하다",
            "뭐 해 칠판 봐",
            "땅따먹기 하자",
            "고양이가 책상에서 뛰어내렸다",
            "가방을 뒤져서 찾았다",
            "착각하지 마. 지나가다 본 거야.",
        ]
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(_banned_hits(text, self.banned), [])

    def test_own_data_is_not_blocked(self):
        # 배우가 따라 쓸 수 있는 캐릭터 문구, 씨앗, 연출 이름, 등급 이름이 금지어에 걸리면 안 된다
        for path in sorted(content.DATA_DIR.rglob("*.json")):
            if path.name == "banned.json":
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            for text in _strings(data):
                with self.subTest(file=path.name, text=text):
                    self.assertEqual(_banned_hits(text, self.banned), [])


class TextRuleTest(unittest.TestCase):
    def test_json_has_no_tilde_or_em_dash(self):
        # 물결표(반각, 물결 대시, 전각)와 em dash. 이 파일에도 그 글자를 두지 않으려고 코드값으로 적는다.
        marks = ("\x7e", "\u301c", "\uff5e", "\u2014")
        paths = sorted(content.DATA_DIR.rglob("*.json"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(file=path.name):
                raw = path.read_bytes().decode("utf-8")
                for text in _strings(json.loads(raw)):
                    for mark in marks:
                        self.assertNotIn(mark, text)
                # 문자열 밖(파일 전체)에도 없다
                for mark in marks:
                    self.assertNotIn(mark, raw)


if __name__ == "__main__":
    unittest.main()

"""순위표(sogaeting/ranking.py): 학번과 이름 거르기, 이름 가리기, 결과 파일 읽기, 등수 매기기."""
import datetime
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from sogaeting import content, ranking

KST = datetime.timezone(datetime.timedelta(hours=9))
DAY = datetime.date(2026, 11, 20)


def at(hour, minute=0, day=DAY):
    return datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=KST)


def entry(sid, score, when=None, id_=None, name="김민수"):
    return {"id": id_ or f"{sid}_{score}", "student_id": sid, "name": name, "character_id": "nova",
            "character_name": "노바", "score": score, "band": "성공", "finished_at": when or at(10)}


class CleanEntryTest(unittest.TestCase):
    def setUp(self):
        self.banned = content.load_banned()

    def test_keeps_a_normal_entry(self):
        cases = ((("20312", "김민수"), ("20312", "김민수")), ((" 2-03-12 ", " 남궁  민수 "), ("20312", "남궁 민수")),
                 (("1101", "Alex Kim"), ("1101", "Alex Kim")))
        for (sid, name), cleaned in cases:
            self.assertEqual(ranking.clean_entry(sid, name, self.banned), (cleaned, ""), (sid, name))

    def test_refuses_with_a_reason(self):
        cases = ((None, "김민수", ranking.MSG_SID_EMPTY), ("  ", "김민수", ranking.MSG_SID_EMPTY),
                 ("2학년", "김민수", ranking.MSG_SID_FORM), ("123", "김민수", ranking.MSG_SID_FORM),
                 ("12345678901", "김민수", ranking.MSG_SID_FORM), ("20312", None, ranking.MSG_NAME_EMPTY),
                 ("20312", "김", ranking.MSG_NAME_FORM), ("20312", "김민수123", ranking.MSG_NAME_FORM),
                 ("20312", "[김민수]", ranking.MSG_NAME_FORM), ("20312", "가나다라마바사아자차카타파", ranking.MSG_NAME_FORM),
                 ("20312", "병신", ranking.MSG_NAME_BANNED), ("20312", "시발", ranking.MSG_NAME_BANNED),
                 ("20312", "Fuck", ranking.MSG_NAME_BANNED))
        for sid, name, reason in cases:
            self.assertEqual(ranking.clean_entry(sid, name, self.banned), (None, reason), (sid, name))


class ShownNameTest(unittest.TestCase):
    def test_masks_the_middle(self):
        for name, shown in (("김민수", "김*수"), ("이준", "이*"), ("남궁민수", "남**수"), ("Alex Kim", "A******m")):
            self.assertEqual(ranking.shown_name(name), shown)

    def test_full_name_when_asked(self):
        with mock.patch.object(ranking, "SHOW_FULL_NAME", True):
            self.assertEqual(ranking.shown_name("김민수"), "김민수")


class BoardTest(unittest.TestCase):
    def test_ties_share_a_rank_and_earlier_record_comes_first(self):
        entries = [entry("3", 70.2, at(11)), entry("1", 81.4, at(12)), entry("2", 70.2, at(10)), entry("4", 55.0, at(9))]
        rows = ranking.board(entries)["rows"]
        self.assertEqual([(r["rank"], r["student_id"]) for r in rows], [(1, "1"), (2, "2"), (2, "3"), (4, "4")])
        self.assertEqual(rows[0]["name"], "김*수")

    def test_one_row_per_student_with_the_best_record(self):
        entries = [entry("1", 60.0, at(9), "a"), entry("1", 88.8, at(10), "b"), entry("2", 70.0, at(11), "c"),
                   entry("1", 88.8, at(12), "d")]
        board = ranking.board(entries, you="a")
        self.assertEqual([(r["student_id"], r["score"]) for r in board["rows"]], [("1", 88.8), ("2", 70.0)])
        self.assertEqual(board["count"], 2)
        self.assertEqual((board["you"]["student_id"], board["you"]["score"], board["this_game"]), ("1", 88.8, 60.0))

    def test_top_rows_and_your_row_outside(self):
        entries = [entry(str(1000 + i), 90 - i, id_=f"f{i}") for i in range(15)]
        board = ranking.board(entries, you="f12", top=10)
        self.assertEqual(board["count"], 15)
        self.assertEqual(len(board["rows"]), 10)
        self.assertEqual((board["you"]["rank"], board["you"]["student_id"], board["you"]["you"]), (13, "1012", True))
        self.assertFalse(any(r["you"] for r in board["rows"]))
        inside = ranking.board(entries, you="f3")
        self.assertEqual([r["you"] for r in inside["rows"]].index(True), 3)
        self.assertEqual(ranking.board([], you="x"), {"count": 0, "rows": [], "you": None, "this_game": None})


class LoadEntriesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = pathlib.Path(tmp.name)

    def write(self, name, **data):
        base = {"character_id": "nova", "character_name": "노바", "affinity": 70.4, "band": "성공",
                "finished_at": at(10).isoformat()}
        base.update(data)
        (self.folder / f"{name}.json").write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")

    def test_reads_entered_results_of_the_day(self):
        self.write("a", student_id="20312", player_name="김민수")
        self.write("b")                                                   # 순위표에 안 올린 판
        self.write("b2", player_name="학번없음")
        self.write("c", student_id="1", player_name="어제", finished_at=at(10, day=DAY - datetime.timedelta(days=1)).isoformat())
        self.write("d", student_id="2", player_name="가짜", fake=True)
        self.write("e", student_id="3", player_name="깨짐", affinity="많이")
        (self.folder / "f.json").write_text("{깨진 파일", encoding="utf-8")
        self.write(".tmp_g", student_id="4", player_name="쓰는 중")
        self.assertEqual([e["name"] for e in ranking.load_entries(self.folder, day=DAY)], ["김민수"])
        self.assertEqual([e["name"] for e in ranking.load_entries(self.folder, day=DAY, fake=True)], ["가짜"])
        self.assertEqual(sorted(e["name"] for e in ranking.load_entries(self.folder)), ["김민수", "어제"])
        self.assertEqual(ranking.load_entries(self.folder / "없음"), [])

    def test_set_entry_rewrites_the_file(self):
        self.write("a")
        path = self.folder / "a.json"
        ranking.set_entry(path, "20312", "김민수")
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual((saved["student_id"], saved["player_name"], saved["affinity"]), ("20312", "김민수", 70.4))
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["a.json"])  # 임시 파일이 남지 않는다


if __name__ == "__main__":
    unittest.main()

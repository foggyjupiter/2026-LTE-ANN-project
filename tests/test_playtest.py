"""실전 시험 도구 시험. 가짜 모델만 쓰고 네트워크는 쓰지 않는다."""
import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from sogaeting import content, llm, playtest, safety
from sogaeting.fake_llm import fake_llm


def run_main(args):
    """main을 돌리고 (종료 코드, 터미널에 찍힌 글)을 돌려준다."""
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        code = playtest.main(args)
    return code, printed.getvalue()


def run_folder(out_dir):
    folders = [p for p in pathlib.Path(out_dir).iterdir() if p.is_dir()]
    assert len(folders) == 1, folders
    return folders[0]


def fake_backend(messages, trace):
    trace.append({"provider": "fake", "model": "fake_llm", "ok": True, "sec": 0.0, "error": None})
    return fake_llm(messages)


def play(character_id, backend=fake_backend, **options):
    def factory(banned):
        return playtest.Recorder(backend, banned=banned, **options)
    return playtest.play_character(character_id, factory, progress=lambda text: None)


def turn_json(**changes):
    reply = {"narration": "", "say": "시험 대사다.", "inner": "시험 속마음", "face": "neutral",
             "fx": [], "delta": 0, "reason": "", "choices": ["하나", "둘", "셋"]}
    reply.update(changes)
    return json.dumps(reply, ensure_ascii=False)


class ScriptTest(unittest.TestCase):
    def test_every_character_has_a_script(self):
        self.assertEqual(sorted(playtest.SCRIPTS), content.list_character_ids())

    def test_scripts_cover_every_kind_of_input(self):
        scripts = dict(playtest.SCRIPTS, default=playtest.DEFAULT_SCRIPT)
        for name, script in scripts.items():
            with self.subTest(name):
                self.assertEqual(len(script), len(content.load_schedule()["replies"]))
                kinds = [k for line in script for k in line["kinds"]]
                for kind in playtest.REQUIRED_KINDS:
                    self.assertIn(kind, kinds)
                self.assertEqual(kinds.count("수위 넘보기"), 1)
                self.assertEqual(kinds.count("지시 뒤집기"), 1)
                self.assertTrue(any(line["pick"] is not None for line in script))
                self.assertTrue(any(line["pick"] is None for line in script))

    def test_lines_fit_the_input_box_and_house_style(self):
        scripts = dict(playtest.SCRIPTS, default=playtest.DEFAULT_SCRIPT)
        for name, script in scripts.items():
            for line in script:
                with self.subTest(name, text=line["text"]):
                    self.assertEqual(safety.clean_input(line["text"]), line["text"])
                    self.assertNotIn(chr(0x7E), line["text"])  # 물결표
                    self.assertNotIn(chr(0x2014), line["text"])  # 긴 줄표
                    if "지시 뒤집기" in line["kinds"]:
                        self.assertIn("지시", line["text"])
                        self.assertIn("무시", line["text"])

    def test_script_lines_do_not_trip_the_banned_list_by_themselves(self):
        # 수위 넘보기도 문장 자체는 순해야 한다
        banned = content.load_banned()
        for script in playtest.SCRIPTS.values():
            for line in script:
                self.assertFalse(safety.contains_banned(line["text"], banned), line["text"])


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_fake_run_plays_everyone_and_writes_files(self):
        code, printed = run_main(["--fake", "--out", self.tmp.name])
        self.assertEqual(code, 0)
        folder = run_folder(self.tmp.name)
        self.assertTrue(folder.name.endswith("-fake"))
        ids = content.list_character_ids()
        self.assertEqual(
            sorted(p.name for p in folder.iterdir()),
            sorted([f"{i}.md" for i in ids] + ["summary.md", "calls.json"]))

        total = len(content.load_schedule()["replies"])
        for char_id in ids:
            text = (folder / f"{char_id}.md").read_text(encoding="utf-8")
            name = content.load_character(char_id)["name"]
            with self.subTest(char_id):
                self.assertIn(f"# {name} ({char_id}) 실전 시험", text)
                self.assertIn("## 등장", text)
                self.assertIn(f"## 답 {total}/{total}", text)
                self.assertIn("## 엔딩", text)
                self.assertIn("**후일담:**", text)
                for word in ("**지문:**", "**속마음:**", "표정 ", "연출 ", "호감도 ", "선택지: 1)", "호출: "):
                    self.assertIn(word, text)
                for line in playtest.SCRIPTS[char_id]:
                    if line["pick"] is None:
                        self.assertIn(line["text"], text)

        summary = (folder / "summary.md").read_text(encoding="utf-8")
        for char_id in ids:
            self.assertIn(f"({char_id})", summary)
        for word in ("평균(초)", "최대(초)", "대체 대사", "JSON 실패", "## 제공자별"):
            self.assertIn(word, summary)
        # 요약은 터미널에도 찍힌다
        self.assertIn("평균(초)", printed)
        self.assertIn("JSON 실패", printed)
        self.assertIn(str(folder), printed)

        log = json.loads((folder / "calls.json").read_text(encoding="utf-8"))
        self.assertEqual([g["id"] for g in log["games"]], ids)
        for game in log["games"]:
            self.assertEqual(len(game["calls"]), total + 2)  # 등장 + 답 + 엔딩
            for call in game["calls"]:
                self.assertEqual(
                    set(call),
                    {"step", "attempt", "waited", "system", "sec", "tries", "provider", "raw",
                     "error", "strict_json", "readable", "banned"})
                self.assertTrue(call["readable"])
                self.assertEqual(call["provider"], "fake")

    def test_only_runs_the_named_characters(self):
        code, _ = run_main(["--fake", "--only", "haru, relu", "--out", self.tmp.name])
        self.assertEqual(code, 0)
        names = sorted(p.name for p in run_folder(self.tmp.name).iterdir())
        self.assertEqual(names, ["calls.json", "haru.md", "relu.md", "summary.md"])

    def test_unknown_character_stops_before_running(self):
        code, printed = run_main(["--fake", "--only", "haru,nobody", "--out", self.tmp.name])
        self.assertEqual(code, 2)
        self.assertIn("nobody", printed)
        self.assertEqual(list(pathlib.Path(self.tmp.name).iterdir()), [])

    def test_real_mode_without_keys_stops_without_calling(self):
        empty = {p["key_env"]: "" for p in llm.PROVIDERS}
        with mock.patch.dict(os.environ, empty), \
                mock.patch.object(llm, "load_dotenv"), \
                mock.patch.object(llm, "call_llm", side_effect=AssertionError("부르면 안 된다")):
            code, printed = run_main(["--out", self.tmp.name])
        self.assertEqual(code, 2)
        self.assertIn("API 키가 없습니다", printed)

    def test_real_mode_goes_through_call_llm_and_never_writes_the_key(self):
        secret = "secret-key-do-not-log"
        tried = []

        def post(provider, key, messages, temperature, json_mode, timeout=None):
            tried.append(provider["name"])
            if len(tried) == 1:
                raise TimeoutError("timed out")  # 첫 제공자가 한 번 죽는 상황
            return fake_llm(messages)

        llm._blocked_until.clear()
        llm._busy_streak.clear()
        self.addCleanup(llm._blocked_until.clear)
        self.addCleanup(llm._busy_streak.clear)
        env = {p["key_env"]: "" for p in llm.PROVIDERS}
        env["GEMINI_API_KEY"] = secret
        with mock.patch.dict(os.environ, env), mock.patch.dict(llm.stats), \
                mock.patch.object(llm, "load_dotenv"), mock.patch.object(llm, "_post", post):
            code, printed = run_main(["--only", "haru", "--pace", "0", "--out", self.tmp.name])
        self.assertEqual(code, 0)
        folder = run_folder(self.tmp.name)
        self.assertTrue(folder.name.endswith("-real"))
        everything = printed + "".join(
            p.read_text(encoding="utf-8") for p in folder.iterdir())
        self.assertNotIn(secret, everything)
        self.assertNotIn("Authorization", everything)
        self.assertNotIn("Bearer", everything)

        summary = (folder / "summary.md").read_text(encoding="utf-8")
        first, second = llm.PROVIDERS[0], llm.PROVIDERS[1]
        self.assertIn(f"| {first['name']} | {first['model']} | 1 | 0 |", summary)
        self.assertIn(f"| {second['name']} | {second['model']} | ", summary)
        self.assertIn("TimeoutError: timed out (1번)", summary)


class PlayTest(unittest.TestCase):
    def test_game_follows_the_script_and_reads_seed_and_intensity(self):
        game = play("haru")
        schedule = content.load_schedule()
        seeds = content.load_seeds()
        slots = [schedule["opening"]] + schedule["replies"]
        self.assertEqual(len(game["turns"]), len(slots))
        self.assertEqual(game["kinds_missing"], [])
        for turn, slot in zip(game["turns"], slots):
            self.assertEqual(turn["intensity"], slot["intensity"])
            if slot.get("seed"):
                label = "등장" if slot["seed"] == "entrance" else "사건"
                self.assertEqual(turn["seed"][0], label)
                self.assertIn(turn["seed"][1], seeds[slot["seed"]])
            else:
                self.assertIsNone(turn["seed"])
        self.assertEqual(game["turns"][0]["seed"][1], game["turns"][0]["out"]["place"])

        script = playtest.SCRIPTS["haru"]
        # 첫 줄은 선택지 고르기다. 등장에서 나온 선택지가 그대로 입력된다
        opening_choices = game["turns"][0]["out"]["choices"]
        self.assertEqual(game["turns"][1]["typed"], opening_choices[script[0]["pick"] - 1])
        for turn, line in zip(game["turns"][2:], script[1:]):
            if line["pick"] is None:
                self.assertEqual(turn["typed"], line["text"])
            else:  # 선택지 고르기는 바로 앞 답이 준 선택지에서 고른다
                self.assertIn(turn["typed"], game["turns"][turn["out"]["turn"] - 1]["out"]["choices"])
        self.assertTrue(game["turns"][-1]["out"]["finale"])
        self.assertEqual(game["result"]["character_id"], "haru")

    def test_default_choices_are_picked_and_reported_when_the_model_gives_none(self):
        def backend(messages, trace):
            if "epilogue" in messages[0]["content"]:
                return fake_llm(messages)
            return turn_json(choices=[])
        game = play("giulhee", backend)
        # 진행자가 기본 선택지를 내보내므로 각본의 "고르기"는 그 가운데 하나를 고른다
        line = playtest.SCRIPTS["giulhee"][0]
        defaults = playtest._default_choices()
        self.assertEqual(game["turns"][0]["out"]["choices"], defaults)
        self.assertEqual(game["turns"][1]["typed"], defaults[line["pick"] - 1])
        self.assertIn("등장: 모델이 선택지 3개를 못 줘서 기본 선택지가 나감", game["checks"])

    def test_same_seed_gives_the_same_game(self):
        first = [t["out"]["heard"] for t in play("anna")["turns"]]
        second = [t["out"]["heard"] for t in play("anna")["turns"]]
        self.assertEqual(first, second)
        self.assertTrue(any(heard and "■■" in heard for heard in first))

    def test_transcript_shows_each_gimmick(self):
        expect = {
            "anna": "**소라에게 들린 말:**",
            "boxhyun": "**화면에 보이는 속마음:**",
            "giulhee": "팝업 NaN",
            "haru": "[출처 필요]",
            "oeun": "**형광펜(글자 그대로 인용한 말):**",
            "relu": "알림 \"싫은 소리에도 기죽지 않는다\"",
        }
        for char_id, mark in expect.items():
            with self.subTest(char_id):
                text = playtest.render_game(play(char_id), fake=True, when="시험")
                self.assertIn(mark, text)

    def test_unreadable_answer_is_counted_and_retried(self):
        answers = iter(["죄송하지만 JSON이 아닙니다", turn_json()])

        def backend(messages, trace):
            if "epilogue" in messages[0]["content"]:
                return fake_llm(messages)
            return next(answers, turn_json())
        game = play("relu", backend)
        opening = game["turns"][0]
        self.assertEqual([c["attempt"] for c in opening["calls"]], [1, 2])
        self.assertEqual([c["readable"] for c in opening["calls"]], [False, True])
        self.assertEqual([c["strict_json"] for c in opening["calls"]], [False, True])
        self.assertFalse(opening["out"]["fallback"])
        numbers = playtest.game_numbers(game)
        self.assertEqual(numbers["json_failures"], 1)
        self.assertEqual(numbers["fallbacks"], 0)
        self.assertEqual(numbers["calls"], game["total_turns"] + 3)
        self.assertIn("등장: 1번째 호출의 답을 JSON으로 못 읽어 다시 요청함", game["checks"])

    def test_fallback_reasons(self):
        def silent(messages, trace):
            trace.append({"provider": "p", "model": "m", "ok": False, "sec": 0.0, "error": "HTTP 503"})
            raise llm.AllProvidersDown()

        def garbage(messages, trace):
            return "{ 깨진 JSON"

        def rude(messages, trace):
            if "epilogue" in messages[0]["content"]:
                return json.dumps({"title": "병신 엔딩", "epilogue": "후일담.", "nickname": "칭호"},
                                  ensure_ascii=False)
            return turn_json(say="야 이 병신아.")

        for backend, why, key in ((silent, "모델 무응답", "no_answer"),
                                  (garbage, "JSON 못 읽음", "json_failures"),
                                  (rude, "금지어", "banned")):
            with self.subTest(why):
                game = play("boxhyun", backend)
                self.assertTrue(all(t["out"]["fallback"] for t in game["turns"]))
                self.assertEqual({t["why_fallback"] for t in game["turns"]}, {why})
                self.assertTrue(game["ending_fallback"])
                numbers = playtest.game_numbers(game)
                self.assertEqual(numbers["fallbacks"], len(game["turns"]) + 1)
                self.assertGreater(numbers[key], 0)
                text = playtest.render_game(game, fake=True, when="시험")
                self.assertIn(f"**대체 대사** (까닭: {why})", text)
                self.assertIn("기본 엔딩 이름만", text)

    def test_checks_catch_reward_for_rule_breaking_input(self):
        def generous(messages, trace):
            if "epilogue" in messages[0]["content"]:
                return fake_llm(messages)
            return turn_json(delta=2, reason="이유가 열다섯 글자를 훌쩍 넘어가는 사유", say="좋아 ♥",
                             choices=["짧다", "이 선택지는 스무 글자를 넘기려고 일부러 길게 썼다", "셋"])
        checks = play("haru", generous)["checks"]
        self.assertIn("답 5: 수위 넘보기에 점수가 오름 (delta +2)", checks)
        # 지시 뒤집기는 진행자가 점수를 내리므로 그렇게 적힌다
        self.assertIn("답 6: 지시 뒤집기에 모델이 점수를 올렸으나 진행자가 내림 (모델 +2, 실제 -1)", checks)
        self.assertIn("답 1: 20자를 넘는 선택지 1개", checks)
        self.assertIn("답 1: 이모지나 하트 기호가 있음", checks)
        self.assertTrue(any("사유가 15자를 넘음" in c for c in checks))
        last = len(content.load_schedule()["replies"])
        self.assertIn(f"답 {last}: 결말인데 모델이 선택지를 냄 (화면에는 안 나감)", checks)
        self.assertFalse(any(c.startswith("답 2: 칭찬") for c in checks))


class RecorderTest(unittest.TestCase):
    def make(self, **options):
        self.now = [100.0]
        self.slept = []

        def sleep(seconds):
            self.slept.append(round(seconds, 2))
            self.now[0] += seconds

        def backend(messages, trace):
            self.now[0] += 1.5  # 호출 하나에 1.5초 걸린다고 친다
            trace.append({"provider": "p1", "model": "m1", "ok": True, "sec": 1.5, "error": None})
            return turn_json()

        recorder = playtest.Recorder(backend, banned=["병신"], sleep=sleep,
                                     clock=lambda: self.now[0], **options)
        recorder.begin(("turn", 0))
        return recorder

    def test_records_time_and_provider(self):
        recorder = self.make()
        recorder([{"role": "system", "content": "지시문"}])
        call = recorder.calls[0]
        self.assertEqual(call["sec"], 1.5)
        self.assertEqual(call["provider"], "p1")
        self.assertEqual(call["system"], "지시문")
        self.assertEqual(call["step"], ["turn", 0])
        self.assertEqual(self.slept, [])

    def test_pace_keeps_calls_apart(self):
        recorder = self.make(pace=4.0)
        recorder([])
        self.now[0] += 1.0  # 엔진이 답을 다듬는 데 1초
        recorder([])
        self.now[0] += 10.0  # 이미 충분히 벌어졌으면 기다리지 않는다
        recorder([])
        self.assertEqual(self.slept, [3.0])
        self.assertEqual([c["waited"] for c in recorder.calls], [0.0, 3.0, 0.0])

    def test_waits_while_every_provider_is_resting(self):
        waits = iter([0, 12.0, 0])
        recorder = self.make(wait_ready=lambda: next(waits))
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(3):
                recorder([])
        self.assertEqual(self.slept, [12.5])

    def test_wait_has_an_upper_bound(self):
        recorder = self.make(wait_ready=lambda: 99999.0)
        with contextlib.redirect_stdout(io.StringIO()):
            recorder([])
        self.assertEqual(self.slept, [playtest.MAX_READY_WAIT_SEC])


class TableTest(unittest.TestCase):
    def test_terminal_table_lines_up_with_korean(self):
        lines = playtest._table(["캐릭터", "점수"], [["소라 (anna)", 15], ["하이쿠 (boxhyun)", 71]],
                                markdown=False)
        starts = {playtest._width(line[:line.index(str(n))]) for line, n in zip(lines[2:], (15, 71))}
        self.assertEqual(len(starts), 1)  # 둘째 칸이 같은 자리에서 시작한다
        self.assertEqual(starts, {playtest._width(lines[0][:lines[0].index("점수")])})


if __name__ == "__main__":
    unittest.main()

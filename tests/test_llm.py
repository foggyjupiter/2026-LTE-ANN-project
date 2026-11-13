import contextlib
import email.message
import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from sogaeting import llm

FIRST = "gemini-flash-lite"
SECOND = "gemini-flash-lite-3.1"
THIRD = "groq"


class FakeClock:
    """time 모듈 자리에 끼우는 가짜 시계. sleep은 기다리지 않고 시각만 옮긴다."""

    def __init__(self, now=1000.0):
        self.now = now
        self.slept = []

    def time(self):
        return self.now

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(round(seconds, 2))
        self.now += seconds


def http_error(code, body=b"", headers=None):
    message = email.message.Message()
    for name, value in (headers or {}).items():
        message[name] = value
    return urllib.error.HTTPError("u", code, "x", message, io.BytesIO(body))


class LlmTestCase(unittest.TestCase):
    def setUp(self):
        llm._blocked_until.clear()
        llm._busy_streak.clear()
        llm._no_json_mode.clear()
        llm.stats.update(calls=0, failures=0, last_provider=None, last_sec=None)
        self.env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k1", "GROQ_API_KEY": "k2"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.clock = FakeClock()
        clock_patch = mock.patch.object(llm, "time", self.clock)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)
        # 실패 로그가 테스트 출력에 섞이지 않게 모아 둔다
        self.printed = io.StringIO()
        redirect = contextlib.redirect_stdout(self.printed)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        self.calls = []
        self.timeouts = []

    def patch_post(self, fn, takes=0.0):
        """_post를 fn으로 바꾼다. takes는 호출 하나에 걸리는 시간(초)."""
        def wrapper(provider, key, messages, temperature, json_mode, timeout=None):
            self.calls.append((provider["name"], json_mode))
            self.timeouts.append(timeout)
            self.clock.now += takes
            return fn(provider, key, messages, temperature, json_mode)
        p = mock.patch.object(llm, "_post", wrapper)
        p.start()
        self.addCleanup(p.stop)

    def names(self):
        return [c[0] for c in self.calls]


class ProvidersTest(unittest.TestCase):
    def test_names_are_unique_and_fast_model_comes_first(self):
        names = [p["name"] for p in llm.PROVIDERS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names, [FIRST, SECOND, THIRD])
        self.assertEqual(llm.PROVIDERS[0]["model"], "gemini-3.5-flash-lite")
        # 실제로 재 보니 12번 넘게 한 번도 답하지 못한 모델은 목록에 두지 않는다
        self.assertNotIn("gemini-3.8-flash", [p["model"] for p in llm.PROVIDERS])

    def test_every_provider_has_what_post_needs(self):
        for p in llm.PROVIDERS:
            with self.subTest(p["name"]):
                self.assertTrue(p["url"].startswith("https://"))
                self.assertTrue(p["url"].endswith("/chat/completions"))
                self.assertTrue(p["key_env"])
                self.assertTrue(p["model"])
                self.assertIsInstance(p["extra"], dict)
                self.assertLess(p.get("timeout", llm.TIMEOUT_SEC), llm.TURN_BUDGET_SEC)

    def test_groq_reasoning_effort_is_a_documented_value(self):
        # GPT-OSS는 low, medium, high만 받는다
        groq = next(p for p in llm.PROVIDERS if p["name"] == "groq")
        self.assertIn(groq["extra"].get("reasoning_effort"), ("low", "medium", "high"))

    def test_gemini_does_not_send_temperature(self):
        for p in llm.PROVIDERS:
            if p["model"].startswith("gemini-"):
                self.assertIs(p.get("temperature", True), False, p["name"])


class CallLlmTest(LlmTestCase):
    def test_first_provider_answers(self):
        self.patch_post(lambda p, *a: "  안녕  ")
        self.assertEqual(llm.call_llm([{"role": "user", "content": "hi"}]), "안녕")
        self.assertEqual(self.names(), [FIRST])
        self.assertEqual(llm.stats["last_provider"], FIRST)
        self.assertIsNotNone(llm.stats["last_sec"])

    def test_429_falls_through_and_cools_down(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(429)
            return "답"
        self.patch_post(post)
        self.assertEqual(llm.call_llm([]), "답")
        self.assertEqual(self.names(), [FIRST, SECOND])
        self.assertEqual(llm._blocked_until[FIRST], 1000.0 + llm.COOLDOWN_SEC)
        self.calls.clear()
        llm.call_llm([])
        self.assertEqual(self.names(), [SECOND])  # 쿨다운 중에는 건너뜀

    def test_429_uses_retry_after_header(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(429, headers={"Retry-After": "7"})
            return "답"
        self.patch_post(post)
        llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], 1007.0)

    def test_429_ignores_absurd_retry_after(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(429, headers={"Retry-After": "86400"})
            return "답"
        self.patch_post(post)
        llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], 1000.0 + llm.COOLDOWN_SEC)

    def test_429_daily_quota_rests_long(self):
        # 2026-11-13에 실제로 받은 본문의 모양 (줄임)
        body = ('[{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": [{"violations": '
                '[{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier", "quotaValue": "500"}]}, '
                '{"retryDelay": "9462s"}]}}]').encode()

        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(429, body=body)
            return "답"
        self.patch_post(post)
        trace = []
        self.assertEqual(llm.call_llm([], trace=trace), "답")
        self.assertEqual(llm._blocked_until[FIRST], 1000.0 + llm.DAILY_COOLDOWN_SEC)
        self.assertIn("하루 한도", trace[0]["error"])

    def test_503_rests_the_provider_and_doubles_when_repeated(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(503)
            return "답"
        self.patch_post(post)
        llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], 1000.0 + llm.BUSY_COOLDOWN_SEC)
        self.calls.clear()
        llm.call_llm([])
        self.assertEqual(self.names(), [SECOND])  # 쉬는 동안에는 건너뛴다

        self.clock.now = 1000.0 + llm.BUSY_COOLDOWN_SEC  # 쉬는 시간이 끝났는데 또 503
        llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], self.clock.now + llm.BUSY_COOLDOWN_SEC * 2)

        for _ in range(10):  # 계속 죽어 있어도 상한을 넘지 않는다
            self.clock.now = llm._blocked_until[FIRST]
            llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], self.clock.now + llm.BUSY_COOLDOWN_MAX_SEC)

    def test_timeout_rests_the_provider_longer_than_a_503(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise TimeoutError("timed out")
            return "답"
        self.patch_post(post)
        llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], 1000.0 + llm.SLOW_COOLDOWN_SEC)
        self.assertGreater(llm.SLOW_COOLDOWN_SEC, llm.TURN_BUDGET_SEC)  # 같은 턴에 또 기다리지 않는다
        self.calls.clear()
        llm.call_llm([])
        self.assertEqual(self.names(), [SECOND])

    def test_success_resets_busy_streak(self):
        results = [http_error(503), "답", http_error(503)]

        def post(p, *a):
            if p["name"] != FIRST:
                return "예비"
            result = results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        self.patch_post(post)
        llm.call_llm([])
        self.clock.now += llm.BUSY_COOLDOWN_SEC
        self.assertEqual(llm.call_llm([]), "답")
        llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], self.clock.now + llm.BUSY_COOLDOWN_SEC)

    def test_all_busy_then_retries_within_the_same_call(self):
        # 실전 시험에서 본 상황: flash-lite 둘이 같이 503을 냈고 조금 뒤에는 풀려 있었다
        answers = {FIRST: [http_error(503), "두 번째에 답"], SECOND: [http_error(503)],
                   THIRD: [http_error(503)]}

        def post(p, *a):
            result = answers[p["name"]].pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        self.patch_post(post, takes=1.0)
        trace = []
        self.assertEqual(llm.call_llm([], trace=trace), "두 번째에 답")
        self.assertEqual(self.names(), [FIRST, SECOND, THIRD, FIRST])
        self.assertEqual(self.clock.slept, [1.0])  # 맨 먼저 풀리는 제공자까지만 기다린다
        self.assertEqual([t["ok"] for t in trace], [False, False, False, True])
        self.assertLessEqual(self.clock.now - 1000.0, llm.TURN_BUDGET_SEC)

    def test_gives_up_when_the_budget_runs_out(self):
        def post(p, *a):
            raise http_error(503)
        self.patch_post(post, takes=1.5)
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertLessEqual(self.clock.now - 1000.0, llm.TURN_BUDGET_SEC)
        self.assertGreater(len(self.calls), len(llm.PROVIDERS))  # 한 바퀴보다는 더 해 본다

    def test_attempt_timeout_never_exceeds_what_is_left(self):
        def post(p, *a):
            raise TimeoutError("timed out")
        self.patch_post(post, takes=6.0)
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertEqual(self.names(), [FIRST, SECOND])
        self.assertEqual(self.timeouts, [6, 4.0])  # 둘째는 남은 4초만 기다린다
        self.assertEqual(self.clock.slept, [])     # 시간 초과가 난 제공자를 기다리지 않는다

    def test_waits_for_a_provider_that_is_about_to_be_ready(self):
        # 바로 앞 호출에서 503이 나서 전부 잠깐 쉬는 중이면 대체 대사로 가지 않고 기다렸다 부른다
        for p in llm.PROVIDERS:
            llm._blocked_until[p["name"]] = 1002.5
        self.patch_post(lambda p, *a: "답")
        self.assertEqual(llm.call_llm([]), "답")
        self.assertEqual(self.clock.slept, [2.5])

    def test_does_not_wait_for_a_long_rest(self):
        for p in llm.PROVIDERS:
            llm._blocked_until[p["name"]] = 1000.0 + llm.COOLDOWN_SEC
        self.patch_post(lambda p, *a: "답")
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.clock.slept, [])

    def test_wrong_key_or_model_does_not_rest(self):
        # 400, 401, 403, 404는 설정이 틀린 것이라 매번 로그가 찍히게 둔다
        for code in (401, 403, 404):
            with self.subTest(code):
                llm._blocked_until.clear()
                self.calls.clear()

                def post(p, *a, code=code):
                    if p["name"] == FIRST:
                        raise http_error(code)
                    return "답"
                self.patch_post(post)
                llm.call_llm([])
                self.assertNotIn(FIRST, llm._blocked_until)
                self.assertIn(f"[{FIRST}] HTTP {code}", self.printed.getvalue())

    def test_wrong_key_everywhere_fails_once_per_provider(self):
        def post(p, *a):
            raise http_error(401)
        self.patch_post(post)
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertEqual(self.names(), [FIRST, SECOND, THIRD])  # 같은 호출 안에서 다시 두드리지 않는다
        self.assertEqual(self.clock.slept, [])

    def test_all_down_raises(self):
        def post(p, *a):
            raise TimeoutError("timed out")
        self.patch_post(post)
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertEqual(len(self.calls), len(llm.PROVIDERS))
        self.assertEqual(llm.stats["failures"], len(llm.PROVIDERS))
        self.calls.clear()
        with self.assertRaises(llm.AllProvidersDown):  # 전부 길게 쉬는 중이면 부르지 않고 바로 끝난다
            llm.call_llm([])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.clock.slept, [])

    def test_no_keys_raises_without_calling(self):
        self.patch_post(lambda p, *a: "답")
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GROQ_API_KEY": ""}):
            with self.assertRaises(llm.AllProvidersDown):
                llm.call_llm([])
        self.assertEqual(self.calls, [])

    def test_empty_answer_counts_as_failure(self):
        def post(p, *a):
            return "   " if p["name"] == FIRST else "답"
        self.patch_post(post)
        self.assertEqual(llm.call_llm([]), "답")
        self.assertEqual(llm.stats["failures"], 1)
        self.assertEqual(self.names(), [FIRST, SECOND])

    def test_json_mode_rejected_then_retried_without(self):
        def post(p, key, messages, temperature, json_mode):
            if json_mode:
                raise http_error(400)
            return "{}"
        self.patch_post(post)
        self.assertEqual(llm.call_llm([], json_mode=True), "{}")
        self.assertEqual(self.calls, [(FIRST, True), (FIRST, False)])
        self.calls.clear()
        llm.call_llm([], json_mode=True)
        self.assertEqual(self.calls, [(FIRST, False)])  # 거부한 제공자는 기억

    def test_trace_records_each_attempt_without_the_key(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(503, json.dumps(
                    [{"error": {"code": 503, "status": "UNAVAILABLE", "message": "high demand k1"}}]
                ).encode())
            return "답"
        self.patch_post(post)
        trace = []
        llm.call_llm([], trace=trace)
        self.assertEqual([t["provider"] for t in trace], [FIRST, SECOND])
        self.assertEqual([t["ok"] for t in trace], [False, True])
        self.assertEqual(trace[0]["model"], "gemini-3.5-flash-lite")
        self.assertEqual(trace[0]["error"], "HTTP 503 UNAVAILABLE high demand ***")
        self.assertIsNone(trace[1]["error"])
        self.assertTrue(all(isinstance(t["sec"], float) for t in trace))
        self.assertNotIn("k1", json.dumps(trace) + self.printed.getvalue())

    def test_error_body_is_printed_in_one_short_line(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(429, ("긴 글 " * 500).encode())
            return "답"
        self.patch_post(post)
        llm.call_llm([])
        line = self.printed.getvalue().strip()
        self.assertTrue(line.startswith(f"[{FIRST}] HTTP 429 긴 글"))
        self.assertNotIn("\n", line)
        self.assertLess(len(line), 400)


class SpareKeysTest(LlmTestCase):
    """GEMINI_API_KEY=키1,키2 처럼 예비 키를 여러 개 적었을 때."""

    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": " a1, ,a2 ,", "GROQ_API_KEY": ""})
        env.start()
        self.addCleanup(env.stop)
        self.keys = []

    def patch_post_by_key(self, fn):
        def post(p, key, *a):
            self.keys.append((p["name"], key))
            return fn(p, key)
        self.patch_post(post)

    def test_keys_are_split_and_blanks_dropped(self):
        self.assertEqual(llm._keys(llm.PROVIDERS[0]), ["a1", "a2"])
        self.assertEqual([slot for slot, _ in llm._slots(llm.PROVIDERS[0])], [FIRST, FIRST + "#2"])

    def test_429_moves_to_the_next_key_of_the_same_model(self):
        def post(p, key):
            if key == "a1":
                raise http_error(429)
            return "답"
        self.patch_post_by_key(post)
        self.assertEqual(llm.call_llm([]), "답")
        self.assertEqual(self.keys, [(FIRST, "a1"), (FIRST, "a2")])
        self.assertEqual(llm._blocked_until[FIRST], 1000.0 + llm.COOLDOWN_SEC)
        self.assertNotIn(FIRST + "#2", llm._blocked_until)
        self.keys.clear()
        llm.call_llm([])
        self.assertEqual(self.keys, [(FIRST, "a2")])  # 한도가 찬 키는 건너뛴다

    def test_503_rests_every_key_of_that_model(self):
        def post(p, key):
            if p["name"] == FIRST:
                raise http_error(503)
            return "답"
        self.patch_post_by_key(post)
        self.assertEqual(llm.call_llm([]), "답")
        # 과부하는 모델 사정이라 같은 모델의 다른 키로 다시 두드리지 않는다
        self.assertEqual(self.keys, [(FIRST, "a1"), (SECOND, "a1")])
        self.assertEqual(llm._blocked_until[FIRST], llm._blocked_until[FIRST + "#2"])

    def test_wrong_key_does_not_stop_the_other_key(self):
        def post(p, key):
            if key == "a1":
                raise http_error(401)
            return "답"
        self.patch_post_by_key(post)
        self.assertEqual(llm.call_llm([]), "답")
        self.assertEqual(self.keys, [(FIRST, "a1"), (FIRST, "a2")])

    def test_every_key_out_of_quota_raises(self):
        def post(p, key):
            raise http_error(429)
        self.patch_post_by_key(post)
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertEqual(len(self.keys), 4)  # 모델 둘에 키 둘씩, 한 번씩만
        self.assertEqual(llm.seconds_until_ready(), llm.COOLDOWN_SEC)

    def test_key_never_appears_in_the_log(self):
        def post(p, key):
            raise http_error(403, json.dumps({"error": {"message": f"bad key {key}"}}).encode())
        self.patch_post_by_key(post)
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertNotIn("a1", self.printed.getvalue())
        self.assertNotIn("a2", self.printed.getvalue())
        self.assertIn(FIRST + "#2", self.printed.getvalue())


class MainModelTest(LlmTestCase):
    """.env에 GEMINI_MAIN_MODEL을 적었을 때."""

    def test_default_list_is_unchanged(self):
        self.assertIs(llm._providers(), llm.PROVIDERS)

    def test_main_model_is_tried_first_then_the_usual_list(self):
        seen = []

        def post(p, *a):
            seen.append((p["name"], p["model"]))
            if p["name"] == "gemini-main":
                raise http_error(503)
            return "답"
        self.patch_post(post)
        with mock.patch.dict(os.environ, {llm.MAIN_MODEL_ENV: " gemini-3.8-flash "}):
            self.assertEqual(llm.call_llm([]), "답")
            main = llm._providers()[0]
        self.assertEqual(seen, [("gemini-main", "gemini-3.8-flash"), (FIRST, "gemini-3.5-flash-lite")])
        self.assertIs(main.get("temperature", True), False)
        self.assertIn(main["extra"]["reasoning_effort"], ("low", "medium", "high"))
        self.assertLess(main["timeout"], llm.TURN_BUDGET_SEC)

    def test_same_model_is_not_listed_twice(self):
        with mock.patch.dict(os.environ, {llm.MAIN_MODEL_ENV: "gemini-3.5-flash-lite"}):
            models = [p["model"] for p in llm._providers()]
        self.assertEqual(models.count("gemini-3.5-flash-lite"), 1)
        self.assertEqual(models[0], "gemini-3.5-flash-lite")


class PostTest(LlmTestCase):
    """요청 본문에 무엇이 실리는지."""

    def post_and_capture(self, provider_name, json_mode=True):
        provider = next(p for p in llm.PROVIDERS if p["name"] == provider_name)
        seen = {}

        def fake_urlopen(req, timeout=None):
            seen["body"] = json.loads(req.data.decode("utf-8"))
            seen["timeout"] = timeout
            seen["url"] = req.full_url
            return io.BytesIO(json.dumps(
                {"choices": [{"message": {"content": "답"}}]}).encode("utf-8"))

        with mock.patch.object(llm.urllib.request, "urlopen", fake_urlopen):
            text = llm._post(provider, "k1", [{"role": "user", "content": "hi"}], 0.9, json_mode)
        self.assertEqual(text, "답")
        return provider, seen

    def test_gemini_body(self):
        provider, seen = self.post_and_capture(FIRST)
        self.assertEqual(seen["url"], llm.GEMINI_URL)
        self.assertEqual(seen["body"]["model"], "gemini-3.5-flash-lite")
        self.assertEqual(seen["body"]["response_format"], {"type": "json_object"})
        self.assertNotIn("temperature", seen["body"])
        self.assertNotIn("reasoning_effort", seen["body"])  # flash-lite는 기본값(minimal)이 가장 빠르다
        self.assertEqual(seen["timeout"], provider["timeout"])

    def test_timeout_argument_wins_over_the_provider_value(self):
        provider = llm.PROVIDERS[0]
        seen = {}

        def fake_urlopen(req, timeout=None):
            seen["timeout"] = timeout
            return io.BytesIO(b'{"choices": [{"message": {"content": "a"}}]}')

        with mock.patch.object(llm.urllib.request, "urlopen", fake_urlopen):
            llm._post(provider, "k", [], 0.5, False, 2.5)
        self.assertEqual(seen["timeout"], 2.5)

    def test_groq_body_keeps_temperature(self):
        _, seen = self.post_and_capture("groq", json_mode=False)
        self.assertEqual(seen["url"], llm.GROQ_URL)
        self.assertEqual(seen["body"]["model"], "openai/gpt-oss-120b")
        self.assertEqual(seen["body"]["temperature"], 0.9)
        self.assertEqual(seen["body"]["reasoning_effort"], "low")
        self.assertNotIn("response_format", seen["body"])

    def test_provider_without_timeout_uses_default(self):
        provider = {"name": "x", "url": "https://example.invalid/chat/completions",
                    "key_env": "X", "model": "m", "extra": {}}
        seen = {}

        def fake_urlopen(req, timeout=None):
            seen["timeout"] = timeout
            return io.BytesIO(b'{"choices": [{"message": {"content": "a"}}]}')

        with mock.patch.object(llm.urllib.request, "urlopen", fake_urlopen):
            llm._post(provider, "k", [], 0.5, False)
        self.assertEqual(seen["timeout"], llm.TIMEOUT_SEC)


class HelpersTest(LlmTestCase):
    def test_seconds_until_ready(self):
        self.assertEqual(llm.seconds_until_ready(), 0)
        for p in llm.PROVIDERS:
            llm._blocked_until[p["name"]] = 1030.0
        llm._blocked_until[SECOND] = 1012.0
        self.assertEqual(llm.seconds_until_ready(), 12.0)
        self.assertEqual(llm.seconds_until_ready(skip={SECOND}), 30.0)
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            self.assertEqual(llm.seconds_until_ready(), 30.0)  # 키가 있는 groq만 본다
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GROQ_API_KEY": ""}):
            self.assertIsNone(llm.seconds_until_ready())

    def test_status_line(self):
        self.assertEqual(llm.status_line(), "모델 호출 0회, 실패 0회, 최근 제공자 None")
        llm.stats.update(calls=3, failures=1, last_provider=FIRST, last_sec=1.84)
        self.assertEqual(
            llm.status_line(), f"모델 호출 3회, 실패 1회, 최근 제공자 {FIRST} (1.8초)")

    def test_load_dotenv(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as f:
            f.write("# 주석\nFOO_TEST_KEY = 'abc'\nGEMINI_API_KEY=should_not_override\n")
        try:
            llm.load_dotenv(f.name)
            self.assertEqual(os.environ["FOO_TEST_KEY"], "abc")
            self.assertEqual(os.environ["GEMINI_API_KEY"], "k1")
        finally:
            os.unlink(f.name)
            os.environ.pop("FOO_TEST_KEY", None)


if __name__ == "__main__":
    unittest.main()

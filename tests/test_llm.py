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
THIRD = "gemini-flash"


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
        # 실패 로그가 테스트 출력에 섞이지 않게 모아 둔다
        self.printed = io.StringIO()
        redirect = contextlib.redirect_stdout(self.printed)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)
        self.calls = []

    def patch_post(self, fn):
        def wrapper(provider, key, messages, temperature, json_mode):
            self.calls.append((provider["name"], json_mode))
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
        self.assertEqual(names[:3], [FIRST, SECOND, THIRD])
        self.assertEqual(llm.PROVIDERS[0]["model"], "gemini-3.5-flash-lite")

    def test_every_provider_has_what_post_needs(self):
        for p in llm.PROVIDERS:
            with self.subTest(p["name"]):
                self.assertTrue(p["url"].startswith("https://"))
                self.assertTrue(p["url"].endswith("/chat/completions"))
                self.assertTrue(p["key_env"])
                self.assertTrue(p["model"])
                self.assertIsInstance(p["extra"], dict)
                self.assertLessEqual(p.get("timeout", llm.TIMEOUT_SEC), 10)

    def test_gemini_reasoning_effort_is_a_documented_value(self):
        # gemini-3.8-flash는 low, medium, high만 받는다. minimal은 오류다
        for p in llm.PROVIDERS:
            if p["model"] == "gemini-3.8-flash":
                self.assertIn(p["extra"].get("reasoning_effort"), ("low", "medium", "high"))

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
        with mock.patch.object(llm.time, "time", return_value=1000.0):
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
        with mock.patch.object(llm.time, "time", return_value=1000.0):
            llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], 1007.0)

    def test_429_ignores_absurd_retry_after(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(429, headers={"Retry-After": "86400"})
            return "답"
        self.patch_post(post)
        with mock.patch.object(llm.time, "time", return_value=1000.0):
            llm.call_llm([])
        self.assertEqual(llm._blocked_until[FIRST], 1000.0 + llm.COOLDOWN_SEC)

    def test_503_rests_the_provider_and_doubles_when_repeated(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise http_error(503)
            return "답"
        self.patch_post(post)
        now = [1000.0]
        with mock.patch.object(llm.time, "time", side_effect=lambda: now[0]):
            llm.call_llm([])
            self.assertEqual(llm._blocked_until[FIRST], 1000.0 + llm.BUSY_COOLDOWN_SEC)
            self.calls.clear()
            llm.call_llm([])
            self.assertEqual(self.names(), [SECOND])  # 쉬는 동안에는 시간을 버리지 않는다

            now[0] = 1000.0 + llm.BUSY_COOLDOWN_SEC  # 쉬는 시간이 끝났는데 또 503
            llm.call_llm([])
            self.assertEqual(llm._blocked_until[FIRST], now[0] + llm.BUSY_COOLDOWN_SEC * 2)

            for _ in range(10):  # 계속 죽어 있어도 상한을 넘지 않는다
                now[0] = llm._blocked_until[FIRST]
                llm.call_llm([])
            self.assertEqual(llm._blocked_until[FIRST], now[0] + llm.BUSY_COOLDOWN_MAX_SEC)

    def test_timeout_rests_the_provider(self):
        def post(p, *a):
            if p["name"] == FIRST:
                raise TimeoutError("timed out")
            return "답"
        self.patch_post(post)
        llm.call_llm([])
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
        now = [1000.0]
        with mock.patch.object(llm.time, "time", side_effect=lambda: now[0]):
            llm.call_llm([])
            now[0] += llm.BUSY_COOLDOWN_SEC
            self.assertEqual(llm.call_llm([]), "답")
            llm.call_llm([])
            self.assertEqual(llm._blocked_until[FIRST], now[0] + llm.BUSY_COOLDOWN_SEC)

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

    def test_all_down_raises(self):
        def post(p, *a):
            raise TimeoutError("timed out")
        self.patch_post(post)
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertEqual(len(self.calls), len(llm.PROVIDERS))
        self.assertEqual(llm.stats["failures"], len(llm.PROVIDERS))
        self.calls.clear()
        with self.assertRaises(llm.AllProvidersDown):  # 전부 쉬는 중이면 부르지 않고 바로 끝난다
            llm.call_llm([])
        self.assertEqual(self.calls, [])

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

    def test_gemini_flash_sends_low_reasoning_effort(self):
        _, seen = self.post_and_capture(THIRD)
        self.assertEqual(seen["body"]["reasoning_effort"], "low")
        self.assertNotIn("temperature", seen["body"])

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
        with mock.patch.object(llm.time, "time", return_value=1000.0):
            self.assertEqual(llm.seconds_until_ready(), 0)
            for p in llm.PROVIDERS:
                llm._blocked_until[p["name"]] = 1030.0
            llm._blocked_until[SECOND] = 1012.0
            self.assertEqual(llm.seconds_until_ready(), 12.0)
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

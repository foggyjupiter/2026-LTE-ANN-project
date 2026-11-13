import io
import os
import unittest
import urllib.error
from unittest import mock

from sogaeting import llm


def http_error(code):
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b""))


class CallLlmTest(unittest.TestCase):
    def setUp(self):
        llm._blocked_until.clear()
        llm._no_json_mode.clear()
        llm.stats.update(calls=0, failures=0, last_provider=None)
        self.env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k1", "GROQ_API_KEY": "k2"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.calls = []

    def patch_post(self, fn):
        def wrapper(provider, key, messages, temperature, json_mode):
            self.calls.append((provider["name"], json_mode))
            return fn(provider, key, messages, temperature, json_mode)
        p = mock.patch.object(llm, "_post", wrapper)
        p.start()
        self.addCleanup(p.stop)

    def test_first_provider_answers(self):
        self.patch_post(lambda p, *a: "  안녕  ")
        self.assertEqual(llm.call_llm([{"role": "user", "content": "hi"}]), "안녕")
        self.assertEqual([c[0] for c in self.calls], ["gemini-flash"])
        self.assertEqual(llm.stats["last_provider"], "gemini-flash")

    def test_429_falls_through_and_cools_down(self):
        def post(p, *a):
            if p["name"] == "gemini-flash":
                raise http_error(429)
            return "답"
        self.patch_post(post)
        self.assertEqual(llm.call_llm([]), "답")
        self.assertEqual([c[0] for c in self.calls], ["gemini-flash", "gemini-flash-lite"])
        self.calls.clear()
        llm.call_llm([])
        self.assertEqual([c[0] for c in self.calls], ["gemini-flash-lite"])  # 쿨다운 중에는 건너뜀

    def test_all_down_raises(self):
        def post(p, *a):
            raise TimeoutError("timed out")
        self.patch_post(post)
        with self.assertRaises(llm.AllProvidersDown):
            llm.call_llm([])
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(llm.stats["failures"], 3)

    def test_no_keys_raises_without_calling(self):
        self.patch_post(lambda p, *a: "답")
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GROQ_API_KEY": ""}):
            with self.assertRaises(llm.AllProvidersDown):
                llm.call_llm([])
        self.assertEqual(self.calls, [])

    def test_empty_answer_counts_as_failure(self):
        def post(p, *a):
            return "   " if p["name"] == "gemini-flash" else "답"
        self.patch_post(post)
        self.assertEqual(llm.call_llm([]), "답")

    def test_json_mode_rejected_then_retried_without(self):
        def post(p, key, messages, temperature, json_mode):
            if json_mode:
                raise http_error(400)
            return "{}"
        self.patch_post(post)
        self.assertEqual(llm.call_llm([], json_mode=True), "{}")
        self.assertEqual(self.calls, [("gemini-flash", True), ("gemini-flash", False)])
        self.calls.clear()
        llm.call_llm([], json_mode=True)
        self.assertEqual(self.calls, [("gemini-flash", False)])  # 거부한 제공자는 기억

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

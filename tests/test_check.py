import io
import os
import socket
import tempfile
import unittest
import urllib.error
from unittest import mock

from sogaeting import check, llm
from tests.test_llm import http_error


class LoadDotenvEncodingTest(unittest.TestCase):
    """윈도우 메모장과 PowerShell이 붙이는 BOM 때문에 키를 못 읽으면 모든 답이 대체 대사가 된다."""

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        llm.dotenv_ignored.clear()

    def load(self, data):
        with tempfile.NamedTemporaryFile("wb", suffix=".env", delete=False) as f:
            f.write(data)
        self.addCleanup(os.unlink, f.name)
        llm.load_dotenv(f.name)

    def test_utf8_with_bom(self):
        self.load(b"\xef\xbb\xbfGEMINI_API_KEY=abc\n")
        self.assertEqual(os.environ.get("GEMINI_API_KEY"), "abc")

    def test_utf16_with_bom_and_crlf(self):
        self.load("GEMINI_API_KEY=abc,def\r\nGROQ_API_KEY=g\r\n".encode("utf-16"))
        self.assertEqual(os.environ.get("GEMINI_API_KEY"), "abc,def")
        self.assertEqual(llm.key_counts()["GEMINI_API_KEY"], 2)
        self.assertEqual(llm.key_counts()["GROQ_API_KEY"], 1)

    def test_computer_environment_wins_and_is_reported(self):
        os.environ["GEMINI_API_KEY"] = "old"
        self.load(b"GEMINI_API_KEY=new\n")
        self.assertEqual(os.environ["GEMINI_API_KEY"], "old")
        self.assertEqual(llm.dotenv_ignored, ["GEMINI_API_KEY"])


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "k1,k2"}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        llm.dotenv_ignored.clear()
        self.lines = []

    def run_check(self, post):
        return check.run("없는-파일.env", out=self.lines.append, post=post)

    def text(self):
        return "\n".join(self.lines)

    def test_every_key_and_model_is_tried_and_explained(self):
        daily = b'{"error": {"details": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}}'

        def post(provider, key, *rest):
            if key == "k1":
                raise http_error(429, body=daily)
            return "안녕"
        self.assertEqual(self.run_check(post), 0)
        text = self.text()
        self.assertIn("GEMINI_API_KEY 2개", text)
        self.assertIn("1번째 키: HTTP 429. 오늘 하루 한도를 다 썼습니다", text)
        self.assertIn("[됨] gemini-3.5-flash-lite, GEMINI_API_KEY 2번째 키", text)
        self.assertNotIn("k1", text)  # 키 값은 찍지 않는다
        self.assertNotIn("k2", text)

    def test_nothing_answers(self):
        def post(provider, key, *rest):
            if provider["model"].startswith("gemini-3.5"):
                raise http_error(400, body=b'{"error": {"message": "API key not valid. Please pass a valid API key."}}')
            if key == "k1":
                raise socket.timeout("timed out")
            raise urllib.error.URLError("getaddrinfo failed")
        self.assertEqual(self.run_check(post), 1)
        text = self.text()
        self.assertIn("키가 틀렸습니다", text)
        self.assertIn("답이 없습니다", text)
        self.assertIn("연결하지 못했습니다", text)
        self.assertIn("모든 대답이 괄호 속 행동", text)

    def test_no_keys(self):
        os.environ.pop("GEMINI_API_KEY")
        self.assertEqual(self.run_check(lambda *a: "안녕"), 2)
        self.assertIn("키를 하나도 읽지 못했습니다", self.text())

    def test_ignored_dotenv_value_is_reported(self):
        llm.dotenv_ignored.append("GEMINI_API_KEY")
        self.run_check(lambda *a: "안녕")
        self.assertIn("환경변수에 이미 있어서", self.text())


if __name__ == "__main__":
    unittest.main()

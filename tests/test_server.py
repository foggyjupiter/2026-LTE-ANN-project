import collections
import contextlib
import http.server
import io
import json
import pathlib
import socket
import socketserver
import tempfile
import threading
import time
import types
import unittest
import urllib.error
import urllib.request
from unittest import mock

from sogaeting import content, llm, server
from sogaeting.director import Session
from sogaeting.fake_llm import fake_llm

TOTAL = len(content.load_schedule()["replies"])  # 한 판의 답 수

ORDER = ["astra", "gemma", "sora", "nova", "mistral", "haiku"]
CARD_KEYS = {"id", "name", "attribute", "motif", "color"}
RESULT_KEYS = {
    "character_id", "character_name", "affinity", "band", "ending_title", "nickname", "finished_at",
}
JSON_TYPE = "application/json; charset=utf-8"
FONT_BYTES = b"wOF2" + bytes(range(32))  # 글꼴 흉내만 내는 작은 파일
SECRET = "web 폴더 밖에 있는 파일"
TILDE = chr(126)       # 문자열에 쓰면 안 되는 두 글자. 이 파일에도 직접 적지 않는다
EM_DASH = chr(0x2014)


class Response(collections.namedtuple("Response", "status headers raw")):
    def json(self):
        return json.loads(self.raw.decode("utf-8"))


def has_hangul(text):
    return any("가" <= ch <= "힣" for ch in text)


class ServerCase(unittest.TestCase):
    """가짜 모델, 임시 결과 폴더, 임시 web 폴더로 서버를 띄우고 urllib로 요청한다."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name).resolve()
        self.results = self.root / "results"
        self.web = self.root / "web"
        (self.web / "fonts").mkdir(parents=True)
        (self.web / "index.html").write_text(
            "<!doctype html><title>시험 화면</title>", encoding="utf-8")
        (self.web / "app.js").write_text("// 시험용\n", encoding="utf-8")
        (self.web / "fonts" / "Galmuri11.woff2").write_bytes(FONT_BYTES)
        # web 폴더 바로 바깥의 파일. 이 파일이 새어 나가면 안 된다
        (self.root / "server.py").write_text(f"# {SECRET}\n", encoding="utf-8")
        # 환경변수에 프록시가 있어도 거치지 않는다
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.server = self.start()

    def start(self, **over):
        """서버를 하나 띄운다. 테스트가 끝나면 알아서 내린다."""
        options = {"llm": fake_llm, "results_dir": self.results, "web_dir": self.web}
        options.update(over)
        srv = server.make_server("127.0.0.1", 0, **options)
        thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()

        def stop():
            srv.shutdown()
            srv.server_close()
            thread.join(5)

        self.addCleanup(stop)
        return srv

    def request(self, method, path, body=None, *, data=None, headers=None, srv=None):
        srv = srv or self.server
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        url = "http://127.0.0.1:%d%s" % (srv.server_address[1], path)
        req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(req, timeout=10) as res:
                return Response(res.status, res.headers, res.read())
        except urllib.error.HTTPError as error:
            raw = error.read()
            error.close()
            return Response(error.code, error.headers, raw)

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body, **kw)

    def new_game(self, character="mistral", **kw):
        """판을 만들고 (판 id, 응답 내용)을 돌려준다."""
        res = self.post("/api/session", {"character": character}, **kw)
        self.assertEqual(res.status, 201, res.raw)
        created = res.json()
        return created["session_id"], created

    def reply(self, session_id, text="안녕, 반가워", **kw):
        return self.post(f"/api/session/{session_id}/reply", {"text": text}, **kw)

    def result_files(self):
        return sorted(self.results.glob("*.json")) if self.results.exists() else []

    def assert_error(self, res, status):
        """오류 응답은 {"error": 한국어 설명} 하나뿐이다."""
        self.assertEqual(res.status, status, res.raw)
        self.assertEqual(res.headers["Content-Type"], JSON_TYPE)
        body = res.json()
        self.assertEqual(set(body), {"error"})
        self.assertIsInstance(body["error"], str)
        self.assertTrue(has_hangul(body["error"]), body)
        self.assertNotIn("Traceback", res.raw.decode("utf-8"))
        self.assertNotIn(TILDE, body["error"])
        self.assertNotIn(EM_DASH, body["error"])


def in_parallel(*jobs):
    """함수들을 동시에 돌리고 결과를 순서대로 돌려준다."""
    results = [None] * len(jobs)

    def run(index, job):
        results[index] = job()

    threads = [threading.Thread(target=run, args=(i, job)) for i, job in enumerate(jobs)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(20)
    return results


class MakeServerTest(unittest.TestCase):
    def test_make_server_does_not_start_serving(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = threading.active_count()
            srv = server.make_server("127.0.0.1", 0, llm=fake_llm, results_dir=tmp, web_dir=tmp)
            try:
                self.assertIsInstance(srv, http.server.ThreadingHTTPServer)
                self.assertGreater(srv.server_address[1], 0)  # port=0이면 빈 포트를 받는다
                self.assertLessEqual(threading.active_count(), before)  # 새로 도는 스레드가 없다
                with socket.create_connection(srv.server_address[:2], timeout=2) as sock:
                    sock.sendall(b"GET /api/characters HTTP/1.0\r\n\r\n")
                    sock.settimeout(0.2)
                    with self.assertRaises(TimeoutError):  # 아무도 답하지 않는다
                        sock.recv(1)
            finally:
                srv.server_close()


class CharactersTest(ServerCase):
    def test_six_characters_in_order_with_keys(self):
        res = self.get("/api/characters")
        self.assertEqual(res.status, 200)
        cards = res.json()
        self.assertEqual([card["id"] for card in cards], ORDER)
        for card in cards:
            self.assertEqual(set(card), CARD_KEYS | {"intro", "note"})
            for key, value in card.items():
                self.assertIsInstance(value, str, key)
                if key != "note":  # 안내는 장치가 있는 캐릭터에게만 있다
                    self.assertTrue(value, key)
            character = content.load_character(card["id"])
            self.assertEqual(card["name"], character["name"])
            self.assertEqual(card["attribute"], character["attribute"])
            self.assertEqual(card["motif"], character["motif"]["name"])
            self.assertEqual(card["color"], character["color"])
            # 하이쿠만 속마음이 가려진다는 안내가 붙는다
            self.assertEqual(bool(card["note"]), card["id"] == "haiku")

    def test_intro_is_first_sentence_of_attitude(self):
        cards = {card["id"]: card for card in self.get("/api/characters").json()}
        self.assertEqual(cards["mistral"]["intro"], "연애도 소개팅도 다 해 본 척 여유를 부린다.")
        self.assertEqual(cards["nova"]["intro"], "밝고 적극적으로 다가온다.")
        for char_id, card in cards.items():
            attitude = content.load_character(char_id)["attitude"]
            self.assertTrue(attitude.startswith(card["intro"]), char_id)
            self.assertTrue(card["intro"].endswith("."), char_id)
            self.assertNotIn(". ", card["intro"], char_id)  # 한 문장뿐이다

    def test_first_sentence_helper(self):
        self.assertEqual(server._first_sentence("첫째다. 둘째다."), "첫째다.")
        self.assertEqual(server._first_sentence("정말? 그렇다."), "정말?")
        self.assertEqual(server._first_sentence("  3.5점을 줬다. 끝.  "), "3.5점을 줬다.")
        self.assertEqual(server._first_sentence('"가지 마."라고 했다. 끝.'), '"가지 마."라고 했다.')
        self.assertEqual(server._first_sentence("마침표 없는 글"), "마침표 없는 글")
        self.assertEqual(server._first_sentence(""), "")


class FullGameTest(ServerCase):
    def test_full_game_saves_exactly_one_result(self):
        res = self.post("/api/session", {"character": "mistral"})
        self.assertEqual(res.status, 201)
        created = res.json()
        self.assertEqual(set(created), {"session_id", "character", "turn"})
        sid = created["session_id"]
        self.assertIsInstance(sid, str)
        self.assertTrue(sid)
        self.assertEqual(set(created["character"]), CARD_KEYS)
        self.assertEqual(created["character"]["id"], "mistral")
        self.assertEqual(created["character"]["name"], "미스트랄")
        self.assertEqual(created["character"]["motif"], "들키면 귀여운 허세")
        opening = created["turn"]
        self.assertEqual((opening["kind"], opening["turn"], opening["finale"]), ("turn", 0, False))
        self.assertEqual(opening["total_turns"], TOTAL)

        for n in range(1, TOTAL + 1):
            res = self.reply(sid, f"{n}번째로 하는 말")
            self.assertEqual(res.status, 200, res.raw)
            turn = res.json()
            self.assertEqual((turn["kind"], turn["turn"]), ("turn", n))
            self.assertEqual(turn["finale"], n == TOTAL)  # 마지막 답만 finale이다
            self.assertIn(f"{n}번째로 하는 말", turn["say"])
        self.assertEqual(self.result_files(), [])  # finish 전에는 저장하지 않는다

        res = self.post(f"/api/session/{sid}/finish")
        self.assertEqual(res.status, 200, res.raw)
        finished = res.json()
        self.assertEqual(set(finished), {"ending", "result"})
        self.assertEqual(finished["ending"]["kind"], "ending")
        self.assertEqual(finished["ending"]["character_id"], "mistral")
        self.assertFalse(finished["ending"]["early"])
        self.assertEqual(set(finished["result"]), RESULT_KEYS)
        self.assertEqual(finished["result"]["affinity"], finished["ending"]["score"])

        files = self.result_files()
        self.assertEqual(len(files), 1)
        # 가짜 모델로 돈 판은 결과 파일에 표시가 붙는다(실제 모델 서버의 순위표에 안 들어가게)
        self.assertEqual(json.loads(files[0].read_text(encoding="utf-8")), dict(finished["result"], fake=True))

        again = self.post(f"/api/session/{sid}/finish")  # 다시 불러도 같은 값, 파일은 그대로
        self.assertEqual(again.status, 200)
        self.assertEqual(again.json(), finished)
        self.assertEqual(self.result_files(), files)

        res = self.get(f"/api/session/{sid}/result")
        self.assertEqual(res.status, 200)
        self.assertEqual(res.json(), finished["result"])
        self.assertEqual(self.result_files(), files)

    def test_finish_right_after_start(self):
        sid, _ = self.new_game("astra")
        res = self.post(f"/api/session/{sid}/finish", {})  # 빈 dict를 실어 보내도 된다
        self.assertEqual(res.status, 200, res.raw)
        self.assertTrue(res.json()["ending"]["early"])
        self.assertEqual(len(self.result_files()), 1)

    def test_every_character_can_start(self):
        for char_id in ORDER:
            sid, created = self.new_game(char_id)
            self.assertEqual(created["character"]["id"], char_id)
            self.assertEqual(created["turn"]["turn"], 0)

    def test_games_do_not_know_each_other(self):
        first, _ = self.new_game("mistral")
        second, _ = self.new_game("mistral")
        self.assertNotEqual(first, second)
        self.assertEqual(self.reply(first).json()["turn"], 1)
        self.assertEqual(self.reply(first).json()["turn"], 2)
        self.assertEqual(self.reply(second).json()["turn"], 1)
        self.post(f"/api/session/{first}/finish")
        self.assertEqual(self.reply(second).json()["turn"], 2)  # 옆 판이 끝나도 이어진다


class RetryTest(ServerCase):
    """화면이 시간 초과로 답을 못 받고 같은 답을 다시 보내도 턴이 하나 더 지나가지 않는다."""

    def send(self, sid, text, turn):
        return self.post(f"/api/session/{sid}/reply", {"text": text, "turn": turn})

    def test_same_answer_with_same_turn_is_answered_once(self):
        sid, _ = self.new_game()
        first = self.send(sid, "안녕, 반가워", 1)
        again = self.send(sid, "안녕, 반가워", 1)
        self.assertEqual((first.status, again.status), (200, 200))
        self.assertEqual(again.json(), first.json())
        self.assertEqual(again.json()["turn"], 1)
        self.assertEqual(self.send(sid, "안녕, 반가워", 2).json()["turn"], 2)  # 다음 턴의 같은 말은 새 답이다

    def test_without_turn_number_every_request_is_a_new_answer(self):
        # 브라우저 화면은 턴 번호를 보내지 않는다. 예전처럼 동작한다
        sid, _ = self.new_game()
        self.assertEqual(self.reply(sid).json()["turn"], 1)
        self.assertEqual(self.reply(sid).json()["turn"], 2)

    def test_different_text_is_not_a_retry(self):
        sid, _ = self.new_game()
        self.send(sid, "하나", 1)
        self.assertEqual(self.send(sid, "둘", 1).json()["turn"], 2)


class FailingOnce:
    """fake_llm을 감싸서 정한 차례(등장이 0)에 정한 횟수만큼 AllProvidersDown을 던진다."""

    def __init__(self, turn, times=1):
        self.turn = turn
        self.left = times

    def __call__(self, messages):
        if sum(1 for m in messages if m["role"] == "assistant") == self.turn and self.left > 0:
            self.left -= 1
            raise llm.AllProvidersDown()
        return fake_llm(messages)


class ModelBusyTest(ServerCase):
    """모델이 답을 못 주면(503) 대체 대사로 넘기지 않고, 503으로 알려 같은 말을 다시 보내게 한다."""

    def test_reply_gets_503_and_the_same_answer_can_be_sent_again(self):
        srv = self.start(llm=FailingOnce(turn=1))
        sid, _ = self.new_game(srv=srv)
        body = {"text": "안녕, 반가워", "turn": 1}
        busy = self.post(f"/api/session/{sid}/reply", body, srv=srv)
        self.assertEqual(busy.status, 503)
        self.assertEqual(busy.json()["error"], server.MSG_MODEL_BUSY_TURN)
        again = self.post(f"/api/session/{sid}/reply", body, srv=srv)
        self.assertEqual(again.status, 200)
        self.assertEqual(again.json()["turn"], 1)
        self.assertFalse(again.json()["fallback"])

    def test_new_game_gets_503_and_can_be_tried_again(self):
        srv = self.start(llm=FailingOnce(turn=0))
        busy = self.post("/api/session", {"character": "astra"}, srv=srv)
        self.assertEqual(busy.status, 503)
        self.assertEqual(busy.json()["error"], server.MSG_MODEL_BUSY_START)
        sid, created = self.new_game("astra", srv=srv)
        self.assertEqual(created["turn"]["turn"], 0)


class ErrorTest(ServerCase):
    def test_unknown_character_is_404(self):
        for name in ("nobody", "", "../banned", "HARU"):
            self.assert_error(self.post("/api/session", {"character": name}), 404)
        self.assertEqual(self.get("/api/status").json()["sessions"], 0)

    def test_character_missing_or_not_string_is_400(self):
        for body in ({}, {"character": 3}, {"character": None}, {"character": ["mistral"]},
                     {"text": "mistral"}):
            self.assert_error(self.post("/api/session", body), 400)

    def test_unknown_session_is_404(self):
        self.assert_error(self.reply("nope"), 404)
        self.assert_error(self.post("/api/session/nope/finish"), 404)
        self.assert_error(self.get("/api/session/nope/result"), 404)
        self.assertEqual(self.result_files(), [])

    def test_empty_text_is_400(self):
        sid, _ = self.new_game()
        for text in ("", "   ", "\n\t "):
            self.assert_error(self.reply(sid, text), 400)
        self.assertEqual(self.reply(sid, "이제 제대로 보낸다").json()["turn"], 1)  # 차례가 안 넘어갔다

    def test_text_that_is_a_number_is_400(self):
        sid, _ = self.new_game()
        self.assert_error(self.post(f"/api/session/{sid}/reply", {"text": 7}), 400)
        for body in ({}, {"text": None}, {"text": ["안녕"]}, {"text": {"a": 1}}, {"character": "mistral"}):
            self.assert_error(self.post(f"/api/session/{sid}/reply", body), 400)
        self.assertEqual(self.reply(sid).json()["turn"], 1)

    def test_body_that_is_not_json_is_400(self):
        sid, _ = self.new_game()
        for data in (b"mistral", b"", b"{character: mistral}", b'{"character": "mistral"', b"\xff\xfe\x00"):
            self.assert_error(self.post("/api/session", data=data), 400)
            self.assert_error(self.post(f"/api/session/{sid}/reply", data=data), 400)
        self.assertEqual(self.get("/api/status").json()["sessions"], 1)

    def test_body_that_is_not_an_object_is_400(self):
        sid, _ = self.new_game()
        for data in (b'["mistral"]', b'"mistral"', b"3", b"null", b"true"):
            self.assert_error(self.post("/api/session", data=data), 400)
            self.assert_error(self.post(f"/api/session/{sid}/reply", data=data), 400)

    def test_broken_content_length_is_400(self):
        for value in ("abc", "-5", "1.5"):
            res = self.post("/api/session", data=b"", headers={"Content-Length": value})
            self.assert_error(res, 400)

    def test_reply_to_finished_game_is_409(self):
        sid, _ = self.new_game()
        self.reply(sid)
        self.assertEqual(self.post(f"/api/session/{sid}/finish").status, 200)
        self.assert_error(self.reply(sid, "한마디만 더"), 409)
        self.assertEqual(len(self.result_files()), 1)

    def test_reply_after_the_last_is_409(self):
        sid, _ = self.new_game()
        for n in range(TOTAL):
            self.assertEqual(self.reply(sid).status, 200)
        self.assert_error(self.reply(sid, "한 번 더"), 409)
        self.assertEqual(self.post(f"/api/session/{sid}/finish").status, 200)  # 엔딩은 볼 수 있다

    def test_result_of_unfinished_game_is_404(self):
        sid, _ = self.new_game()
        self.assert_error(self.get(f"/api/session/{sid}/result"), 404)
        self.reply(sid)
        self.assert_error(self.get(f"/api/session/{sid}/result"), 404)
        self.assertEqual(self.result_files(), [])

    def test_get_api_session_is_405(self):
        res = self.get("/api/session")
        self.assert_error(res, 405)
        self.assertEqual(res.headers["Allow"], "POST")

    def test_other_wrong_methods_are_405(self):
        sid, _ = self.new_game()
        cases = [
            ("POST", "/api/characters", "GET"),
            ("POST", "/api/status", "GET"),
            ("PUT", "/api/session", "POST"),
            ("DELETE", f"/api/session/{sid}", None),  # 이런 주소는 없다
            ("GET", f"/api/session/{sid}/reply", "POST"),
            ("GET", f"/api/session/{sid}/finish", "POST"),
            ("POST", f"/api/session/{sid}/result", "GET"),
            ("DELETE", f"/api/session/{sid}/result", "GET"),
            ("POST", "/", "GET"),
            ("PUT", "/app.js", "GET"),
        ]
        for method, path, allow in cases:
            res = self.request(method, path, {"text": "안녕"} if method != "GET" else None)
            if allow is None:
                self.assert_error(res, 404)
            else:
                self.assert_error(res, 405)
                self.assertEqual(res.headers["Allow"], allow, path)
        self.assertEqual(self.reply(sid).json()["turn"], 1)  # 거절된 요청은 판을 건드리지 않았다

    def test_unknown_path_is_404(self):
        sid, _ = self.new_game()
        for path in ("/api", "/api/", "/api/nope", "/api/characters/", "/api/session/",
                     f"/api/session/{sid}", f"/api/session/{sid}/nope",
                     f"/api/session/{sid}/reply/extra", "/nothing.html"):
            self.assert_error(self.get(path), 404)
            self.assert_error(self.post(path, {"text": "안녕"}), 404)

    def test_body_over_10kb_is_400(self):
        sid, _ = self.new_game()
        frame = len(json.dumps({"text": ""}).encode("utf-8"))

        def body_of(size):
            data = json.dumps({"text": "a" * (size - frame)}).encode("utf-8")
            self.assertEqual(len(data), size)
            return data

        # 한도를 1바이트 넘기면 거절한다
        self.assert_error(self.post(f"/api/session/{sid}/reply", data=body_of(10 * 1024 + 1)), 400)
        self.assert_error(self.reply(sid, "가" * 5000), 400)  # 15KB
        self.assert_error(self.post("/api/session", {"character": "mistral", "pad": "a" * 20000}), 400)
        self.assert_error(self.post(f"/api/session/{sid}/finish", {"pad": "a" * 20000}), 400)
        self.assertEqual(self.result_files(), [])
        # 딱 10KB까지는 받는다. 거절된 요청은 차례를 쓰지 않았다
        res = self.post(f"/api/session/{sid}/reply", data=body_of(10 * 1024))
        self.assertEqual(res.status, 200, res.raw)
        self.assertEqual(res.json()["turn"], 1)

    def test_unexpected_error_is_500_and_traceback_stays_in_terminal(self):
        def broken_llm(messages):
            raise ZeroDivisionError("모델 안쪽의 비밀스러운 오류")

        srv = self.start(llm=broken_llm)
        terminal = io.StringIO()
        with contextlib.redirect_stderr(terminal):
            res = self.post("/api/session", {"character": "mistral"}, srv=srv)
        self.assert_error(res, 500)
        self.assertNotIn("ZeroDivisionError", res.raw.decode("utf-8"))
        self.assertNotIn("비밀스러운", res.raw.decode("utf-8"))
        self.assertIn("Traceback", terminal.getvalue())
        self.assertIn("ZeroDivisionError", terminal.getvalue())
        # 서버는 죽지 않고 다음 요청을 받는다
        self.assertEqual(self.get("/api/characters", srv=srv).status, 200)
        self.assertEqual(self.get("/api/status", srv=srv).json()["sessions"], 0)

    def test_failed_save_is_500_and_next_finish_saves_once(self):
        sid, _ = self.new_game()
        terminal = io.StringIO()
        with mock.patch.object(server, "save_result", side_effect=PermissionError("못 쓴다")), \
                contextlib.redirect_stderr(terminal):
            self.assert_error(self.post(f"/api/session/{sid}/finish"), 500)
        self.assertIn("PermissionError", terminal.getvalue())
        self.assertEqual(self.result_files(), [])
        first = self.post(f"/api/session/{sid}/finish")
        self.assertEqual(first.status, 200)
        self.assertEqual(self.post(f"/api/session/{sid}/finish").json(), first.json())
        self.assertEqual(len(self.result_files()), 1)


class StaticTest(ServerCase):
    def test_root_is_index_html(self):
        res = self.get("/")
        self.assertEqual(res.status, 200)
        self.assertTrue(res.headers["Content-Type"].startswith("text/html"))
        self.assertEqual(res.raw, (self.web / "index.html").read_bytes())
        self.assertIn("시험 화면", res.raw.decode("utf-8"))
        self.assertEqual(self.get("/index.html").raw, res.raw)

    def test_font_is_woff2(self):
        res = self.get("/fonts/Galmuri11.woff2")
        self.assertEqual(res.status, 200)
        self.assertEqual(res.headers["Content-Type"], "font/woff2")
        self.assertEqual(res.raw, FONT_BYTES)
        self.assertEqual(res.headers["Content-Length"], str(len(FONT_BYTES)))

    def test_paths_leaving_web_dir_are_404(self):
        outside = self.root / "server.py"
        self.assertTrue(outside.is_file())  # 막지 않으면 읽을 수 있는 파일이다
        absolute = outside.as_posix()
        paths = [
            "/../server.py",
            "/%2e%2e/server.py",
            "/%2E%2E/server.py",
            "/..%2fserver.py",
            "/%2e%2e%2fserver.py",
            "/fonts/../../server.py",
            "/fonts/%2e%2e/%2e%2e/server.py",
            "/./../server.py",
            "/..%5cserver.py",
            "/..\\server.py",
            "/" + absolute,                        # //tmp/.../server.py
            "/%2f" + absolute.lstrip("/"),         # 인코딩된 절대 경로
            "/../web/../server.py",
            "/%00",
            "/index.html%00.js",
        ]
        for path in paths:
            res = self.get(path)
            self.assert_error(res, 404)
            self.assertNotIn(SECRET, res.raw.decode("utf-8"), path)

    def test_link_pointing_outside_web_dir_is_404(self):
        try:
            (self.web / "link.py").symlink_to(self.root / "server.py")
        except (OSError, NotImplementedError):
            self.skipTest("이 컴퓨터에서는 링크를 만들 수 없다")
        self.assert_error(self.get("/link.py"), 404)

    def test_dot_dot_that_stays_inside_is_served(self):
        res = self.get("/fonts/../app.js")
        self.assertEqual(res.status, 200)
        self.assertEqual(res.raw, (self.web / "app.js").read_bytes())

    def test_query_string_is_ignored(self):
        res = self.get("/?character=mistral")
        self.assertEqual(res.status, 200)
        self.assertTrue(res.headers["Content-Type"].startswith("text/html"))
        self.assertEqual(res.raw, (self.web / "index.html").read_bytes())
        self.assertEqual(self.get("/app.js?v=2&x=../../server.py").status, 200)
        self.assertEqual(self.get("/fonts/Galmuri11.woff2?").status, 200)
        self.assertEqual(len(self.get("/api/characters?now=1").json()), 6)

    def test_missing_file_and_folder_are_404(self):
        for path in ("/nope.js", "/fonts", "/fonts/", "/fonts/nope.woff2", "/index.html/x",
                     "/favicon.ico"):
            self.assert_error(self.get(path), 404)

    def test_content_type_follows_extension(self):
        expected = {
            "page.html": "text/html; charset=utf-8",
            "style.css": "text/css; charset=utf-8",
            "fx.js": "text/javascript; charset=utf-8",
            "data.json": JSON_TYPE,
            "assets/characters/mistral/smile.png": "image/png",
            "assets/photo.jpg": "image/jpeg",
            "assets/face.svg": "image/svg+xml",
            "fonts/Galmuri14.woff2": "font/woff2",
            "assets/pop.mp3": "audio/mpeg",
            "assets/pop.ogg": "audio/ogg",
            "assets/BIG.PNG": "image/png",
            "assets/characters/README.md": "application/octet-stream",
        }
        for name, content_type in expected.items():
            path = self.web / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode("utf-8"))
            res = self.get("/" + name)
            self.assertEqual(res.status, 200, name)
            self.assertEqual(res.headers["Content-Type"], content_type, name)
            self.assertEqual(res.raw, name.encode("utf-8"))

    def test_file_name_with_hangul_and_space(self):
        (self.web / "assets").mkdir()
        (self.web / "assets" / "하루 얼굴.png").write_bytes(b"png")
        res = self.get("/assets/%ED%95%98%EB%A3%A8%20%EC%96%BC%EA%B5%B4.png")
        self.assertEqual((res.status, res.raw), (200, b"png"))

    def test_default_web_dir_is_the_package_folder(self):
        srv = self.start(web_dir=None)
        res = self.get("/fonts/Galmuri11.woff2", srv=srv)  # 레포에 들어 있는 진짜 글꼴
        self.assertEqual(res.status, 200)
        self.assertEqual(res.headers["Content-Type"], "font/woff2")
        self.assertEqual(res.raw, (server.WEB_DIR / "fonts" / "Galmuri11.woff2").read_bytes())
        self.assert_error(self.get("/../server.py", srv=srv), 404)
        self.assert_error(self.get("/%2e%2e/server.py", srv=srv), 404)
        self.assert_error(self.get("/../data/banned.json", srv=srv), 404)

    def test_every_response_says_no_store(self):
        sid, _ = self.new_game()
        responses = [
            self.get("/"),
            self.get("/fonts/Galmuri11.woff2"),
            self.get("/nope.js"),
            self.get("/../server.py"),
            self.get("/api/characters"),
            self.get("/api/status"),
            self.post("/api/session", {"character": "mistral"}),
            self.post("/api/session", {"character": "nobody"}),
            self.reply(sid),
            self.reply(sid, ""),
            self.get("/api/session"),
            self.post(f"/api/session/{sid}/finish"),
            self.get(f"/api/session/{sid}/result"),
            self.reply(sid),
            self.request("FOO", "/api/characters"),  # http.server가 스스로 거절하는 요청
        ]
        self.assertEqual([r.status for r in responses],
                         [200, 200, 404, 404, 200, 200, 201, 404, 200, 400, 405, 200, 200, 409, 501])
        for res in responses:
            self.assertEqual(res.headers["Cache-Control"], "no-store", res.status)
        self.assert_error(responses[-1], 501)


class CleanupTest(ServerCase):
    def test_ttl_zero_drops_the_previous_game(self):
        srv = self.start(session_ttl=0)
        first, _ = self.new_game(srv=srv)
        self.assertEqual(self.reply(first, srv=srv).status, 200)  # 새 판이 생기기 전에는 살아 있다
        second, _ = self.new_game(srv=srv)
        self.assert_error(self.reply(first, srv=srv), 404)
        self.assert_error(self.post(f"/api/session/{first}/finish", srv=srv), 404)
        self.assert_error(self.get(f"/api/session/{first}/result", srv=srv), 404)
        self.assertEqual(self.reply(second, srv=srv).status, 200)
        self.assertEqual(self.get("/api/status", srv=srv).json()["sessions"], 1)
        self.assertEqual(self.result_files(), [])

    def test_games_within_ttl_are_kept(self):
        first, _ = self.new_game()
        second, _ = self.new_game()
        third, _ = self.new_game()
        self.assertEqual(self.get("/api/status").json()["sessions"], 3)
        for sid in (first, second, third):
            self.assertEqual(self.reply(sid).status, 200)

    def test_only_idle_games_are_dropped(self):
        idle, _ = self.new_game()
        busy, _ = self.new_game()
        for entry in self.server.app._entries.values():
            entry.last_seen -= 1000  # 두 판 모두 오래 묵은 것으로 만든다 (기본 ttl은 900초)
        self.assertEqual(self.reply(busy).status, 200)  # 요청이 오면 시계가 다시 돈다
        self.new_game()
        self.assert_error(self.reply(idle), 404)
        self.assertEqual(self.reply(busy).status, 200)
        self.assertEqual(self.get("/api/status").json()["sessions"], 2)


class KoreanTest(ServerCase):
    def test_korean_is_sent_as_utf8(self):
        res = self.get("/api/characters")
        self.assertEqual(res.headers["Content-Type"], JSON_TYPE)
        self.assertIn("미스트랄".encode("utf-8"), res.raw)
        self.assertIn("들키면 귀여운 허세".encode("utf-8"), res.raw)
        self.assertNotIn(b"\\u", res.raw)  # \uXXXX 꼴로 바뀌지 않았다

        res = self.post("/api/session", {"character": "mistral"})
        self.assertEqual(res.headers["Content-Type"], JSON_TYPE)
        self.assertIn("가짜 모델".encode("utf-8"), res.raw)
        self.assertNotIn(b"\\u", res.raw)
        sid = res.json()["session_id"]

        res = self.reply(sid, "한글로 보낸 말")
        self.assertIn("한글로 보낸 말".encode("utf-8"), res.raw)
        self.assertNotIn(b"\\u", res.raw)

        res = self.post(f"/api/session/{sid}/finish")
        self.assertIn("시연 엔딩".encode("utf-8"), res.raw)
        self.assertNotIn(b"\\u", res.raw)

        res = self.post("/api/session", {"character": "nobody"})
        self.assertEqual(res.headers["Content-Type"], JSON_TYPE)
        self.assertIn("캐릭터".encode("utf-8"), res.raw)
        self.assertNotIn(b"\\u", res.raw)

    def test_half_an_emoji_does_not_break_the_reply(self):
        sid, _ = self.new_game()
        res = self.post(f"/api/session/{sid}/reply", data=b'{"text": "\\ud83d \xec\x95\x88\xeb\x85\x95"}')
        self.assertEqual(res.status, 200, res.raw)
        self.assertEqual(res.json()["turn"], 1)  # 본문이 올바른 UTF-8이고 차례가 넘어갔다
        self.assertIn("안녕", res.json()["say"])


class StatusTest(ServerCase):
    def test_status_keys_and_session_count(self):
        numbers = {"calls": 12, "failures": 3, "last_provider": "gemini-flash"}
        with mock.patch.dict(llm.stats, numbers):
            res = self.get("/api/status")
            self.assertEqual(res.status, 200)
            self.assertEqual(res.json(), {**numbers, "sessions": 0})
            self.new_game()
            sid, _ = self.new_game()
            self.assertEqual(self.get("/api/status").json(), {**numbers, "sessions": 2})
            self.post(f"/api/session/{sid}/finish")
            self.assertEqual(self.get("/api/status").json()["sessions"], 2)  # 끝난 판도 결과를 읽게 둔다


class LlmChoiceTest(ServerCase):
    def test_without_llm_the_engine_default_is_used(self):
        seen = []

        class Spy(Session):
            def __init__(self, *args, **kwargs):
                seen.append((args, dict(kwargs)))
                kwargs["llm"] = fake_llm  # 테스트에서는 실제 모델을 부르지 않는다
                super().__init__(*args, **kwargs)

        with mock.patch.object(server, "Session", Spy):
            self.new_game("nova", srv=self.start(llm=None))
            self.new_game("sora")
        self.assertEqual(seen, [(("nova",), {}), (("sora",), {"llm": fake_llm})])


class Counting:
    """fake_llm을 감싸서 동시에 들어와 있는 호출 수를 센다."""

    def __init__(self, delay):
        self.delay = delay
        self.active = 0
        self.peak = 0
        self.lock = threading.Lock()

    def __call__(self, messages):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(self.delay)
        with self.lock:
            self.active -= 1
        return fake_llm(messages)


class Meeting:
    """barrier가 걸려 있는 동안에는 호출 두 개가 동시에 들어와야만 답한다."""

    def __init__(self):
        self.barrier = None

    def __call__(self, messages):
        if self.barrier is not None:
            self.barrier.wait()  # 혼자 기다리다 시간이 다 되면 BrokenBarrierError
        return fake_llm(messages)


class LockTest(ServerCase):
    def test_requests_for_one_game_run_one_at_a_time(self):
        slow = Counting(0.08)
        srv = self.start(llm=slow)
        sid, _ = self.new_game(srv=srv)
        slow.peak = 0
        results = in_parallel(
            lambda: self.reply(sid, "먼저 보낸 말", srv=srv),
            lambda: self.reply(sid, "겹쳐서 보낸 말", srv=srv),
            lambda: self.reply(sid, "또 겹쳐서 보낸 말", srv=srv),
        )
        self.assertEqual([r.status for r in results], [200, 200, 200])
        self.assertEqual(sorted(r.json()["turn"] for r in results), [1, 2, 3])
        self.assertEqual(slow.peak, 1)  # 같은 판에서는 한 번에 하나만 모델을 불렀다

    def test_different_games_do_not_wait_for_each_other(self):
        meeting = Meeting()
        srv = self.start(llm=meeting)
        first, _ = self.new_game(srv=srv)
        second, _ = self.new_game(srv=srv)
        meeting.barrier = threading.Barrier(2, timeout=5)
        results = in_parallel(
            lambda: self.reply(first, srv=srv),
            lambda: self.reply(second, srv=srv),
        )
        self.assertEqual([r.status for r in results], [200, 200])

    def test_new_games_can_start_at_the_same_time(self):
        meeting = Meeting()
        srv = self.start(llm=meeting)
        meeting.barrier = threading.Barrier(2, timeout=5)
        results = in_parallel(
            lambda: self.post("/api/session", {"character": "mistral"}, srv=srv),
            lambda: self.post("/api/session", {"character": "gemma"}, srv=srv),
        )
        self.assertEqual([r.status for r in results], [201, 201])
        self.assertEqual(self.get("/api/status", srv=srv).json()["sessions"], 2)

    def test_finish_twice_at_once_saves_one_file(self):
        slow = Counting(0.1)
        srv = self.start(llm=slow)
        sid, _ = self.new_game(srv=srv)
        results = in_parallel(*[lambda: self.post(f"/api/session/{sid}/finish", srv=srv)] * 3)
        self.assertEqual([r.status for r in results], [200, 200, 200])
        self.assertEqual(results[0].json(), results[1].json())
        self.assertEqual(results[0].json(), results[2].json())
        self.assertEqual(len(self.result_files()), 1)


class TerminalTest(ServerCase):
    def test_requests_are_not_logged(self):
        terminal = io.StringIO()
        with contextlib.redirect_stderr(terminal), contextlib.redirect_stdout(terminal):
            sid, _ = self.new_game()
            self.reply(sid)
            self.get("/")
            self.get("/nope.js")
            self.get("/api/session")
            self.post(f"/api/session/{sid}/finish")
        self.assertEqual(terminal.getvalue(), "")

    def test_hook_runs_after_each_request_that_called_the_model(self):
        calls = []
        self.server.app.after_model_call = lambda: calls.append(1)
        self.get("/api/characters")
        self.get("/api/status")
        self.get("/")
        self.post("/api/session", {"character": "nobody"})
        self.assertEqual(len(calls), 0)
        sid, _ = self.new_game()
        self.assertEqual(len(calls), 1)
        self.reply(sid, "")
        self.reply(sid, 3)
        self.get(f"/api/session/{sid}/result")
        self.assertEqual(len(calls), 1)
        self.reply(sid)
        self.assertEqual(len(calls), 2)
        self.post(f"/api/session/{sid}/finish")
        self.assertEqual(len(calls), 3)
        self.post(f"/api/session/{sid}/finish")  # 두 번째는 모델을 부르지 않는다
        self.get(f"/api/session/{sid}/result")
        self.reply(sid)
        self.assertEqual(len(calls), 3)

    def test_broken_hook_does_not_break_the_game(self):
        def hook():
            raise OSError("터미널이 닫혔다")

        self.server.app.after_model_call = hook
        with contextlib.redirect_stderr(io.StringIO()):
            sid, _ = self.new_game()
            self.assertEqual(self.reply(sid).json()["turn"], 1)


class MainTest(unittest.TestCase):
    def run_main(self, argv):
        out = io.StringIO()
        with mock.patch.object(llm, "load_dotenv") as load_dotenv, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = server.main(argv)
        return code, out.getvalue(), load_dotenv

    def test_fake_server_starts_prints_address_and_stops_quietly(self):
        made = []
        real_make_server = server.make_server

        def spy(*args, **kwargs):
            made.append((args, kwargs, real_make_server(*args, **kwargs)))
            return made[-1][2]

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(server, "make_server", spy), \
                mock.patch.object(socketserver.BaseServer, "serve_forever",
                                  side_effect=KeyboardInterrupt) as serve_forever:
            code, out, load_dotenv = self.run_main(["--fake", "--port", "0", "--results", tmp])
            args, kwargs, srv = made[0]
            self.assertEqual(code, 0)
            load_dotenv.assert_called_once_with()
            serve_forever.assert_called_once()
            self.assertEqual(args, ("127.0.0.1", 0))
            self.assertEqual(kwargs, {"llm": fake_llm, "results_dir": tmp})
            self.assertIn(f"http://127.0.0.1:{srv.server_address[1]}/", out)
            self.assertIn("가짜 모델", out)
            self.assertNotIn("Traceback", out)
            self.assertNotIn("KeyboardInterrupt", out)
            self.assertEqual(srv.socket.fileno(), -1)  # 소켓을 닫고 끝났다

    def test_defaults_use_the_real_model_and_print_status_line(self):
        stub = mock.Mock()
        stub.server_address = ("127.0.0.1", 8000)
        stub.app = types.SimpleNamespace(after_model_call=None)
        stub.serve_forever.side_effect = KeyboardInterrupt
        with mock.patch.object(server, "make_server", return_value=stub) as make_server:
            code, out, load_dotenv = self.run_main([])
        self.assertEqual(code, 0)
        load_dotenv.assert_called_once_with()
        make_server.assert_called_once_with("127.0.0.1", 8000, llm=None, results_dir="results")
        stub.server_close.assert_called_once_with()
        self.assertIn("http://127.0.0.1:8000/", out)
        self.assertNotIn("가짜 모델", out)

        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            stub.app.after_model_call()
        self.assertEqual(printed.getvalue(), llm.status_line() + "\n")

    def test_host_and_port_options(self):
        stub = mock.Mock()
        stub.server_address = ("0.0.0.0", 8791)
        stub.app = types.SimpleNamespace(after_model_call=None)
        stub.serve_forever.side_effect = KeyboardInterrupt
        with mock.patch.object(server, "make_server", return_value=stub) as make_server:
            code, out, _ = self.run_main(["--host", "0.0.0.0", "--port", "8791", "--results", "out"])
        self.assertEqual(code, 0)
        make_server.assert_called_once_with("0.0.0.0", 8791, llm=None, results_dir="out")
        self.assertIn("http://localhost:8791/", out)

    def test_port_in_use_is_explained_without_traceback(self):
        with mock.patch.object(server, "make_server", side_effect=OSError(98, "Address already in use")):
            code, out, _ = self.run_main(["--fake", "--port", "8791"])
        self.assertEqual(code, 1)
        self.assertIn("8791", out)
        self.assertTrue(has_hangul(out))
        self.assertNotIn("Traceback", out)


class SourceTest(unittest.TestCase):
    def test_no_tilde_or_em_dash_in_server_source(self):
        source = pathlib.Path(server.__file__).read_text(encoding="utf-8")
        self.assertNotIn(TILDE, source)
        self.assertNotIn(EM_DASH, source)


if __name__ == "__main__":
    unittest.main()


class RankingTest(ServerCase):
    """엔딩 뒤 학번과 이름으로 순위표에 올리기, 오늘의 순위표."""

    def finished_game(self, character="mistral", replies=2):
        sid, _ = self.new_game(character)
        for n in range(replies):
            self.assertEqual(self.reply(sid, f"{n + 1}번째 말").status, 200)
        res = self.post(f"/api/session/{sid}/finish")
        self.assertEqual(res.status, 200, res.raw)
        return sid, res.json()

    def rank(self, sid, student_id="20312", name="김민수"):
        return self.post(f"/api/session/{sid}/rank", {"student_id": student_id, "name": name})

    def test_entry_goes_into_the_result_and_the_board(self):
        sid, finished = self.finished_game()
        res = self.rank(sid, " 203-12 ", "  김민수 ")
        self.assertEqual(res.status, 200, res.raw)
        body = res.json()
        self.assertEqual((body["student_id"], body["name"]), ("20312", "김*수"))
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["rows"], [body["you"]])
        self.assertEqual((body["you"]["rank"], body["you"]["student_id"], body["you"]["name"]), (1, "20312", "김*수"))
        self.assertTrue(body["you"]["you"])
        self.assertEqual(body["you"]["score"], finished["result"]["affinity"])
        self.assertEqual(body["this_game"], finished["result"]["affinity"])
        self.assertEqual(body["you"]["character_name"], "미스트랄")
        # 파일에는 학번과 이름이 다 남는다(상품을 줄 때 본다)
        saved = json.loads(self.result_files()[0].read_text(encoding="utf-8"))
        self.assertEqual((saved["student_id"], saved["player_name"]), ("20312", "김민수"))
        # 다시 보내면 고쳐 적는다
        res = self.rank(sid, "20313", "김민수")
        self.assertEqual(res.json()["you"]["student_id"], "20313")
        self.assertEqual(len(self.result_files()), 1)

    def test_one_row_per_student_with_the_best_game(self):
        games = [self.finished_game(replies=n) for n in (1, 2, 3)]
        scores = [g[1]["result"]["affinity"] for g in games]
        for sid, _ in games:
            body = self.rank(sid).json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["you"]["score"], max(scores))
        self.assertEqual(body["this_game"], scores[-1])

    def test_public_board_lists_entered_games_only(self):
        first, _ = self.finished_game("mistral")
        self.finished_game("astra")  # 순위표에 올리지 않은 판은 없다
        self.rank(first, "10101", "이준")
        res = self.get("/api/ranking")
        self.assertEqual(res.status, 200)
        body = res.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual([(r["student_id"], r["name"]) for r in body["rows"]], [("10101", "이*")])
        self.assertIsNone(body["you"])
        self.assertIsNone(body["this_game"])
        self.assertFalse(body["rows"][0]["you"])
        self.assertRegex(body["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertNotIn("이준", res.raw.decode("utf-8"))  # 순위표에는 이름이 다 나가지 않는다

    def test_real_model_board_skips_fake_games(self):
        sid, _ = self.finished_game()
        self.rank(sid)
        real = self.start(llm=lambda messages: fake_llm(messages))  # 가짜 모델 함수가 아니면 실제 모델 서버로 본다
        body = self.get("/api/ranking", srv=real).json()
        self.assertEqual((body["count"], body["rows"]), (0, []))

    def test_bad_entries_are_refused(self):
        sid, _ = self.finished_game()
        cases = (("", "김민수", "학번을"), ("2학년3반", "김민수", "숫자로"), ("123", "김민수", "숫자로"),
                 ("20312", "", "이름을"), ("20312", "김", "2-12자"), ("20312", "김민수!", "2-12자"),
                 ("20312", "시발", "올릴 수 없어요"), (20312, "김민수", "학번을"))
        for student_id, name, word in cases:
            res = self.rank(sid, student_id, name)
            self.assert_error(res, 400)
            self.assertIn(word, res.json()["error"], (student_id, name))
        saved = json.loads(self.result_files()[0].read_text(encoding="utf-8"))
        self.assertNotIn("student_id", saved)

    def test_entry_needs_a_finished_game(self):
        sid, _ = self.new_game()
        self.assert_error(self.rank(sid), 409)
        self.assert_error(self.rank("nobody"), 404)
        self.assert_error(self.get(f"/api/session/{sid}/rank"), 405)
        self.assert_error(self.post("/api/ranking"), 405)

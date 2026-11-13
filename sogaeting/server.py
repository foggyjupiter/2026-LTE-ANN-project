"""로컬 서버: 엔진의 Session을 JSON API로 감싸고 sogaeting/web/ 의 파일을 내준다.

실행: python3 -m sogaeting.server [--fake] [--host H] [--port N] [--results DIR]

판의 상태는 이 프로세스의 메모리에만 있고 서버를 끄면 사라진다.
표준 라이브러리만 쓴다.
"""
import argparse
import http.server
import json
import pathlib
import re
import secrets
import sys
import threading
import time
import traceback
import urllib.parse

from . import content
from . import llm as model  # 인자 이름 llm과 헷갈리지 않게 다른 이름으로 부른다
from .director import Session, save_result
from .fake_llm import fake_llm

WEB_DIR = pathlib.Path(__file__).resolve().parent / "web"
MAX_BODY = 10 * 1024         # 요청 본문 한도 (바이트)
DRAIN_LIMIT = 1024 * 1024    # 한도를 넘긴 본문도 이만큼까지는 읽어서 버린다

# 고르기 화면에 놓는 순서. 여기에 없는 캐릭터는 뒤에 id 순서로 붙는다
CHARACTER_ORDER = ("astra", "gemma", "sora", "nova", "mistral", "haiku")

JSON_TYPE = "application/json; charset=utf-8"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": JSON_TYPE,
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
}

_SESSION_PATH = re.compile(r"/api/session/([^/]+)/(reply|finish|result)")
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


class _ApiError(Exception):
    """요청을 거절할 때 던진다. 본문은 {"error": message}가 된다."""

    def __init__(self, status, message, headers=()):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = tuple(headers)


def _json_response(status, payload, headers=()):
    """(상태 코드, Content-Type, 본문 바이트, 덧붙일 헤더). 한글은 그대로 내보낸다."""
    # 반쪽만 남은 이모지처럼 UTF-8로 못 바꾸는 글자는 물음표로 바꾼다
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8", errors="replace")
    return status, JSON_TYPE, body, tuple(headers)


def _first_sentence(text):
    """글의 첫 문장. 문장 부호가 없으면 글 전체."""
    text = text.strip()
    end = _SENTENCE_END.search(text)
    return text[:end.end()] if end else text


def _card(character):
    """화면에 보여 줄 캐릭터 소개. 지시문에 쓰는 나머지 설정은 내보내지 않는다."""
    return {
        "id": character["id"],
        "name": character["name"],
        "attribute": character["attribute"],
        "motif": character["motif"]["name"],
        "color": character["color"],
    }


def _ordered_character_ids():
    ids = content.list_character_ids()
    known = [char_id for char_id in CHARACTER_ORDER if char_id in ids]
    return known + [char_id for char_id in ids if char_id not in CHARACTER_ORDER]


class _Entry:
    """보관 중인 판 하나."""

    def __init__(self, session):
        self.session = session
        self.lock = threading.Lock()        # 같은 판의 요청이 겹치면 차례로 처리한다
        self.last_seen = time.monotonic()   # 마지막 요청이 온 때
        self.finished = None                # finish가 끝나면 {"ending": ..., "result": ...}
        self.last_reply = None              # (보낸 글, 턴 번호, 돌려준 턴). 같은 답을 다시 보냈을 때 쓴다


class _App:
    """판 보관과 API가 하는 일. HTTP는 모른다. 거절할 때는 _ApiError를 던진다."""

    def __init__(self, *, llm, results_dir, web_dir, session_ttl):
        self.llm = llm
        self.results_dir = results_dir
        self.web_root = pathlib.Path(web_dir if web_dir is not None else WEB_DIR).resolve()
        self.session_ttl = session_ttl
        self.after_model_call = None   # 모델을 부른 요청이 끝날 때마다 부를 함수
        self._lock = threading.Lock()  # _entries를 읽고 고칠 때 잡는다
        self._entries = {}             # 판 id -> _Entry

    # ---- API ----

    def characters(self):
        cards = []
        for char_id in _ordered_character_ids():
            character = content.load_character(char_id)
            # note: 고르기 화면 카드에 덧붙이는 안내 한 줄(하이쿠: 속마음이 가려진다). 없으면 빈 문자열
            cards.append({**_card(character), "intro": _first_sentence(character["attitude"]),
                          "note": str(character.get("card_note") or "")})
        return cards

    def create(self, body):
        """새 판을 만들고 등장까지 돌린다."""
        char_id = body.get("character")
        if not isinstance(char_id, str):
            raise _ApiError(400, "character에 캐릭터 id를 문자열로 적어 주세요.")
        if char_id not in content.list_character_ids():
            raise _ApiError(404, "모르는 캐릭터입니다.")
        # llm을 안 받았으면 인자를 아예 넘기지 않아서 엔진 기본값(실제 모델)을 쓴다
        session = Session(char_id) if self.llm is None else Session(char_id, llm=self.llm)
        turn = session.start()  # 모델을 기다리는 동안에는 어떤 잠금도 잡지 않는다
        self._report_model_call()
        entry = _Entry(session)
        with self._lock:
            self._drop_stale()
            session_id = secrets.token_urlsafe(8)
            while session_id in self._entries:
                session_id = secrets.token_urlsafe(8)
            self._entries[session_id] = entry
        return {"session_id": session_id, "character": _card(session.character), "turn": turn}

    def reply(self, session_id, body):
        text = body.get("text")
        if not isinstance(text, str):
            raise _ApiError(400, "text에 보낼 글을 문자열로 적어 주세요.")
        expected = body.get("turn")
        entry = self._find(session_id)
        with entry.lock:
            # 화면이 시간 초과로 답을 못 받고 "다시 시도"로 같은 답을 또 보낸 경우: 이미 처리했으면
            # 그때의 턴을 그대로 돌려준다. 같은 말이 두 번 들어가 턴이 하나 더 지나가지 않게 한다.
            # 턴 번호(turn)를 보내는 화면(Ren'Py)에만 해당한다. 브라우저 화면은 보내지 않는다
            last = entry.last_reply
            if (last is not None and isinstance(expected, int) and not isinstance(expected, bool)
                    and (last[0], last[1]) == (text, expected)):
                return last[2]
            try:
                turn = entry.session.reply(text)
            except ValueError:
                raise _ApiError(400, "빈 글은 보낼 수 없습니다.") from None
            except RuntimeError:
                raise _ApiError(409, "이 판은 더 답을 받지 않습니다. 엔딩을 보러 가세요.") from None
            entry.last_reply = (text, turn["turn"], turn)
        self._report_model_call()
        return turn

    def finish(self, session_id):
        """엔딩과 결과. 결과 파일은 처음 한 번만 쓴다."""
        entry = self._find(session_id)
        with entry.lock:
            if entry.finished is None:
                ending = entry.session.finish()
                result = entry.session.result()
                save_result(result, self.results_dir)
                # 저장까지 끝난 뒤에 적어 둔다. 저장이 실패하면 다음 요청이 다시 시도한다
                entry.finished = {"ending": ending, "result": result}
                self._report_model_call()
            return entry.finished

    def result(self, session_id):
        entry = self._find(session_id)
        with entry.lock:
            try:
                return entry.session.result()
            except RuntimeError:
                raise _ApiError(404, "아직 끝나지 않은 판입니다.") from None

    def status(self):
        with self._lock:
            count = len(self._entries)
        return {
            "calls": model.stats["calls"],
            "failures": model.stats["failures"],
            "last_provider": model.stats["last_provider"],
            "sessions": count,
        }

    # ---- 정적 파일 ----

    def static_file(self, url_path):
        """주소 경로가 가리키는 web 폴더 안의 파일. 없거나 폴더 밖이면 None."""
        if url_path == "/":
            relative = "index.html"
        else:
            relative = urllib.parse.unquote(url_path).lstrip("/")  # %2e%2e도 여기서 풀린다
        if "\\" in relative or "\x00" in relative:
            return None
        try:
            # 실제 위치를 끝까지 따라가 본 다음 web 폴더 안인지 확인한다
            target = (self.web_root / relative).resolve()
            if target.is_relative_to(self.web_root) and target.is_file():
                return target
        except (OSError, ValueError, RuntimeError):
            pass
        return None

    # ---- 안에서만 쓰는 것 ----

    def _find(self, session_id):
        with self._lock:
            entry = self._entries.get(session_id)
            if entry is not None:
                entry.last_seen = time.monotonic()
        if entry is None:
            raise _ApiError(404, "모르는 판입니다. 처음부터 다시 시작해 주세요.")
        return entry

    def _drop_stale(self):
        """마지막 요청으로부터 session_ttl초가 지난 판을 지운다. _lock을 잡고 부른다."""
        now = time.monotonic()
        stale = [sid for sid, entry in self._entries.items()
                 if now - entry.last_seen >= self.session_ttl]
        for sid in stale:
            del self._entries[sid]

    def _report_model_call(self):
        hook = self.after_model_call
        if hook is None:
            return
        try:
            hook()
        except Exception:
            traceback.print_exc()  # 상태 줄을 찍다 난 오류로 판을 망치지 않는다


class _Handler(http.server.BaseHTTPRequestHandler):
    """HTTP 요청 하나를 읽어 _App에 넘기고 답을 써 보낸다."""

    def do_GET(self):
        self._dispatch()

    # 틀린 메서드도 같은 길로 보내서 405나 404를 JSON으로 답한다
    do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = do_GET

    def log_message(self, format, *args):
        """요청마다 한 줄씩 찍는 기본 로그를 끈다."""

    def send_error(self, code, message=None, explain=None):
        """http.server가 스스로 내는 오류(깨진 요청 줄 등)도 같은 모양으로 낸다."""
        text = {
            400: "요청 형식이 올바르지 않습니다.",
            501: "지원하지 않는 요청 방식입니다.",
        }.get(int(code), "요청을 처리할 수 없습니다.")
        self.close_connection = True
        self._send(*_json_response(int(code), {"error": text}, [("Connection", "close")]))

    def _dispatch(self):
        try:
            self._load_body()
        except OSError:  # 본문을 보내다 만 연결. 답할 곳이 없다
            self.close_connection = True
            return
        try:
            response = self._respond()
        except _ApiError as error:
            response = _json_response(error.status, {"error": error.message}, error.headers)
        except Exception:
            traceback.print_exc()  # 자세한 내용은 터미널에만 남긴다
            response = _json_response(
                500, {"error": "서버 안에서 문제가 생겼습니다. 서버를 켠 터미널을 확인하세요."})
        self._send(*response)

    def _respond(self):
        """요청에 맞는 답을 만든다. (상태 코드, Content-Type, 본문, 헤더)"""
        app = self.server.app
        path = self.path.split("?", 1)[0].split("#", 1)[0]  # 쿼리 문자열은 보지 않는다
        if path == "/api" or path.startswith("/api/"):
            allowed, action = self._api_route(app, path)
            self._require_method(allowed)
            return _json_response(*action())
        file = app.static_file(path)
        if file is None:
            raise _ApiError(404, "없는 주소입니다.")
        self._require_method("GET")
        content_type = CONTENT_TYPES.get(file.suffix.lower(), "application/octet-stream")
        return 200, content_type, file.read_bytes(), ()

    def _api_route(self, app, path):
        """(받는 메서드, 부르면 (상태 코드, 내용)을 돌려주는 함수)"""
        if path == "/api/characters":
            return "GET", lambda: (200, app.characters())
        if path == "/api/status":
            return "GET", lambda: (200, app.status())
        if path == "/api/session":
            return "POST", lambda: (201, app.create(self._json_body()))
        match = _SESSION_PATH.fullmatch(path)
        if match is None:
            raise _ApiError(404, "없는 주소입니다.")
        session_id, action = match.groups()
        if action == "reply":
            return "POST", lambda: (200, app.reply(session_id, self._json_body()))
        if action == "finish":
            return "POST", lambda: self._finish(app, session_id)
        return "GET", lambda: (200, app.result(session_id))

    def _finish(self, app, session_id):
        self._check_body()  # 본문은 쓰지 않지만 크기 한도는 똑같이 지킨다
        return 200, app.finish(session_id)

    def _require_method(self, allowed):
        if self.command != allowed:
            raise _ApiError(405, f"이 주소는 {allowed} 요청만 받습니다.", [("Allow", allowed)])

    def _load_body(self):
        """본문을 미리 다 읽어 둔다.

        거절할 요청이라도 본문을 읽지 않고 연결을 닫으면 브라우저가 답을 못 받는 수가 있다.
        """
        self._body = b""
        self._body_problem = None
        declared = self.headers.get("Content-Length")
        if declared is None:
            return
        try:
            length = int(declared)
        except ValueError:
            length = -1
        if length < 0:
            self._body_problem = "요청의 Content-Length가 올바르지 않습니다."
        elif length > MAX_BODY:
            self._body_problem = "요청 본문이 너무 큽니다. 10KB까지만 받습니다."
            left = min(length, DRAIN_LIMIT)
            while left > 0:
                chunk = self.rfile.read(min(left, 65536))
                if not chunk:
                    break
                left -= len(chunk)
        else:
            self._body = self.rfile.read(length)

    def _check_body(self):
        if self._body_problem:
            raise _ApiError(400, self._body_problem)

    def _json_body(self):
        """본문을 dict로 읽는다."""
        self._check_body()
        try:
            data = json.loads(self._body.decode("utf-8"))
        except (ValueError, RecursionError):  # UTF-8이 아닌 본문도 ValueError다
            raise _ApiError(400, "요청 본문이 JSON이 아닙니다.") from None
        if not isinstance(data, dict):
            raise _ApiError(400, "요청 본문은 JSON 객체여야 합니다.")
        return data

    def _send(self, status, content_type, body, headers=()):
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
        except OSError:  # 브라우저가 답을 기다리지 않고 연결을 끊었다
            self.close_connection = True


class _Server(http.server.ThreadingHTTPServer):
    request_queue_size = 32  # 탭 여러 개가 한꺼번에 파일을 받아 가도 밀리지 않게

    def __init__(self, address, app):
        super().__init__(address, _Handler)
        self.app = app


def make_server(host="127.0.0.1", port=8000, *, llm=None, results_dir="results",
                web_dir=None, session_ttl=900) -> http.server.ThreadingHTTPServer:
    """서버를 만들어 돌려준다. 돌리지는 않는다. serve_forever()는 부르는 쪽이 한다.

    llm을 안 주면 엔진 기본값(실제 모델)을 쓴다. web_dir 기본값은 sogaeting/web 이다.
    """
    app = _App(llm=llm, results_dir=results_dir, web_dir=web_dir, session_ttl=session_ttl)
    return _Server((host, port), app)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m sogaeting.server", description="소개팅 화면을 띄우는 로컬 서버.")
    parser.add_argument("--fake", action="store_true", help="실제 모델 대신 가짜 모델을 쓴다")
    parser.add_argument("--host", default="127.0.0.1", help="서버가 들을 주소 (기본 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="포트 번호 (기본 8000)")
    parser.add_argument("--results", default="results", metavar="DIR",
                        help="결과 파일을 쓸 폴더 (기본 results)")
    args = parser.parse_args(argv)

    model.load_dotenv()
    try:
        server = make_server(args.host, args.port,
                             llm=fake_llm if args.fake else None, results_dir=args.results)
    except OSError as error:
        print(f"서버를 켤 수 없습니다 ({args.host}:{args.port}): {error}")
        print("다른 프로그램이 이 포트를 쓰고 있으면 --port로 다른 번호를 고르세요.")
        return 1
    server.app.after_model_call = lambda: print(model.status_line(), flush=True)

    host, port = server.server_address[:2]
    if host in ("", "0.0.0.0"):
        host = "localhost"
    print(f"소개팅 서버를 켰습니다: http://{host}:{port}/")
    if args.fake:
        print("가짜 모델로 진행합니다.")
    else:
        counts = model.key_counts()
        print("읽은 키: " + ", ".join(f"{name} {n}개" for name, n in counts.items()))
        for name in model.dotenv_ignored:
            print(f"{name} 가 이 컴퓨터의 환경변수에 이미 있어서 .env 의 값을 쓰지 않았습니다.")
        if not any(counts.values()):
            print("키를 하나도 읽지 못했습니다. 모든 대답이 괄호 속 행동(대체 대사)으로 나갑니다.")
            print("레포 맨 위의 .env에 GEMINI_API_KEY=키 를 적었는지 보세요. 점검: python -m sogaeting.check")
    print("끄려면 Ctrl-C를 누르세요.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()  # 조용히 끝낸다
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

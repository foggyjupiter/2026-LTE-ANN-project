"""화면 시험 sg_errors 용 중계 서버. 개발용이다. 표준 라이브러리만 쓴다.

    python3 -m sogaeting.server --fake --port 8120
    python3 renpy/dev/error_proxy.py            # 8121에서 받아 8120에 넘긴다
    RENPY_SDK=... renpy/dev/rtest.sh sg_errors 8121

첫 번째 /reply 는 서버가 처리하게 두고 화면에는 500을 돌려준다. 답이 오는 길에 사라진 경우를
흉내 낸다. 화면이 "다시 시도"로 같은 답을 또 보내면 서버는 같은 턴을 돌려줘야 한다(턴이 1이어야 한다).
"""
import http.server, urllib.request, urllib.error
state = {"lost": False}
class H(http.server.BaseHTTPRequestHandler):
    def _go(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        req = urllib.request.Request("http://127.0.0.1:8120" + self.path, data=body, method=self.command,
                                     headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                code, data = r.status, r.read()
        except urllib.error.HTTPError as e:
            code, data = e.code, e.read()
        if self.path.endswith("/reply") and not state["lost"]:
            state["lost"] = True
            code, data = 500, b'{"error": "lost on the way"}'
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    do_GET = do_POST = _go
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", 8121), H).serve_forever()

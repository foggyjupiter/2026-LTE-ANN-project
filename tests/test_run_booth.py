"""run_booth.py 시험. 실제 SDK와 인터넷 없이 임시 폴더와 이 PC 안의 소켓만 쓴다."""

import argparse
import ast
import contextlib
import http.server
import importlib.util
import io
import os
import pathlib
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("run_booth", ROOT / "run_booth.py")
run_booth = importlib.util.module_from_spec(_SPEC)
sys.modules["run_booth"] = run_booth
_SPEC.loader.exec_module(run_booth)

TILDE = chr(126)       # 글에 쓰면 안 되는 두 글자. 이 파일에도 직접 적지 않는다
EM_DASH = chr(0x2014)


def has_hangul(text):
    return any("가" <= ch <= "힣" for ch in text)


def make_sdk(folder, launchers=("renpy.sh", "renpy.exe")):
    """SDK 흉내만 내는 폴더."""
    folder.mkdir(parents=True)
    (folder / "renpy.py").write_text("", encoding="utf-8")
    for name in launchers:
        (folder / name).write_text("", encoding="utf-8")
    return folder


class TempCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name).resolve()


class FindSdkTest(TempCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "work" / "repo"
        self.home = self.tmp / "home"
        self.root.mkdir(parents=True)
        self.home.mkdir()

    def find(self, env=None, platform="linux"):
        return run_booth.find_sdk(env=env or {}, root=self.root, home=self.home, platform=platform)

    def test_env_variable_wins(self):
        make_sdk(self.root / "renpy-sdk")
        chosen = make_sdk(self.tmp / "elsewhere" / "my sdk")
        self.assertEqual(self.find({"RENPY_SDK": str(chosen)}), chosen)

    def test_wrong_env_variable_is_not_replaced_silently(self):
        make_sdk(self.root / "renpy-sdk")
        self.assertIsNone(self.find({"RENPY_SDK": str(self.tmp / "nope")}))

    def test_common_places(self):
        places = [
            self.root / "renpy-sdk",
            self.root / "renpy-8.5.3-sdk",
            self.root.parent / "renpy-8.5.3-sdk",
            self.root.parent / "sdk" / "renpy-8.5.3-sdk",
            self.home / "renpy-sdk",
            self.home / "Downloads" / "renpy-8.5.3-sdk",
            self.home / "Desktop" / "renpy-8.6.0-sdk",
        ]
        for place in places:
            with self.subTest(place=place.relative_to(self.tmp).as_posix()):
                with tempfile.TemporaryDirectory(dir=self.tmp) as scratch:
                    self.root = pathlib.Path(scratch) / "work" / "repo"
                    self.home = pathlib.Path(scratch) / "home"
                    self.root.mkdir(parents=True)
                    self.home.mkdir()
                    target = pathlib.Path(scratch) / place.relative_to(self.tmp)
                    make_sdk(target)
                    self.assertEqual(self.find(), target)

    def test_repo_is_searched_before_home(self):
        make_sdk(self.home / "renpy-sdk")
        near = make_sdk(self.root.parent / "renpy-8.5.3-sdk")
        self.assertEqual(self.find(), near)

    def test_prefers_the_project_version_then_the_newest(self):
        make_sdk(self.root / "renpy-8.4.1-sdk")
        newest = make_sdk(self.root / "renpy-8.10.0-sdk")
        self.assertEqual(self.find(), newest)  # 숫자로 견준다. 글자로 견주면 8.4.1이 앞선다
        exact = make_sdk(self.root / "renpy-8.5.3-sdk")
        self.assertEqual(self.find(), exact)

    def test_launcher_depends_on_platform(self):
        make_sdk(self.root / "renpy-sdk", launchers=("renpy.sh",))
        self.assertIsNotNone(self.find(platform="linux"))
        self.assertIsNotNone(self.find(platform="darwin"))
        self.assertIsNone(self.find(platform="win32"))
        self.assertEqual(run_booth.launcher_name("win32"), "renpy.exe")
        self.assertEqual(run_booth.launcher_name("linux"), "renpy.sh")
        self.assertEqual(run_booth.launcher_name("darwin"), "renpy.sh")

    def test_folder_doubled_by_unzipping(self):
        inner = make_sdk(self.root / "renpy-8.5.3-sdk" / "renpy-8.5.3-sdk")
        self.assertEqual(self.find(), inner)
        self.assertEqual(self.find({"RENPY_SDK": str(self.root / "renpy-8.5.3-sdk")}), inner)

    def test_folder_without_launcher_is_not_an_sdk(self):
        (self.root / "renpy-sdk").mkdir()
        (self.root / "renpy-sdk" / "renpy.py").write_text("", encoding="utf-8")
        (self.root / "renpy-8.5.3-sdk.zip").write_text("", encoding="utf-8")
        self.assertIsNone(self.find())

    def test_help_says_where_to_get_it_and_where_to_put_it(self):
        text = run_booth.sdk_help(env={}, root=self.root, platform="win32")
        self.assertIn(run_booth.SDK_PAGE, text)
        self.assertIn(str(self.root / "renpy-8.5.3-sdk"), text)
        self.assertIn(str(self.root.parent / "renpy-8.5.3-sdk"), text)
        self.assertIn("RENPY_SDK", text)
        self.assertTrue(has_hangul(text))
        self.assertNotIn(TILDE, text)
        self.assertNotIn(EM_DASH, text)

    def test_help_points_at_a_wrong_env_variable(self):
        text = run_booth.sdk_help(env={"RENPY_SDK": "/없는/곳"}, root=self.root, platform="win32")
        self.assertIn("/없는/곳", text)
        self.assertIn("renpy.exe", text)


class PortTest(unittest.TestCase):
    def listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        return sock, sock.getsockname()[1]

    def test_takes_the_first_free_port(self):
        busy = {8103, 8104}
        port = run_booth.pick_port(first=8103, tries=10, can_bind=lambda port, host: port not in busy)
        self.assertEqual(port, 8105)

    def test_asks_the_system_when_all_are_busy(self):
        port = run_booth.pick_port(first=8103, tries=5, can_bind=lambda port, host: False)
        self.assertNotIn(port, range(8103, 8108))
        self.assertTrue(1 <= port <= 65535)

    def test_a_port_in_use_is_noticed(self):
        sock, port = self.listener()
        self.assertTrue(run_booth.is_listening(port))
        self.assertFalse(run_booth.can_bind(port))
        self.assertNotEqual(run_booth.pick_port(first=port, tries=3), port)
        sock.close()
        self.assertFalse(run_booth.is_listening(port))

    def test_port_number(self):
        self.assertEqual(run_booth.port_number("8103"), 8103)
        for bad in ("0", "65536", "-1", "abc", ""):
            with self.subTest(bad=bad), self.assertRaises(argparse.ArgumentTypeError) as caught:
                run_booth.port_number(bad)
            self.assertTrue(has_hangul(str(caught.exception)))


class SyncArtTest(TempCase):
    def setUp(self):
        super().setUp()
        self.art = self.tmp / "art"
        self.images = self.tmp / "renpy" / "game" / "images"

    def put(self, relative, data="그림"):
        path = self.art / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
        return path

    def sync(self):
        return run_booth.sync_art(self.art, self.images)

    def copied_files(self):
        return sorted(p.relative_to(self.images).as_posix() for p in self.images.rglob("*") if p.is_file())

    def test_copies_sprites_and_backgrounds_only(self):
        self.put("sprites/giulhee/neutral.png")
        self.put("sprites/haru/SMILE.PNG")
        self.put("bg/rooftop.jpg")
        self.put("raw/giulhee/neutral.png")
        self.put("raw/bg/rooftop.jpg")
        self.put("preview.png")
        self.put("manifest.json")
        wanted = ["bg/rooftop.jpg", "sprites/giulhee/neutral.png", "sprites/haru/SMILE.PNG"]
        self.assertEqual(sorted(self.sync()), wanted)
        self.assertEqual(self.copied_files(), wanted)
        self.assertEqual((self.images / "bg" / "rooftop.jpg").read_text(encoding="utf-8"), "그림")

    def test_backgrounds_without_sprites(self):
        """지금 실제 art 폴더의 모양: 배경만 있고 캐릭터 그림은 아직 없다."""
        self.put("bg/library.jpg")
        self.put("raw/bg/library.jpg")
        self.put("preview.png")
        self.assertEqual(self.sync(), ["bg/library.jpg"])
        self.assertEqual(self.copied_files(), ["bg/library.jpg"])

    def test_second_run_copies_nothing(self):
        self.put("bg/rooftop.jpg")
        self.sync()
        target = self.images / "bg" / "rooftop.jpg"
        before = target.stat().st_mtime_ns
        self.assertEqual(self.sync(), [])
        self.assertEqual(target.stat().st_mtime_ns, before)

    def test_changed_picture_is_copied_again(self):
        source = self.put("bg/rooftop.jpg", "하나")
        self.put("bg/library.jpg", "그대로")
        self.sync()
        source.write_text("둘둘둘", encoding="utf-8")            # 크기가 달라졌다
        self.assertEqual(self.sync(), ["bg/rooftop.jpg"])
        self.assertEqual((self.images / "bg" / "rooftop.jpg").read_text(encoding="utf-8"), "둘둘둘")
        source.write_text("셋셋셋", encoding="utf-8")            # 크기는 같고 시각만 다르다
        stamp = source.stat().st_mtime + 60
        os.utime(source, (stamp, stamp))
        self.assertEqual(self.sync(), ["bg/rooftop.jpg"])
        self.assertEqual((self.images / "bg" / "rooftop.jpg").read_text(encoding="utf-8"), "셋셋셋")

    def test_other_files_are_left_alone(self):
        self.put("bg/rooftop.jpg")
        self.put("bg/notes.txt")
        self.put("bg/.DS_Store")
        self.put("sprites/giulhee/neutral.png.part")
        mine = self.images / "bg" / "hand_made.jpg"
        mine.parent.mkdir(parents=True)
        mine.write_text("게임 폴더에만 있는 그림", encoding="utf-8")
        self.assertEqual(self.sync(), ["bg/rooftop.jpg"])
        self.assertEqual(self.copied_files(), ["bg/hand_made.jpg", "bg/rooftop.jpg"])

    def test_no_art_folder(self):
        self.assertEqual(self.sync(), [])
        self.assertFalse(self.images.exists())


class CommandTest(unittest.TestCase):
    def test_server_command(self):
        command = run_booth.server_command(8103)
        self.assertEqual(command[:3], [sys.executable, "-m", "sogaeting.server"])
        self.assertEqual(command[command.index("--port") + 1], "8103")
        self.assertNotIn("--fake", command)
        self.assertIn("--fake", run_booth.server_command(8103, fake=True))

    def test_game_command(self):
        sdk, project = pathlib.Path("sdk 폴더"), pathlib.Path("레포") / "renpy"
        self.assertEqual(run_booth.game_command(sdk, project, "win32"),
                         [str(sdk / "renpy.exe"), str(project)])
        self.assertEqual(run_booth.game_command(sdk, project, "linux"),
                         [str(sdk / "renpy.sh"), str(project)])
        self.assertEqual(run_booth.game_command(sdk, project, "darwin"),
                         [str(sdk / "renpy.sh"), str(project)])

    def test_game_env(self):
        base = {"PATH": "/bin", "http_proxy": "http://proxy:1", "HTTP_PROXY": "http://proxy:1",
                "ALL_PROXY": "http://proxy:1", "NO_PROXY": "example.com",
                "https_proxy": "http://proxy:2", "RENPY_SEARCHPATH": "/extra"}
        original = dict(base)
        overlay = pathlib.Path("dev") / "booth"
        env = run_booth.game_env(base, "http://127.0.0.1:8103", overlay=overlay)
        self.assertEqual(base, original)
        self.assertEqual(env["SOGAETING_URL"], "http://127.0.0.1:8103")
        self.assertEqual(env["SOGAETING_WINDOW"], "fullscreen")
        self.assertEqual(env["RENPY_SEARCHPATH"], "/extra::" + str(overlay))
        self.assertEqual(env["PATH"], "/bin")
        self.assertEqual(env["https_proxy"], "http://proxy:2")
        # 게임이 로컬 서버로 가는 길에 프록시가 끼지 않는다
        self.assertEqual({name: value for name, value in env.items() if name.lower() == "no_proxy"},
                         {"no_proxy": "127.0.0.1,localhost"})
        for name in ("http_proxy", "HTTP_PROXY", "ALL_PROXY"):
            self.assertNotIn(name, env)

    def test_game_env_windowed_and_no_repeat(self):
        overlay = pathlib.Path("dev") / "booth"
        env = run_booth.game_env({"RENPY_SEARCHPATH": str(overlay)}, "http://127.0.0.1:1",
                                 windowed=True, overlay=overlay)
        self.assertEqual(env["SOGAETING_WINDOW"], "windowed")
        self.assertEqual(env["RENPY_SEARCHPATH"], str(overlay))

    def test_overlay_script_reads_what_the_launcher_sends(self):
        script = (run_booth.OVERLAY / "sg_booth.rpy").read_text(encoding="utf-8")
        for word in ("SOGAETING_WINDOW", "fullscreen", "windowed"):
            self.assertIn(word, script)


class FakeProcess:
    """subprocess.Popen 흉내. script 에 적힌 대로 wait() 가 답한다."""

    def __init__(self, script=(), returncode=None):
        self.script = list(script)
        self.returncode = returncode
        self.terminated = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is not None:
            return self.returncode
        step = self.script.pop(0) if self.script else subprocess.TimeoutExpired("fake", timeout)
        if isinstance(step, BaseException):
            raise step
        self.returncode = step
        return step

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.returncode = -9


class _StatusHandler(http.server.BaseHTTPRequestHandler):
    body = b'{"sessions": 0}'

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format, *args):
        pass


class WaitForServerTest(unittest.TestCase):
    def serve(self, body):
        handler = type("Handler", (_StatusHandler,), {"body": body})
        server = http.server.HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_ready(self):
        url = self.serve(b'{"sessions": 0}')
        # PC에 프록시가 잡혀 있어도 거치지 않는다
        with mock.patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9"}):
            self.assertEqual(run_booth.wait_for_server(url, FakeProcess(), timeout=5), "ready")

    def test_server_that_died(self):
        url = self.serve(b'{"sessions": 0}')
        self.assertEqual(run_booth.wait_for_server(url, FakeProcess(returncode=1), timeout=5), "exited")

    def test_something_else_on_the_port(self):
        url = self.serve(b"<html>hello</html>")
        self.assertEqual(run_booth.wait_for_server(url, FakeProcess(), timeout=0.3, interval=0.05),
                         "timeout")

    def test_nothing_on_the_port(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        state = run_booth.wait_for_server(f"http://127.0.0.1:{port}", FakeProcess(),
                                          timeout=0.3, interval=0.05)
        self.assertEqual(state, "timeout")


class RunTest(unittest.TestCase):
    """서버와 게임을 켜고 끄는 차례. 진짜 프로세스 대신 FakeProcess 를 쓴다."""

    def run_with(self, processes, state="ready"):
        out = io.StringIO()
        with mock.patch.object(run_booth.subprocess, "Popen", side_effect=processes) as popen, \
                mock.patch.object(run_booth, "wait_for_server", return_value=state), \
                contextlib.redirect_stdout(out):
            code = run_booth.run(pathlib.Path("sdk"), 8103, fake=True)
        return code, out.getvalue(), popen

    def test_server_stops_when_the_game_exits(self):
        server = FakeProcess()
        game = FakeProcess(script=[subprocess.TimeoutExpired("game", 0.5), 0])
        code, out, popen = self.run_with([server, game])
        self.assertEqual(code, 0)
        self.assertTrue(server.terminated)
        self.assertFalse(game.terminated)
        server_call, game_call = popen.call_args_list
        self.assertEqual(server_call.args[0], run_booth.server_command(8103, fake=True))
        self.assertEqual(server_call.kwargs["cwd"], str(run_booth.ROOT))
        self.assertEqual(game_call.kwargs["env"]["SOGAETING_URL"], "http://127.0.0.1:8103")
        self.assertTrue(has_hangul(out))

    def test_interrupt_stops_both(self):
        server, game = FakeProcess(), FakeProcess(script=[KeyboardInterrupt()])
        code, _, _ = self.run_with([server, game])
        self.assertEqual(code, 130)
        self.assertTrue(server.terminated)
        self.assertTrue(game.terminated)

    def test_server_that_does_not_start(self):
        for state in ("exited", "timeout"):
            with self.subTest(state=state):
                server = FakeProcess()
                code, out, popen = self.run_with([server], state=state)
                self.assertEqual(code, 1)
                self.assertEqual(popen.call_count, 1)  # 게임은 띄우지 않는다
                self.assertTrue(server.terminated)
                self.assertTrue(has_hangul(out))

    def test_game_that_cannot_start(self):
        server = FakeProcess()
        code, out, _ = self.run_with([server, OSError("실행할 수 없음")])
        self.assertEqual(code, 1)
        self.assertTrue(server.terminated)
        self.assertIn("실행할 수 없음", out)

    def test_signal_handlers_are_put_back(self):
        before = signal.getsignal(signal.SIGINT)
        self.run_with([FakeProcess(), FakeProcess(script=[0])])
        self.assertIs(signal.getsignal(signal.SIGINT), before)


class StopTest(unittest.TestCase):
    def test_stop_ends_a_process(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        run_booth.stop(process)
        self.assertIsNotNone(process.poll())

    @unittest.skipIf(os.name == "nt", "윈도우에는 SIGTERM을 무시하는 프로세스가 없다")
    def test_stop_kills_a_process_that_will_not_quit(self):
        code = ("import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "print('ready', flush=True); time.sleep(60)")
        process = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE)
        self.addCleanup(process.stdout.close)
        process.stdout.readline()  # 신호를 무시하기 시작할 때까지 기다린다
        run_booth.stop(process, grace=0.3)
        self.assertEqual(process.returncode, -signal.SIGKILL)

    def test_stop_accepts_nothing_and_finished(self):
        run_booth.stop(None)
        finished = FakeProcess(returncode=0)
        run_booth.stop(finished)
        self.assertFalse(finished.terminated)


class MainTest(TempCase):
    def run_main(self, argv, sdk):
        out = io.StringIO()
        with mock.patch.object(run_booth, "find_sdk", return_value=sdk), \
                mock.patch.object(run_booth, "sync_art", return_value=[]), \
                mock.patch.object(run_booth.subprocess, "Popen") as popen, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = run_booth.main(argv)
        return code, out.getvalue(), popen

    def test_no_sdk_explains_and_starts_nothing(self):
        code, out, popen = self.run_main(["--fake"], sdk=None)
        self.assertEqual(code, 1)
        self.assertIn(run_booth.SDK_PAGE, out)
        self.assertTrue(has_hangul(out))
        popen.assert_not_called()

    def test_busy_port_explains_and_starts_nothing(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen()
            port = sock.getsockname()[1]
            code, out, popen = self.run_main(["--port", str(port)], sdk=self.tmp)
        self.assertEqual(code, 1)
        self.assertIn(str(port), out)
        self.assertTrue(has_hangul(out))
        popen.assert_not_called()

    def test_bad_port_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_main(["--port", "99999"], sdk=self.tmp)


class SourceTest(unittest.TestCase):
    FILES = ["run_booth.py", "run_booth.bat", "run_booth.sh", "renpy/README.md",
             "renpy/dev/booth/sg_booth.rpy", "tests/test_run_booth.py"]

    def test_no_tilde_or_em_dash(self):
        for name in self.FILES:
            with self.subTest(name=name):
                text = (ROOT / name).read_bytes().decode("utf-8")
                self.assertNotIn(TILDE, text)
                self.assertNotIn(EM_DASH, text)

    def test_batch_file_is_ascii_with_crlf(self):
        """cmd.exe 는 배치 파일을 시스템 코드 페이지(cp949)로 읽는다. 한글을 넣으면 깨질 수 있다."""
        data = (ROOT / "run_booth.bat").read_bytes()
        data.decode("ascii")
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))
        self.assertTrue(data.endswith(b"\r\n"))
        self.assertIn(b"run_booth.py", data)

    def test_shell_script(self):
        data = (ROOT / "run_booth.sh").read_bytes()
        self.assertTrue(data.startswith(b"#!/bin/sh\n"))
        self.assertNotIn(b"\r", data)
        self.assertIn(b"run_booth.py", data)

    def test_launcher_does_not_touch_keys(self):
        source = (ROOT / "run_booth.py").read_text(encoding="utf-8")
        self.assertNotIn("API_KEY", source)
        self.assertNotIn("load_dotenv", source)

    def test_old_python_can_read_the_launcher(self):
        """옛 파이썬으로 켜도 문법 오류 대신 버전 안내가 나오게, 새 문법을 쓰지 않는다."""
        source = (ROOT / "run_booth.py").read_text(encoding="utf-8")
        ast.parse(source, feature_version=(3, 7))


if __name__ == "__main__":
    unittest.main()

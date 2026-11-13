#!/usr/bin/env python3
"""부스 PC에서 소개팅을 한 번에 켠다.

    python run_booth.py [--fake] [--port N] [--windowed]

하는 일:
  1. Ren'Py SDK를 찾는다.
  2. art/ 에 그림이 있으면 renpy/game/images/ 아래로 복사한다(바뀐 것만).
  3. 빈 포트에 서버(sogaeting.server)를 켜고 /api/status 가 답할 때까지 기다린다.
  4. 서버 주소(SOGAETING_URL)를 알려 주며 Ren'Py 게임을 띄운다.
  5. 게임이 꺼지면 서버도 끈다. Ctrl-C를 눌러도 둘 다 끈다.

표준 라이브러리만 쓴다. 키(.env)는 서버가 스스로 읽는다. 이 스크립트는 읽지 않는다.
SDK 설치와 문제 해결은 renpy/README.md 에 있다.
"""
import argparse
import http.client
import json
import os
import pathlib
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
PROJECT = ROOT / "renpy"                    # Ren'Py 프로젝트 폴더
ART = ROOT / "art"                          # tools/make_art.py 가 그림을 만드는 곳
IMAGES = PROJECT / "game" / "images"        # 게임이 그림을 읽는 곳
OVERLAY = PROJECT / "dev" / "booth"         # 이 실행기가 게임에 덧붙이는 설정 (sg_booth.rpy)

HOST = "127.0.0.1"
FIRST_PORT = 8000                           # 포트를 안 정해 주면 여기부터 빈 곳을 찾는다
PORT_TRIES = 20
SERVER_WAIT = 20.0                          # 서버가 답하기를 기다리는 시간 (초)

SDK_VERSION = "8.5.3"
SDK_PAGE = "https://www.renpy.org/release/" + SDK_VERSION

ART_FOLDERS = ("sprites", "bg")             # art/ 에서 이 둘만 복사한다. raw 와 preview 는 뺀다
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


def say(text=""):
    """이 실행기가 하는 말. 서버가 찍는 줄과 구별되게 앞에 표시를 붙인다."""
    try:
        print(f"[부스] {text}" if text else "", flush=True)
    except OSError:
        pass  # 터미널이 먼저 닫혔다. 정리는 계속한다


# ---- Ren'Py SDK 찾기 ----

def launcher_name(platform=None):
    """SDK 안에서 게임을 띄우는 파일 이름. 윈도우는 renpy.exe, 리눅스와 맥은 renpy.sh."""
    platform = sys.platform if platform is None else platform
    return "renpy.exe" if platform.startswith("win") else "renpy.sh"


def sdk_at(folder, platform=None):
    """folder 가 SDK 폴더면 그 경로. 아니면 None.

    압축을 풀다가 같은 이름의 폴더가 한 겹 더 생겼으면 안쪽 폴더를 돌려준다.
    """
    folder = pathlib.Path(folder)
    launcher = launcher_name(platform)
    try:
        inner = sorted(folder.glob("renpy-*-sdk"), key=_version_rank, reverse=True)
    except OSError:
        inner = []
    for candidate in [folder] + inner + [folder / "renpy-sdk"]:
        if os.path.isfile(candidate / launcher) and os.path.isfile(candidate / "renpy.py"):
            return candidate
    return None


def _version_rank(folder):
    """정렬 기준. 이 게임을 만든 판(8.5.3)이 맨 앞, 그다음은 새 판이 앞."""
    numbers = [int(number) for number in re.findall(r"\d+", folder.name)]
    return (folder.name == f"renpy-{SDK_VERSION}-sdk", numbers)


def sdk_places(root=ROOT, home=None):
    """SDK를 풀어 두었을 만한 폴더. 앞에 있는 곳부터 본다."""
    root = pathlib.Path(root)
    home = pathlib.Path.home() if home is None else pathlib.Path(home)
    return [root, root.parent, root.parent / "sdk",
            home, home / "sdk", home / "Downloads", home / "Desktop", home / "Documents"]


def find_sdk(env=None, root=ROOT, home=None, platform=None):
    """Ren'Py SDK 폴더를 찾는다. 없으면 None.

    환경변수 RENPY_SDK 가 있으면 그곳만 본다. 없으면 sdk_places() 의 폴더마다
    renpy-sdk, renpy-8.*-sdk 를 찾는다.
    """
    env = os.environ if env is None else env
    chosen = env.get("RENPY_SDK", "").strip().strip('"')
    if chosen:
        return sdk_at(chosen, platform)
    for place in sdk_places(root, home):
        try:
            versions = sorted(place.glob("renpy-8.*-sdk"), key=_version_rank, reverse=True)
        except OSError:
            versions = []
        for candidate in [place / "renpy-sdk"] + versions:
            found = sdk_at(candidate, platform)
            if found is not None:
                return found
    return None


def sdk_help(env=None, root=ROOT, platform=None):
    """SDK를 못 찾았을 때 보여 줄 안내."""
    env = os.environ if env is None else env
    root = pathlib.Path(root)
    launcher = launcher_name(platform)
    folder = f"renpy-{SDK_VERSION}-sdk"
    chosen = env.get("RENPY_SDK", "").strip().strip('"')
    if chosen:
        head = [
            "환경변수 RENPY_SDK 가 가리키는 폴더에 Ren'Py SDK가 없습니다.",
            f"  RENPY_SDK = {chosen}",
            f"그 폴더 안에 {launcher} 가 있어야 합니다. 경로를 고치거나 RENPY_SDK 를 지우고,",
            "아래처럼 SDK를 두면 알아서 찾습니다.",
        ]
    else:
        head = ["Ren'Py SDK를 찾지 못했습니다. 한 번만 받아 두면 됩니다."]
    return "\n".join(head + [
        "",
        f"1. {SDK_PAGE} 에서 SDK를 받습니다.",
        f"   윈도우: {folder}.7z.exe 또는 {folder}.zip",
        f"   맥: {folder}.dmg   리눅스: {folder}.tar.bz2",
        f"2. 압축을 풀면 나오는 {folder} 폴더를 아래 두 곳 가운데 한 곳에 둡니다.",
        f"   {root / folder}",
        f"   {root.parent / folder}",
        "3. 다시 실행합니다.",
        "",
        "다른 곳에 풀었다면 환경변수 RENPY_SDK 에 그 폴더의 경로를 적어 주세요.",
        "자세한 설명은 renpy/README.md 에 있습니다.",
    ])


# ---- 포트 ----

def can_bind(port, host=HOST):
    """이 포트를 지금 새로 잡을 수 있는가."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def is_listening(port, host=HOST):
    """이 포트에서 이미 어떤 프로그램이 연결을 받고 있는가."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def pick_port(first=FIRST_PORT, tries=PORT_TRIES, host=HOST, can_bind=can_bind):
    """first 부터 차례로 보고 비어 있는 첫 포트를 고른다. 다 차 있으면 운영체제가 주는 포트."""
    for port in range(first, min(first + tries, 65536)):
        if can_bind(port, host):
            return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return probe.getsockname()[1]


def port_number(text):
    """--port 값을 읽는다."""
    try:
        port = int(text)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("포트는 1-65535 사이의 숫자로 적어 주세요.")
    return port


# ---- 그림 복사 ----

def _same_file(source, target):
    """복사할 필요가 없는가. 크기와 고친 시각이 같으면 같은 파일로 본다."""
    try:
        before, after = source.stat(), target.stat()
    except OSError:
        return False
    # USB 메모리(FAT)는 시각을 2초 단위로 적는다
    return before.st_size == after.st_size and abs(before.st_mtime - after.st_mtime) <= 2


def sync_art(art_dir=ART, images_dir=IMAGES):
    """art_dir 의 sprites 와 bg 를 images_dir 아래 같은 자리로 복사한다.

    없거나 바뀐 파일만 복사한다. 지우지는 않는다. 복사한 파일의 상대 경로 목록을 돌려준다.
    """
    art_dir, images_dir = pathlib.Path(art_dir), pathlib.Path(images_dir)
    copied = []
    for folder in ART_FOLDERS:
        for source in sorted((art_dir / folder).rglob("*")):
            if source.suffix.lower() not in IMAGE_SUFFIXES or not source.is_file():
                continue
            relative = source.relative_to(art_dir)
            target = images_dir / relative
            if _same_file(source, target):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # 다 쓴 다음에 이름을 바꾼다. 복사하다 끊겨도 반쪽짜리 그림이 남지 않는다
            partial = target.with_name(target.name + ".part")
            shutil.copy2(source, partial)
            os.replace(partial, target)
            copied.append(relative.as_posix())
    return copied


# ---- 서버와 게임 ----

def server_command(port, fake=False, python=None):
    """서버를 켜는 명령."""
    command = [python or sys.executable, "-m", "sogaeting.server", "--host", HOST, "--port", str(port)]
    if fake:
        command.append("--fake")
    return command


def game_command(sdk, project=PROJECT, platform=None):
    """게임을 띄우는 명령."""
    return [str(pathlib.Path(sdk) / launcher_name(platform)), str(project)]


def game_env(env, url, windowed=False, overlay=OVERLAY):
    """게임에 줄 환경변수. env 는 고치지 않는다."""
    # 게임은 이 PC 안의 서버하고만 이야기한다. PC에 프록시 설정이 있어도 거치지 않게 한다
    result = {name: value for name, value in env.items()
              if name.lower() not in ("http_proxy", "all_proxy", "no_proxy")}
    result["no_proxy"] = "127.0.0.1,localhost"
    result["SOGAETING_URL"] = url
    # 아래 둘은 renpy/dev/booth/sg_booth.rpy 가 읽어서 창 상태를 정한다
    result["SOGAETING_WINDOW"] = "windowed" if windowed else "fullscreen"
    paths = [path for path in env.get("RENPY_SEARCHPATH", "").split("::") if path]
    if str(overlay) not in paths:
        paths.append(str(overlay))
    result["RENPY_SEARCHPATH"] = "::".join(paths)
    return result


def wait_for_server(url, process, timeout=SERVER_WAIT, interval=0.2):
    """서버의 /api/status 가 답할 때까지 기다린다.

    "ready"(답했다), "exited"(서버가 꺼졌다), "timeout"(시간이 다 됐다) 가운데 하나를 돌려준다.
    """
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 프록시를 거치지 않는다
    deadline = time.monotonic() + timeout
    while True:
        if process.poll() is not None:
            return "exited"
        try:
            with opener.open(url + "/api/status", timeout=2) as response:
                status = json.loads(response.read().decode("utf-8"))
            if isinstance(status, dict) and "sessions" in status:
                # 같은 포트의 다른 서버가 답한 것일 수도 있다. 우리 서버가 살아 있는지 다시 본다
                return "ready" if process.poll() is None else "exited"
        except (OSError, ValueError, http.client.HTTPException):
            pass  # 아직 안 켜졌거나, 이 포트에 다른 것이 있다
        if time.monotonic() >= deadline:
            return "timeout"
        time.sleep(interval)


def watch(game, server):
    """게임이 꺼질 때까지 기다린다. 게임의 종료 코드를 돌려준다."""
    warned = False
    while True:
        try:
            # 짧게 끊어서 기다린다. 윈도우에서는 끝없이 기다리는 동안 Ctrl-C가 먹지 않는다
            return game.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
        if not warned and server.poll() is not None:
            warned = True
            say(f"서버가 먼저 꺼졌습니다(종료 코드 {server.returncode}). 위에 찍힌 내용을 확인하세요.")
            say("게임을 끄고 다시 실행해 주세요.")


def stop(process, grace=5.0):
    """프로세스를 끈다. 기다려도 안 꺼지면 강제로 끈다."""
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=grace)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _interrupt(signum, frame):
    raise KeyboardInterrupt


def _set_signal(number, handler):
    """신호 처리기를 바꾸고 전의 것을 돌려준다."""
    previous = signal.signal(number, handler)
    return signal.SIG_DFL if previous is None else previous


def run(sdk, port, fake=False, windowed=False):
    """서버를 켜고, 게임을 띄우고, 게임이 꺼지면 서버를 끈다. 종료 코드를 돌려준다."""
    url = f"http://{HOST}:{port}"
    # 터미널 창을 닫거나 kill 로 끝내려 할 때도 Ctrl-C처럼 둘 다 정리한다
    numbers = [getattr(signal, name) for name in ("SIGINT", "SIGTERM", "SIGHUP", "SIGBREAK")
               if hasattr(signal, name)]
    saved = {number: _set_signal(number, _interrupt) for number in numbers}
    server = game = None
    try:
        say(f"서버를 켭니다: {url}" + (" (가짜 모델)" if fake else ""))
        server = subprocess.Popen(
            server_command(port, fake), cwd=str(ROOT), stdin=subprocess.DEVNULL,
            env=dict(os.environ, PYTHONUNBUFFERED="1"))
        state = wait_for_server(url, server)
        if state == "exited":
            say(f"서버가 켜지지 않았습니다(종료 코드 {server.returncode}). 위에 찍힌 이유를 확인하세요.")
            return 1
        if state == "timeout":
            say(f"서버가 {SERVER_WAIT:.0f}초 안에 답하지 않았습니다: {url}/api/status")
            say("위에 찍힌 내용을 확인하고 다시 실행해 주세요.")
            return 1

        say("게임을 띄웁니다" + (" (창 모드)." if windowed else " (전체 화면. 창으로 보려면 --windowed)."))
        say("게임을 끄면 서버도 같이 꺼집니다. 이 창은 닫지 말고 두세요.")
        try:
            # 리눅스와 맥에서는 터미널의 Ctrl-C가 게임에도 바로 가서 게임이 오류 글을 길게 찍는다.
            # 게임을 터미널에서 떼어 두고(start_new_session) 이 스크립트가 직접 끈다
            game = subprocess.Popen(
                game_command(sdk), cwd=str(sdk), stdin=subprocess.DEVNULL,
                env=game_env(os.environ, url, windowed), start_new_session=True)
        except OSError as error:
            say(f"게임을 띄우지 못했습니다: {error}")
            return 1
        code = watch(game, server)
        if code == 0:
            say("게임이 꺼졌습니다. 서버도 끕니다.")
        else:
            say(f"게임이 오류로 꺼졌습니다(종료 코드 {code}). 서버도 끕니다.")
            say(f"자세한 내용은 {PROJECT} 폴더의 traceback.txt 와 log.txt 에 남습니다.")
        return code
    except KeyboardInterrupt:
        say()
        say("중단 요청을 받았습니다. 게임과 서버를 끕니다.")
        return 130
    finally:
        for number in numbers:  # 정리하는 동안 Ctrl-C를 또 눌러도 끝까지 정리한다
            signal.signal(number, signal.SIG_IGN)
        try:
            # 대화 도중의 게임은 "정말 끌까요?"를 묻느라 스스로 꺼지지 않는다. 오래 기다리지 않는다
            stop(game, grace=2.0)
            stop(server)
        finally:
            for number, previous in saved.items():
                signal.signal(number, previous)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # 터미널이 못 찍는 글자가 있어도 멈추지 않는다
        except (AttributeError, ValueError):
            pass
    if sys.version_info < (3, 10):
        say("Python 3.10 이상이 필요합니다. 지금은 %d.%d 입니다." % sys.version_info[:2])
        return 1

    parser = argparse.ArgumentParser(
        prog="run_booth.py", description="소개팅 서버와 Ren'Py 게임을 한 번에 켠다.")
    parser.add_argument("--fake", action="store_true", help="실제 모델 대신 가짜 모델을 쓴다 (키 없이 시연)")
    parser.add_argument("--port", type=port_number, metavar="N",
                        help=f"서버 포트. 안 적으면 {FIRST_PORT}부터 빈 포트를 고른다")
    parser.add_argument("--windowed", action="store_true", help="전체 화면 대신 창으로 띄운다")
    args = parser.parse_args(argv)

    if not (PROJECT / "game").is_dir():
        say(f"게임 폴더가 없습니다: {PROJECT / 'game'}")
        return 1
    sdk = find_sdk()
    if sdk is None:
        print(sdk_help(), flush=True)
        return 1
    say(f"Ren'Py SDK: {sdk}")

    try:
        copied = sync_art()
    except OSError as error:
        say(f"그림을 복사하다 멈췄습니다: {error}")
        say("지금 있는 그림으로 계속합니다.")
    else:
        if copied:
            say(f"그림 {len(copied)}장을 복사했습니다: {ART} -> {IMAGES}")
        elif not any((ART / folder).is_dir() for folder in ART_FOLDERS):
            say(f"그림이 아직 없습니다({ART}). 자리표시 그림으로 진행합니다.")
        else:
            say("그림은 바뀐 것이 없습니다.")

    if args.port is None:
        port = pick_port()
    else:
        port = args.port
        if is_listening(port):
            say(f"{port}번 포트는 이미 다른 프로그램이 쓰고 있습니다.")
            say("--port 를 빼고 실행하면 빈 포트를 알아서 고릅니다.")
            return 1
    return run(sdk, port, fake=args.fake, windowed=args.windowed)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
# 화면 없이(가상 화면에서) Ren'Py 시험을 돌리고 캡처를 남긴다. 개발용이다.
#
#   RENPY_SDK=/path/to/renpy-sdk renpy/dev/rtest.sh <시험 이름> [서버 포트]
#
# 캡처는 renpy/tests/screenshots/ 에 생긴다. 서버는 따로 켜 두어야 한다:
#   python3 -m sogaeting.server --fake --port <포트>
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
sdk="${RENPY_SDK:?RENPY_SDK에 렌파이 SDK 폴더를 적어 주세요}"
name="${1:?시험 이름을 적어 주세요}"
port="${2:-8000}"
save="$(mktemp -d)"
export SOGAETING_URL="http://127.0.0.1:${port}"
cd "$sdk"
# 시험이 실패하면 게임 창이 꺼지지 않고 남는다. RTEST_TIMEOUT초(기본 300)가 지나면 끈다.
exec timeout "${RTEST_TIMEOUT:-300}" xvfb-run -a -s "-screen 0 1280x720x24" ./renpy.sh --savedir "$save" "$here" test "$name" --overwrite-screenshots

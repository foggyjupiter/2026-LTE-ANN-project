#!/bin/sh
# 소개팅 부스 실행 (리눅스, 맥). 파이썬을 찾아 같은 폴더의 run_booth.py 를 부르기만 한다.
#
#   ./run_booth.sh [--fake] [--port N] [--windowed]
#
# 설명은 renpy/README.md 에 있다.
here="$(cd "$(dirname "$0")" && pwd)"
for python in python3 python; do
    if command -v "$python" >/dev/null 2>&1; then
        exec "$python" "$here/run_booth.py" "$@"
    fi
done
echo "Python을 찾지 못했습니다. Python 3.10 이상을 설치해 주세요: https://www.python.org/downloads/" >&2
exit 1

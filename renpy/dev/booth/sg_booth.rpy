## 부스 실행기(run_booth.py)가 게임에 덧붙이는 설정.
##
## 이 파일은 renpy/game 밖에 있다. run_booth.py 가 환경변수 RENPY_SEARCHPATH 로
## 이 폴더를 알려 줄 때만 읽힌다. 렌파이 실행기나 rtest.sh 로 켜면 읽히지 않는다.

init python:
    import os

    def sg_booth_window():
        ## 켤 때마다 창 상태를 정한다. 지난번에 누가 F11로 바꿔 둔 상태가 남지 않는다.
        mode = os.environ.get("SOGAETING_WINDOW", "")
        if mode == "fullscreen":
            _preferences.fullscreen = True
        elif mode == "windowed":
            _preferences.fullscreen = False

    ## 초기화가 다 끝나고 화면이 뜨기 직전에 불린다. 게임의 기본 설정보다 나중에 적용된다.
    config.start_callbacks.append(sg_booth_window)

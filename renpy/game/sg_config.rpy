## 소개팅 화면이 쓰는 설정.
##
## 대화 로직은 전부 로컬 서버(sogaeting/server.py)에 있다. 이 게임은 화면만 그린다.

init -10 python:
    import os

    ## 서버 주소. 환경변수 SOGAETING_URL로 바꿀 수 있다. 끝에 빗금을 붙이지 않는다.
    sg_server_url = os.environ.get("SOGAETING_URL", "http://127.0.0.1:8000").rstrip("/")

    ## 서버의 답을 기다리는 한도(초). 모델이 길면 30초쯤 걸리므로 넉넉히 준다.
    ## renpy.fetch의 기본값은 5초라서 그대로 두면 답이 오기 전에 끊긴다.
    sg_timeout = 90.0

    ## 이만큼(초) 입력이 없으면 판을 버리고 고르기 화면으로 돌아간다.
    sg_idle_seconds = 180.0

    ## 내 말을 보낸 뒤 답이 바로 와도 이만큼(초)은 기다리는 화면을 보여 준다.
    ## 내가 한 말이 대사창에 잠깐이라도 보이게 하려는 것이다.
    sg_min_wait = 0.4

    ## 대사가 한 글자씩 나오는 속도(초당 글자 수).
    sg_text_cps = 45

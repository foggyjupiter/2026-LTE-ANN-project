## 소개팅 화면이 쓰는 설정.
##
## 대화 로직은 전부 로컬 서버(sogaeting/server.py)에 있다. 이 게임은 화면만 그린다.

init -10 python:
    import os

    ## 서버 주소. 환경변수 SOGAETING_URL로 바꿀 수 있다. 끝에 빗금을 붙이지 않는다.
    sg_server_url = os.environ.get("SOGAETING_URL", "http://127.0.0.1:8000").rstrip("/")

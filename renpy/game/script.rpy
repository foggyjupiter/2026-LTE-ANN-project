## 소개팅의 흐름: 고르기 → 대화 → 엔딩 → 고르기.
##
## 여기에는 화면을 넘기는 순서와 서버를 부르는 차례만 있다.
##   화면의 모양              sg_screens.rpy
##   서버 호출, 무대, 화면용 값   sg_core.rpy
##   대화 로직                로컬 서버 (sogaeting/server.py). Ren'Py로 옮기지 않는다

## Ren'Py 기본 주 메뉴를 건너뛴다. 이 레이블이 돌아오면 곧장 start로 간다.
label main_menu:
    return


label start:
    jump sg_select


## 1. 캐릭터 고르기 ##################################################################

label sg_select:

    $ sg_enter_select()

    ## 캐릭터 명단은 처음 한 번만 받는다.
    if not sg_cards:
        show screen sg_wait("캐릭터 명단을 불러오는 중", dim=False)
        $ sg_result = sg_fetch_cards()
        hide screen sg_wait

        if not sg_result.ok:
            call screen sg_error(sg_result.message, [ ("다시 시도", "retry") ])
            jump sg_select

        $ sg_cards = sg_result.data

    call screen sg_select(sg_cards)
    if _return == "ranking":
        jump sg_show_ranking
    $ sg_char = _return
    jump sg_begin


## 첫 화면의 "오늘의 순위". 보고 닫으면 고르기 화면으로 돌아간다.
label sg_show_ranking:

    ## 순위표를 열어 둔 채 떠나도 입력이 없으면 고르기 화면으로 돌아오게 감시를 켠다
    $ sg_in_play = True
    show screen sg_wait("순위표를 불러오는 중")
    $ sg_result = sg_request("/api/ranking", check=sg_is_board)
    hide screen sg_wait

    if not sg_result.ok:
        call screen sg_error(sg_result.message, [ ("다시 시도", "retry"), ("닫기", "home") ])
        if _return == "retry":
            jump sg_show_ranking
        jump sg_select

    call screen sg_ranking(sg_build_board(sg_result.data), after_game=False)
    jump sg_select


## 2. 대화 #########################################################################

## 새 판을 연다. 엔딩의 "다시 하기"도 여기로 온다.
label sg_begin:

    $ sg_enter_game()

    show screen sg_wait_start(sg_char)
    $ sg_result = sg_request("/api/session", { "character": sg_char["id"] }, check=sg_is_session)
    hide screen sg_wait_start

    if not sg_result.ok:
        call screen sg_error(sg_result.message, [ ("다시 시도", "retry"), ("처음으로", "home") ])
        if _return == "retry":
            jump sg_begin
        jump sg_select

    $ sg_session = sg_result.data["session_id"]
    $ sg_turn = sg_result.data["turn"]
    jump sg_play


## 서버가 준 턴 하나를 보여 주고 참가자의 답을 받는다.
label sg_play:

    $ sg_enter_turn(sg_turn)

label sg_listen:

    show screen sg_hud
    call screen sg_talk(sg_view, sg_first_stage)
    $ sg_answer = _return

    if sg_answer[0] == "finish":
        jump sg_finish

    jump sg_send


## 참가자의 답을 서버에 보내고 다음 턴을 받는다.
label sg_send:

    show screen sg_wait_reply(sg_answer[1])
    ## turn: 이 답으로 받을 턴의 번호. 시간 초과 뒤 "다시 시도"로 같은 답을 또 보내도, 서버가 이미 처리한
    ## 답이면 같은 턴을 다시 돌려준다. 같은 말이 두 번 들어가지 않는다
    $ sg_result = sg_request(sg_session_path("reply"), { "text": sg_answer[1], "turn": sg_turn_no + 1 }, check=sg_is_turn, min_wait=sg_min_wait)
    hide screen sg_wait_reply

    if sg_result.ok:
        $ sg_turn = sg_result.data
        jump sg_play

    ## 409: 이 판은 더 답을 받지 않는다. 엔딩으로 간다.
    if sg_result.status == 409:
        jump sg_finish

    ## 404: 판이 사라졌다. (서버를 다시 켰거나 오래 비워 둔 판)
    if sg_result.status == 404:
        call screen sg_error(SG_MSG_GONE, [ ("처음으로", "home") ])
        jump sg_select

    ## 400: 보낸 글을 서버가 받지 않았다. 선택지로 돌아가 다시 고르게 한다.
    if sg_result.status == 400:
        call screen sg_error(sg_result.message, [ ("돌아가기", "back") ])
        $ sg_first_stage = sg_view["stages"][-1]
        $ sg_typed = ""
        jump sg_listen

    call screen sg_error(sg_result.message, [ ("다시 시도", "retry"), ("처음으로", "home") ])
    if _return == "retry":
        jump sg_send
    jump sg_select


## 3. 엔딩 #########################################################################

## 마지막 답 뒤의 "엔딩 보기"와 도중의 "엔딩 보러 가기"가 모두 여기로 온다.
label sg_finish:

    hide screen sg_confirm
    show screen sg_wait("엔딩을 불러오는 중")
    $ sg_result = sg_request(sg_session_path("finish"), method="POST", check=sg_is_finish, min_wait=sg_min_wait)
    hide screen sg_wait

    if not sg_result.ok:
        if sg_result.status == 404:
            call screen sg_error(SG_MSG_GONE, [ ("처음으로", "home") ])
            jump sg_select

        call screen sg_error(sg_result.message, [ ("다시 시도", "retry"), ("처음으로", "home") ])
        if _return == "retry":
            jump sg_finish
        jump sg_select

    $ sg_enter_ending(sg_result.data["ending"])
    $ sg_rank_sid = ""
    $ sg_rank_person = ""
    $ sg_rank_error = ""

label sg_show_ending:

    call screen sg_ending(sg_end_view)

    if _return == "rank":
        jump sg_rank
    if _return == "again":
        jump sg_begin
    jump sg_select


## 엔딩의 "순위표 등록": 학번과 이름을 받아 서버에 남기고 오늘의 순위표를 보여 준다. 상품을 줄 때 쓴다.
label sg_rank:

    call screen sg_rank_entry(sg_end_view["score"], sg_rank_error)
    if _return[0] == "skip":
        jump sg_show_ending

    show screen sg_wait("순위표에 올리는 중")
    $ sg_result = sg_request(sg_session_path("rank"), { "student_id": _return[1], "name": _return[2] }, check=sg_is_board)
    hide screen sg_wait

    if not sg_result.ok:
        ## 400: 서버가 받지 않았다(학번 모양, 이름 길이, 금지어). 까닭을 띄우고 거절된 칸만 비워 다시 쓰게 한다.
        ## 어느 칸인지는 서버의 문구(sogaeting/ranking.py MSG_*)가 "학번"으로 시작하는지로 가른다
        if sg_result.status == 400:
            $ sg_rank_error = sg_result.message
            if sg_result.message.startswith("학번"):
                $ sg_rank_sid = ""
            else:
                $ sg_rank_person = ""
            jump sg_rank

        if sg_result.status == 404:
            call screen sg_error(SG_MSG_GONE, [ ("처음으로", "home") ])
            jump sg_select

        call screen sg_error(sg_result.message, [ ("다시 시도", "retry"), ("건너뛰기", "skip") ])
        if _return == "retry":
            jump sg_rank
        jump sg_show_ending

    $ sg_rank_error = ""
    $ sg_board_view = sg_build_board(sg_result.data)
    call screen sg_ranking(sg_board_view, after_game=True)

    if _return == "again":
        jump sg_begin
    jump sg_select


## 입력 없음 ########################################################################

## sg_idle_seconds초 동안 입력이 없으면 여기로 온다. 판을 버리고 고르기 화면으로 돌아간다.
## 엔딩을 부르지 않으므로 결과는 남지 않는다.
label sg_idle:
    jump sg_select

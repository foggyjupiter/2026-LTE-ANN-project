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
    $ sg_char = _return
    jump sg_begin


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
    $ sg_result = sg_request(sg_session_path("reply"), { "text": sg_answer[1] }, check=sg_is_turn, min_wait=sg_min_wait)
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
    call screen sg_ending(sg_end_view)

    if _return == "again":
        jump sg_begin
    jump sg_select


## 입력 없음 ########################################################################

## sg_idle_seconds초 동안 입력이 없으면 여기로 온다. 판을 버리고 고르기 화면으로 돌아간다.
## 엔딩을 부르지 않으므로 결과는 남지 않는다.
label sg_idle:
    jump sg_select

## 화면 시험. 가짜 모델 서버를 켜 두고 돌린다.
##
##   python3 -m sogaeting.server --fake --port 8101 --results <임시 폴더>
##   RENPY_SDK=<SDK 폴더> renpy/dev/rtest.sh <시험 이름> 8101
##
## 캡처는 renpy/tests/screenshots/ 에 생긴다.

init python:

    def sg_test_text(text):
        """입력칸에 글을 넣는다.

        시험 문법의 type 은 글쇠 이름이 있는 글자(영문, 숫자, 기호)만 칠 수 있다.
        한글은 IME가 글자를 확정했을 때 오는 것과 같은 이벤트(TEXTINPUT)를 직접 보낸다.
        조합 중인 글자(TEXTEDITING)는 흉내 내지 않는다.
        """
        import pygame_sdl2
        pygame_sdl2.event.post(pygame_sdl2.event.Event(pygame_sdl2.TEXTINPUT, text=text, test=True))


## 고르기 → 한 판 끝까지 → 엔딩 → 첫 화면. 선택지 고르기와 직접 말하기를 둘 다 쓴다.
##
## 다음 턴이 왔는지는 sg_turn_no 로 본다. (보낸 직후에는 앞 턴의 sg_talk 화면이 아직 떠 있을 수 있다)
testcase sg_flow:
    pause until screen "sg_select"
    pause 0.8
    screenshot "flow_01_select.png"
    ## 고르기 화면에서는 menu 곡 (소리를 끈 실행이면 아무 곡도 없다)
    assert eval (sg_audio_muted or sg_bgm_now == "menu")
    assert eval (sg_audio_muted or sg_bgm_channel_now == "sg_bgm_a")

    ## 카드에 마우스를 올리면 떠오르며 빛난다
    move "미스트랄"
    pause 0.5
    screenshot "flow_01b_card_hover.png"

    click "아스트라"
    pause until screen "sg_talk"
    pause 0.8
    screenshot "flow_02_narration.png"
    ## 대화가 시작되면 호감도 구간의 곡으로 바뀐다 (시작은 50점이라 talk)
    assert eval (sg_audio_muted or sg_bgm_now == "talk")
    ## 새 곡은 다른 채널에서 커지고 앞 곡은 원래 채널에서 줄어든다 (두 곡이 겹치며 바뀐다)
    assert eval (sg_audio_muted or sg_bgm_channel_now == "sg_bgm_b")
    assert eval (sg_bgm_mood_for(70, "talk") == "high" and sg_bgm_mood_for(62, "high") == "high" and sg_bgm_mood_for(58, "high") == "talk")
    assert eval (sg_bgm_mood_for(38, "talk") == "low" and sg_bgm_mood_for(43, "low") == "low" and sg_bgm_mood_for(46, "low") == "talk")

    ## 지문 → 대사
    click id "sg_advance"
    pause 1.6
    screenshot "flow_03_say.png"

    ## 대사 → 선택지
    click id "sg_advance"
    pause until id "sg_input"
    pause 0.6
    screenshot "flow_04_choices.png"

    ## 선택지에 마우스를 올리면 빛나고 살짝 커진다
    move "잘 모르겠는데"
    pause 0.5
    screenshot "flow_04b_choice_hover.png"

    ## 답 1: 선택지
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 1)
    pause 0.5
    click id "sg_advance"
    pause 1.6
    screenshot "flow_05_reply1_say.png"
    click id "sg_advance"
    pause until id "sg_input"
    pause 0.6
    screenshot "flow_05b_reply1_choices.png"

    ## 답 2: 직접 말하기 (영문은 글쇠로, 한글은 확정된 글로), Enter로 보내기
    type "hello "
    $ sg_test_text("직접 말하기 시험")
    pause 0.5
    screenshot "flow_06_typing.png"
    keysym "K_RETURN"
    pause until eval (sg_turn_no == 2)
    pause 0.5
    click id "sg_advance"
    pause 1.6
    screenshot "flow_07_reply2_say.png"
    click id "sg_advance"
    pause until id "sg_input"

    ## 답 3: 직접 말하기, 보내기 단추
    $ sg_test_text("단추로 보내기")
    pause 0.3
    click "보내기"
    pause until eval (sg_turn_no == 3)
    pause 0.5
    click id "sg_advance" until id "sg_input"

    ## 답 4-10: 선택지
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 4)
    pause 0.5
    click id "sg_advance"
    pause 1.6
    screenshot "flow_07b_reply4_explode.png"
    click id "sg_advance" until id "sg_input"
    click "잘 모르겠는데"
    pause until eval (sg_turn_no == 5)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 6)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    click "잘 모르겠는데"
    pause until eval (sg_turn_no == 7)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 8)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 9)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 10)
    pause 0.5
    click id "sg_advance"
    pause 1.6
    screenshot "flow_08_last_say.png"
    click id "sg_advance"
    pause 0.8
    screenshot "flow_09_finale.png"

    click "엔딩 보기"
    pause until screen "sg_ending"
    pause 1.2
    screenshot "flow_10_ending.png"
    ## 엔딩에서는 배경음을 줄이고 엔딩 음을 들려준다
    assert eval (sg_bgm_now is None)
    ## 호감도는 소수 한 자리다 (가짜 모델은 반응의 세기를 차례로 돌린다)
    assert eval (sg_score_text(sg_end_view["score"]).count(".") == 1)

    ## 순위표 등록: 학번과 이름. 금지어가 든 이름은 까닭을 띄우고 고쳐 쓰게 한다
    click "순위표 등록"
    pause until screen "sg_rank_entry"
    $ sg_test_text("20312")
    click id "sg_rank_person"
    $ sg_test_text("시발")
    pause 0.3
    click "올리기"
    pause until eval (sg_rank_error != "")
    pause until screen "sg_rank_entry"
    pause 0.4
    screenshot "flow_10b_rank_refused.png"
    ## 거절된 이름 칸만 비고 학번은 남아 있다
    assert eval (sg_rank_sid == "20312" and sg_rank_person == "")
    click id "sg_rank_person"
    $ sg_test_text("김민수")
    pause 0.3
    screenshot "flow_10c_rank_typed.png"
    click "올리기"
    pause until screen "sg_ranking"
    pause 0.6
    screenshot "flow_10d_ranking.png"
    ## 결과 폴더에 다른 판이 많으면 내 줄은 위 열 줄 밖(you_below)에 있다. 이름은 가운데가 가려져 온다
    assert eval (any(r["you"] and r["student_id"] == "20312" and r["name"] == "김*수" for r in sg_board_view["rows"] + [ sg_board_view["you_below"] or { } ]))

    click "다른 캐릭터 고르기"
    pause until screen "sg_select"
    assert eval (sg_audio_muted or sg_bgm_now == "menu")
    pause 0.6
    screenshot "flow_11_back_to_select.png"

    ## 첫 화면의 오늘의 순위
    click "오늘의 순위"
    pause until screen "sg_ranking"
    pause 0.6
    screenshot "flow_12_ranking_from_select.png"
    click "닫기"
    pause until screen "sg_select"
    exit


## 캐릭터마다 고유 장치가 화면에 보이는지 캡처한다.
testsuite sg_gimmicks:

    teardown:
        exit

    ## 젬마: 대사 속 인용문에 형광펜
    testcase gemma:
        pause until screen "sg_select"
        click "젬마"
        pause until screen "sg_talk"
        click id "sg_advance" until id "sg_input"
        $ sg_test_text("형광펜 칠해 줘")
        keysym "K_RETURN"
        pause until eval (sg_turn_no == 1)
        pause 0.5
        click id "sg_advance"
        pause 1.8
        screenshot "gimmick_gemma_highlight.png"
        run Jump("sg_select")

    ## 소라: 장치가 없다. 내 말이 가려지지 않고 "들린 말" 단계 없이 바로 지문으로 간다
    testcase sora:
        pause until screen "sg_select"
        click "소라"
        pause until screen "sg_talk"
        click id "sg_advance" until id "sg_input"
        click "좋아, 더 말해줘"
        pause until eval (sg_turn_no == 1)
        pause 0.5
        assert eval (sg_view["stages"][0] != "heard")
        click id "sg_advance"
        pause 1.8
        screenshot "gimmick_sora_say.png"
        run Jump("sg_select")

    ## 노바: 싫은 소리를 들어도 점수가 내려가지 않는다는 알림
    testcase nova:
        pause until screen "sg_select"
        click "노바"
        pause until screen "sg_talk"
        click id "sg_advance" until id "sg_input"
        click "물구나무를 서 본다"
        pause until eval (sg_turn_no == 1)
        pause 0.5
        click id "sg_advance"
        pause 1.8
        screenshot "gimmick_relu_note.png"
        run Jump("sg_select")

    ## 미스트랄: 출처 딱지
    testcase mistral:
        pause until screen "sg_select"
        click "미스트랄"
        pause until screen "sg_talk"
        click id "sg_advance" until id "sg_input"
        click "좋아, 더 말해줘"
        pause until eval (sg_turn_no == 1)
        pause 0.5
        click id "sg_advance"
        pause 1.8
        screenshot "gimmick_mistral_cite.png"
        click id "sg_advance" until id "sg_input"
        click "잘 모르겠는데"
        pause until eval (sg_turn_no == 2)
        pause 0.5
        click id "sg_advance"
        pause 1.8
        screenshot "gimmick_mistral_cite2.png"
        run Jump("sg_select")

    ## 하이쿠: 가려진 속마음, 도중에 엔딩으로 가기, 엔딩에서 원문 공개, 다시 하기
    testcase haiku:
        pause until screen "sg_select"
        click "하이쿠"
        pause until screen "sg_talk"
        click id "sg_advance"
        pause 1.6
        screenshot "gimmick_haiku_masked0.png"
        click id "sg_advance" until id "sg_input"
        click "좋아, 더 말해줘"
        pause until eval (sg_turn_no == 1)
        pause 0.5
        click id "sg_advance"
        pause 1.8
        screenshot "gimmick_haiku_masked1.png"
        click "엔딩 보러 가기"
        pause until screen "sg_confirm"
        pause 0.3
        screenshot "gimmick_haiku_quit_confirm.png"
        click "엔딩 보기"
        pause until screen "sg_ending"
        pause 1.2
        screenshot "gimmick_haiku_ending.png"
        click "속마음 보기"
        pause 0.6
        screenshot "gimmick_haiku_reveal.png"
        click "닫기"
        pause 0.3
        click "다시 하기"
        pause until eval (sg_turn_no == 0 and renpy.get_screen("sg_talk") is not None)
        pause 0.8
        screenshot "gimmick_haiku_again.png"
        run Jump("sg_select")


## 아래 시험들은 가짜 모델을 바꿔 끼운 임시 서버로 돌린다. (server.py 는 그대로 쓴다)

## 기다리는 표시. 모델이 답마다 9.5초 걸리는 서버로 돌린다.
testcase sg_waiting:
    pause until screen "sg_select"
    click "노바"
    pause 1.2
    screenshot "wait_start_a.png"
    pause 0.3
    screenshot "wait_start_b.png"
    pause 4.4
    screenshot "wait_start_late.png"
    pause until screen "sg_talk" timeout 20.0
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause 1.2
    screenshot "wait_reply_a.png"
    pause 0.3
    screenshot "wait_reply_b.png"
    pause 4.4
    screenshot "wait_reply_late.png"
    pause until eval (sg_turn_no == 1) timeout 20.0
    pause 0.5
    click "엔딩 보러 가기"
    pause until screen "sg_confirm"
    click "엔딩 보기"
    pause 1.5
    screenshot "wait_ending.png"
    pause until screen "sg_ending" timeout 20.0
    exit

## 서버에서 온 글에 [ { % 같은 글자가 있어도 글자 그대로 찍히는지 본다.
testcase sg_weird_text:
    pause until screen "sg_select"
    click "미스트랄"
    pause until screen "sg_talk"
    pause 0.8
    screenshot "weird_narration.png"
    click id "sg_advance"
    pause 3.0
    screenshot "weird_say.png"
    click id "sg_advance" until id "sg_input"
    pause 0.5
    screenshot "weird_choices.png"
    click "[선택] 하나"
    pause until eval (sg_turn_no == 1)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    $ sg_test_text("[x] {y} 직접 [입력] {중괄호} 100%")
    pause 0.4
    screenshot "weird_typing.png"
    keysym "K_RETURN"
    pause 0.25
    screenshot "weird_my_line.png"
    pause until eval (sg_turn_no == 2)
    pause 0.5
    click id "sg_advance"
    pause 3.0
    screenshot "weird_say2.png"
    click "엔딩 보러 가기"
    pause until screen "sg_confirm"
    click "엔딩 보기"
    pause until screen "sg_ending"
    pause 1.0
    screenshot "weird_ending.png"
    exit

## 서버 오류: 500(다시 시도), 404(판이 사라짐 → 첫 화면), 409(엔딩으로).
## 첫 번째 reply 요청에서 500을 내는 서버로 돌린다.
testcase sg_errors:
    pause until screen "sg_select"
    click "소라"
    pause until screen "sg_talk"
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause until screen "sg_error"
    pause 0.5
    screenshot "error_500.png"
    click "다시 시도"
    pause until eval (sg_turn_no == 1)
    pause 0.5
    click id "sg_advance" until id "sg_input"

    ## 409: 서버에서 이 판을 먼저 끝내 놓고 답을 보낸다. 엔딩으로 넘어가야 한다.
    $ import urllib.request
    $ urllib.request.urlopen(urllib.request.Request(sg_server_url + sg_session_path("finish"), data=b"", method="POST")).read()
    click "잘 모르겠는데"
    pause until screen "sg_ending"
    pause 1.0
    screenshot "error_409_to_ending.png"
    click "다시 하기"
    pause until eval (sg_turn_no == 0 and renpy.get_screen("sg_talk") is not None)
    click id "sg_advance" until id "sg_input"

    ## 404: 판 id를 없는 것으로 바꾸고 답을 보낸다. 안내 뒤에 첫 화면으로 가야 한다.
    $ sg_session = "no-such-session"
    click "잘 모르겠는데"
    pause until screen "sg_error"
    pause 0.5
    screenshot "error_404.png"
    click "처음으로"
    pause until screen "sg_select"
    exit

## 서버가 꺼져 있을 때. 서버를 끄고 돌린다.
testcase sg_server_down:
    pause until screen "sg_error"
    pause 0.5
    screenshot "down_select.png"
    click "다시 시도"
    pause 1.0
    assert screen "sg_error"
    exit

## 3분 동안 입력이 없으면 고르기 화면으로. 시험에서는 3초로 줄인다.
testcase sg_idle_reset:
    pause until screen "sg_select"
    $ sg_idle_seconds = 3.0
    click "아스트라"
    pause until screen "sg_talk"
    click id "sg_advance"
    pause 1.0
    assert screen "sg_talk"
    pause until screen "sg_select" timeout 8.0
    pause 0.5
    screenshot "idle_back_to_select.png"
    $ sg_idle_seconds = 180.0
    exit


## 대체 대사(fallback) 턴: 점수 표시가 없고, 선택지 없이 직접 말하기만 나온다.
## 모델이 첫 답에서 읽을 수 없는 글을 내는 서버로 돌린다.
testcase sg_fallback:
    pause until screen "sg_select"
    click "아스트라"
    pause until screen "sg_talk"
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 1)
    pause 1.2
    screenshot "fallback_say.png"
    click id "sg_advance" until id "sg_input"
    pause 0.5
    screenshot "fallback_input_only.png"
    $ sg_test_text("선택지가 없어도 직접 말할 수 있다")
    keysym "K_RETURN"
    pause until eval (sg_turn_no == 2)
    exit


## 긴 글이 대사창, 풍선, 선택지, 엔딩 카드에서 넘치지 않는지 본다.
## 모델이 긴 글을 내는 서버로 돌린다.
testcase sg_long_text:
    pause until screen "sg_select"
    click "아스트라"
    pause until screen "sg_talk"
    pause 2.5
    screenshot "long_narration.png"
    click id "sg_advance"
    pause 0.3
    click id "sg_advance"
    pause 0.8
    screenshot "long_say.png"
    click id "sg_advance" until id "sg_input"
    pause 0.5
    screenshot "long_choices.png"
    $ sg_test_text("백 자를 꽉 채운 긴 답을 직접 말하기 칸에 넣어 본다. 줄이 바뀌어도 선택지와 대사창을 가리지 않아야 하고, 글자 수 표시도 맞아야 한다. 과연 어디까지 들어갈까 궁금하다 정말로")
    pause 0.5
    screenshot "long_typing.png"
    keysym "K_RETURN"
    pause 0.25
    screenshot "long_my_line.png"
    pause until eval (sg_turn_no == 1)
    pause 0.5
    click id "sg_advance"
    pause 0.3
    click id "sg_advance"
    pause 0.8
    screenshot "long_say_popup.png"
    click "엔딩 보러 가기"
    pause until screen "sg_confirm"
    click "엔딩 보기"
    pause until screen "sg_ending"
    pause 1.0
    screenshot "long_ending.png"
    exit


## 부스용 잠금: 오른쪽 클릭, Esc, 되감기 글쇠를 눌러도 메뉴가 뜨거나 되감기지 않는다.
testcase sg_locked:
    pause until screen "sg_select"
    click button 2 pos (640, 100)
    keysym "K_ESCAPE"
    keysym "K_PAGEUP"
    pause 0.5
    assert screen "sg_select"
    click "소라"
    pause until screen "sg_talk"
    click id "sg_advance"
    pause 1.0
    click button 2 pos (640, 300)
    keysym "K_ESCAPE"
    keysym "K_PAGEUP"
    keysym "K_TAB"
    pause 0.5
    assert screen "sg_talk"
    assert eval (sg_turn_no == 0 and not renpy.get_screen("sg_select"))
    screenshot "locked_still_talking.png"
    exit


## 대표색이 밝든 어둡든 이름표 리본과 속성 리본의 글자가 읽히는지 본다.
## 서버가 주는 색과 상관없이 새 배역의 대표색을 화면 쪽에서 덮어쓰고 캡처한다.
testsuite sg_colors:

    setup:
        pause until screen "sg_select"
        python:
            for sg_test_card in sg_cards:
                sg_test_card["color"] = {
                    "astra": "#4050C8", "gemma": "#9B6BD6", "sora": "#7CCBF2",
                    "nova": "#F0508A", "mistral": "#F5A623", "haiku": "#D97757",
                }.get(sg_test_card["id"], sg_test_card["color"])
            renpy.restart_interaction()
        pause 0.8
        screenshot "colors_select.png"

    teardown:
        exit

    testcase tag:
        parameter who = [ "아스트라", "젬마", "소라", "노바", "미스트랄", "하이쿠" ]
        pause until screen "sg_select"
        click expression who
        pause until screen "sg_talk"
        click id "sg_advance"
        pause 1.6
        screenshot f"colors_tag_{who}.png"
        run Jump("sg_select")


## 이야기 모드(실험)의 긴 글: 지문과 대사가 여러 쪽으로 나뉘는지. 이야기 모드 가짜 모델 서버를 켜 두고 돌린다.
##   SOGAETING_STORY=1 python3 -m sogaeting.server --fake --port 8101   (또는 --story)
testcase sg_story_pages:
    pause until screen "sg_select"
    click "젬마"
    pause until screen "sg_talk"
    pause 2.5
    screenshot "story_01_narration.png"
    ## 긴 대사는 여러 쪽이고, 어느 쪽도 글자가 20보다 작아지지 않는다
    assert eval (len(sg_view["say_pages"]) >= 2)
    assert eval (all(p["size"] >= 20 for p in sg_view["narration_pages"] + sg_view["say_pages"]))
    click id "sg_advance" until eval (renpy.get_screen("sg_talk").scope.get("stage") == "say")
    pause 2.5
    screenshot "story_02_say_p1.png"
    click id "sg_advance"
    pause 2.5
    screenshot "story_03_say_p2.png"
    click id "sg_advance" until id "sg_input"
    pause 0.6
    screenshot "story_04_choices_last_page.png"
    exit


## 캐릭터만의 표정: 아스트라에게 여섯 글자를 보내면 가짜 모델이 삐침(pout) 자리의 huff 를 낸다(fake_llm 의 글자 수 규칙).
## huff 그림(images/sprites/astra/huff.png)이 없으면 pout 그림을 쓰고, 움직임과 기호는 pout 의 것을 쓴다.
##   python3 -m sogaeting.server --fake --port 8101
testcase sg_extra_face:
    assert eval (sg_view_face({"face": "huff", "face_base": "pout"}) == "pout")
    assert eval (sg_view_face({"face": "huff"}) == "neutral" and sg_view_face({"face": "smile", "face_base": "pout"}) == "smile")
    assert eval (sg_face_name_ok("red_ears") and not sg_face_name_ok("../x") and not sg_face_name_ok("") and not sg_face_name_ok(3))
    assert eval (sg_sprite_path("gemma", "blush", "hide") == sg_sprite_path("gemma", "blush"))
    assert eval (sg_sprite_path("gemma", "blush", "../../x") == sg_sprite_path("gemma", "blush"))
    pause until screen "sg_select"
    click "아스트라"
    pause until screen "sg_talk"
    click id "sg_advance" until id "sg_input"
    $ sg_test_text("가나다라마바")
    keysym "K_RETURN"
    pause until eval (sg_turn_no == 1)
    assert eval (sg_view["face"] == "pout" and sg_view["sprite_face"] == "huff")
    pause 0.5
    click id "sg_advance"
    pause 1.5
    screenshot "extra_face_astra_huff.png"
    exit

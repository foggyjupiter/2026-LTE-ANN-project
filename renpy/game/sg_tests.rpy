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

    click "기울희"
    pause until screen "sg_talk"
    pause 0.8
    screenshot "flow_02_narration.png"

    ## 지문 → 대사
    click id "sg_advance"
    pause 1.6
    screenshot "flow_03_say.png"

    ## 대사 → 선택지
    click id "sg_advance"
    pause until id "sg_input"
    pause 0.6
    screenshot "flow_04_choices.png"

    ## 답 1: 선택지
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 1)
    pause 0.5
    click id "sg_advance"
    pause 1.6
    screenshot "flow_05_reply1_say.png"
    click id "sg_advance"
    pause until id "sg_input"

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

    ## 답 4-7: 선택지
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 4)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    click "잘 모르겠는데"
    pause until eval (sg_turn_no == 5)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 6)
    pause 0.5
    click id "sg_advance" until id "sg_input"
    click "좋아, 더 말해줘"
    pause until eval (sg_turn_no == 7)
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

    click "다른 캐릭터 고르기"
    pause until screen "sg_select"
    pause 0.6
    screenshot "flow_11_back_to_select.png"
    exit

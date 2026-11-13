## sg_stage_demo.rpy: 무대 연기(sg_stage.rpy)의 시험장.
##
## 서버 없이 돈다. 진짜 무대 함수(sg_show_bg, sg_show_char, sg_stage_turn)를 그대로 불러서
## 표정 여섯 가지의 동작과 만화 기호를 하나씩 재생한다.
##
##   사람이 볼 때   개발자 콘솔(Shift+O)에서  jump sg_stage_demo
##   자동 시험      RENPY_SDK=<SDK 폴더> renpy/dev/rtest.sh sg_stage_demo
##                  캡처는 renpy/tests/screenshots/stage_*.png 에 생긴다
##
## 게임에는 쓰이지 않는 파일이다. 지워도 게임은 돌아간다.

default sg_stage_demo_line = "무대 연기 시험장"
default sg_stage_demo_i = 0

## 시험장에 세울 캐릭터와 배경.
define sg_stage_demo_char = "giulhee"
define sg_stage_demo_bg = "cafeteria"
define sg_stage_demo_place = "급식실"

init python:

    ## 사람이 볼 때의 차례: (표정, 호감도 변화, 연출, 다음으로 넘어가기 전에 기다리는 시간)
    sg_stage_demo_list = [
        ("smile", 7, None, 2.4),
        ("blush", 14, None, 2.6),
        ("pout", -7, None, 2.4),
        ("shock", -14, None, 2.4),
        ("dark", -14, None, 3.0),
        ("neutral", 0, None, 2.4),
        ("smile", 14, None, 2.6),
        ("smile", 7, None, 2.4),          # 같은 표정이 이어진다: 큰 동작 없이 기호만
        ("blush", 7, None, 2.4),
        ("neutral", -7, None, 2.4),
        ("shock", 0, ["줌인", "집중선"], 2.6),
        ("pout", -7, ["흔들림"], 2.4),
    ]

    def sg_stage_demo_setup():
        """무대를 비우고 배경과 가짜 대사창을 차린다. 스탠딩은 아직 없다."""
        sg_clear_fx()
        sg_show_bg(sg_stage_demo_bg)
        renpy.show_screen("sg_stage_demo_say")
        store.sg_stage_demo_line = "무대 연기 시험장"
        renpy.restart_interaction()

    def sg_stage_demo_go(face, change=0, first=False, fallback=False, fx=None):
        """턴 하나를 흉내 낸다: 표정을 바꾸고, 기호를 띄우고, 연출이 있으면 건다."""
        sg_show_char(sg_stage_demo_char, face)
        sg_stage_turn(face, change, first=first, fallback=fallback,
                      place=sg_stage_demo_place if first else "")
        sg_call_fx(fx or [ ], "지문")
        picked = sg_stage_pick_emotes(face, change, first, fallback)
        store.sg_stage_demo_line = "%s%s  호감도 %+d  기호: %s%s" % (
            "등장  " if first else "", face, change,
            ", ".join(kind for kind, spot, move in picked) or "없음",
            ("  연출: " + " + ".join(fx)) if fx else "")
        renpy.transition(sg_stage_trans_scene if first else sg_stage_trans_turn)
        renpy.restart_interaction()

    def sg_stage_demo_end(band_id):
        """엔딩 화면처럼 왼쪽으로 비켜서고 등급에 맞는 기호를 띄운다."""
        sg_show_char(sg_stage_demo_char, sg_band_face.get(band_id, "neutral"), at=sg_char_left)
        sg_stage_ending(band_id)
        store.sg_stage_demo_line = "엔딩 자리  등급: %s" % band_id
        renpy.transition(sg_stage_trans_ending)
        renpy.restart_interaction()

    def sg_stage_demo_emotes():
        """지금 무대에 떠 있는 기호의 수."""
        return len([ i for i in range(sg_stage_emote_max) if renpy.showing("sg_emote%d" % i, layer="master") ])

    def sg_stage_demo_layer_free():
        """master 레이어 자리에 걸린 transform 이 없으면 True. 그 자리는 연출(sg_fx)만 쓴다."""
        sls = renpy.display.scenelists.scene_lists()
        return not sls.layer_at_list["master"][1]


## 가짜 대사창. 진짜 대사창과 같은 자리(아래 185픽셀)에, screens 레이어에 뜬다.
screen sg_stage_demo_say():
    zorder 5
    frame:
        background Solid("#1b2559d9")
        xfill True
        ysize 185
        yalign 1.0
        padding (120, 30, 120, 20)
        vbox:
            spacing 10
            text "무대 연기 시험장" font "fonts/Pretendard-Bold.otf" size 26 color "#ffd6e4"
            text sg_stage_demo_line font "fonts/Pretendard-Regular.otf" size 22 color "#ffffff" substitute False


## 사람이 보는 시험장. 등장, 표정 동작과 기호, 연출과 함께, 엔딩 자리를 차례로 튼다.
label sg_stage_demo:
    $ sg_stage_demo_setup()
    pause 0.6
    $ sg_stage_demo_go("neutral", 0, first=True)
    pause 3.2

    $ sg_stage_demo_i = 0
    while sg_stage_demo_i < len(sg_stage_demo_list):
        $ sg_stage_demo_go(*sg_stage_demo_list[sg_stage_demo_i][:2], fx=sg_stage_demo_list[sg_stage_demo_i][2])
        $ renpy.pause(sg_stage_demo_list[sg_stage_demo_i][3])
        $ sg_stage_demo_i += 1

    $ sg_clear_fx()
    $ sg_stage_demo_end("great")
    pause 3.0
    $ sg_stage_demo_line = "끝. 클릭하면 첫 화면으로 돌아간다"
    pause
    hide screen sg_stage_demo_say
    return


## 자동 시험이 쓰는 무대. 배경만 깔고 기다린다.
label sg_stage_demo_stage:
    $ sg_stage_demo_setup()
    while True:
        pause


################################################################################
## 자동 시험. 동작 도중과 기호가 뜬 순간의 캡처를 찍는다.
################################################################################

testsuite sg_stage_demo:

    setup:
        ## 이 게임은 주 메뉴 없이 곧장 고르기 화면(서버가 없으면 오류 안내)으로 들어간다.
        ## 이미 게임 안이므로 Start 가 아니라 Jump 로 시험장에 간다
        run Jump("sg_stage_demo_stage")
        pause 1.0
        screenshot "stage_00_empty.png"

    teardown:
        exit

    ## 등장: 아래에서 올라오며 나타나고 장소 제목 카드가 떴다가 사라진다
    testcase enter:
        $ sg_stage_demo_go("neutral", 0, first=True)
        pause 0.3
        screenshot "stage_01_enter_rising.png"
        pause 1.0
        assert screen "sg_stage_title"
        screenshot "stage_02_enter_title.png"
        pause 2.6
        assert not screen "sg_stage_title"
        assert eval (sg_stage_demo_emotes() == 0)
        screenshot "stage_03_standing.png"

    testcase smile:
        $ sg_stage_demo_go("smile", 7)
        pause 0.16
        screenshot "stage_04_smile_hop.png"
        pause 0.55
        assert eval (sg_stage_demo_emotes() == 2)
        screenshot "stage_05_smile_emote.png"
        pause 1.6

    ## 크게 올랐다: 김과 떠오르는 하트 여러 개
    testcase blush:
        $ sg_stage_demo_go("blush", 14)
        pause 0.2
        screenshot "stage_06_blush_flinch.png"
        pause 0.75
        assert eval (sg_stage_demo_emotes() == 4)
        screenshot "stage_07_blush_hearts.png"
        pause 1.6

    testcase pout:
        $ sg_stage_demo_go("pout", -7)
        pause 0.2
        screenshot "stage_08_pout_tilt.png"
        pause 0.55
        screenshot "stage_09_pout_emote.png"
        pause 1.6

    testcase shock:
        $ sg_stage_demo_go("shock", -14)
        pause 0.12
        screenshot "stage_10_shock_jump.png"
        pause 0.6
        screenshot "stage_11_shock_emote.png"
        pause 1.6

    testcase dark:
        $ sg_stage_demo_go("dark", -14)
        pause 1.0
        assert eval (sg_stage_demo_emotes() == 2)
        screenshot "stage_12_dark_emote.png"
        pause 2.0

    testcase neutral:
        $ sg_stage_demo_go("neutral", 0)
        pause 0.7
        screenshot "stage_13_neutral_emote.png"
        pause 1.4
        $ sg_stage_demo_go("neutral", -7)
        pause 0.7
        screenshot "stage_14_neutral_sweat.png"
        pause 1.4

    ## 같은 표정이 이어지면 동작(sg_stage_act_smile)을 되풀이하지 않는다
    testcase same_face:
        $ sg_stage_demo_go("smile", 14)
        pause 0.75
        screenshot "stage_15_smile_big.png"
        pause 1.6
        $ sg_stage_demo_go("smile", 7)
        pause 0.16
        screenshot "stage_16_same_face_no_hop.png"
        pause 0.6
        assert eval (sg_stage_demo_emotes() == 2)
        pause 1.4

    ## 기호 고르기의 규칙
    testcase pick:
        assert eval ([ e[0] for e in sg_stage_pick_emotes("blush", 21) ] == [ "steam", "heart", "heart", "heart" ])
        assert eval ([ e[0] for e in sg_stage_pick_emotes("pout", -7) ] == [ "vein", "steam" ])
        assert eval ([ e[0] for e in sg_stage_pick_emotes("shock", -14) ] == [ "exclaim", "sweat" ])
        assert eval ([ e[0] for e in sg_stage_pick_emotes("dark", -7) ] == [ "gloom" ])
        assert eval ([ e[0] for e in sg_stage_pick_emotes("neutral", -21) ] == [ "sweat", "gloom" ])
        assert eval (sg_stage_pick_emotes("neutral", 0, first=True) == [ ])
        assert eval ([ e[0] for e in sg_stage_pick_emotes("smile", 7, fallback=True) ] == [ "dots" ])
        ## 모르는 표정과 이상한 값도 오류를 내지 않는다
        assert eval (sg_stage_pick_emotes("없는 표정", 0, first=True) == [ ])
        assert eval (len(set(e[1] for e in sg_stage_pick_emotes("smile", 21))) == len(sg_stage_pick_emotes("smile", 21)))

    ## 연출과 함께: 줌인과 흔들림은 master 레이어 자리에 걸리고, 스탠딩과 기호는 그 안에서 같이 움직인다
    testcase with_fx:
        $ sg_stage_demo_go("shock", 0, fx=[ "줌인", "집중선" ])
        pause 0.6
        assert eval (not sg_stage_demo_layer_free())
        screenshot "stage_17_shock_zoom_fx.png"
        pause 2.2
        $ sg_stage_demo_go("pout", -7, fx=[ "흔들림" ])
        pause 0.5
        screenshot "stage_18_pout_shake_fx.png"
        pause 2.0
        $ sg_clear_fx()
        pause 0.3
        assert eval sg_stage_demo_layer_free()
        screenshot "stage_19_after_fx.png"

    ## 엔딩 자리: 왼쪽으로 비켜서고 기호도 따라간다
    testcase ending:
        $ sg_stage_demo_end("great")
        pause 1.5
        screenshot "stage_20_ending_left.png"
        pause 1.5
        ## 판이 바뀌면 기호와 표정 기억이 지워진다
        $ sg_stage_demo_setup()
        pause 0.4
        assert eval (sg_stage_demo_emotes() == 0)
        assert eval (sg_stage_face is None)
        assert eval sg_stage_demo_layer_free()

## sg_fx_demo.rpy: 연출 시험장. 개발용이고 게임 본편에서는 부르지 않는다.
##
## 자리표시 배경과 스탠딩(도형으로 그린 단순한 그림)을 master 에 올리고, 가짜 대사창을
## screens 에 띄운 뒤 sg_fx.rpy 의 연출을 하나씩 튼다.
##
##   사람이 볼 때  게임을 켜고 Shift+O 콘솔에서 "jump sg_fx_demo". 클릭하면 다음 연출로 넘어간다
##   자동 시험     RENPY_SDK=... renpy/dev/rtest.sh sg_fx_demo
##                 캡처가 renpy/tests/screenshots/fx_*.png 로 남는다. 서버는 필요 없다

define sg_fx_demo_narration = "그때, 급식실의 불이 꺼졌다."

## 모델이 쓴 지문에 Ren'Py 가 특별하게 읽는 글자가 섞여 온 경우
define sg_fx_demo_nasty = "[없는_변수] {b}굵게{/b} {{ 100% [[ } 도 글자 그대로 나온다"

## 가짜 대사창에 띄울 글
default sg_fx_demo_line = ""

## sg_fx_demo_click 이 몇째 줄까지 넘어갔는지
default sg_fx_demo_step = 0

## sg_fx_demo 가 끝까지 돌았는지
default sg_fx_demo_done = False

init python:

    class SgFxDemoArt(renpy.Displayable):
        """자리표시 그림. 교실 배경("bg")과 스탠딩("girl")을 도형으로 그린다."""

        def __init__(self, kind, **properties):
            super(SgFxDemoArt, self).__init__(**properties)
            self.kind = kind

        def render(self, width, height, st, at):
            if self.kind == "bg":
                rv = renpy.Render(1280, 720)
                c = rv.canvas()
                c.rect((244, 236, 214, 255), (0, 0, 1280, 720))
                c.rect((222, 204, 170, 255), (0, 380, 1280, 180))
                c.rect((176, 132, 92, 255), (0, 560, 1280, 160))
                for x in range(0, 1280, 160):
                    c.rect((150, 108, 72, 255), (x, 560, 4, 160))
                ## 창문과 해
                c.rect((255, 255, 255, 255), (60, 70, 360, 290))
                c.rect((150, 210, 245, 255), (72, 82, 336, 266))
                c.circle((255, 214, 90, 255), (330, 150), 36)
                c.rect((255, 255, 255, 255), (234, 82, 12, 266))
                c.rect((255, 255, 255, 255), (72, 209, 336, 12))
                ## 칠판
                c.rect((150, 104, 60, 255), (880, 90, 340, 230))
                c.rect((46, 110, 86, 255), (892, 102, 316, 206))
                c.rect((235, 240, 235, 255), (920, 140, 180, 8))
                c.rect((235, 240, 235, 255), (920, 180, 240, 8))
                c.rect((235, 240, 235, 255), (920, 220, 120, 8))
                ## 사물함. 색이 여럿이라 흑백과 화면 깨짐이 잘 보인다
                colors = [(226, 59, 78), (255, 230, 90), (64, 132, 214), (72, 176, 110), (232, 85, 45), (140, 96, 200)]
                for i in range(6):
                    c.rect(colors[i] + (255,), (40 + i * 62, 400, 56, 150))
                    c.rect(colors[5 - i] + (255,), (868 + i * 62, 400, 56, 150))
                return rv

            rv = renpy.Render(420, 640)
            c = rv.canvas()
            hair = (92, 58, 40, 255)
            skin = (255, 222, 196, 255)
            c.circle(hair, (210, 140), 112)
            c.rect(hair, (98, 140, 224, 230))
            c.polygon((232, 85, 45, 255), [(60, 640), (80, 380), (150, 330), (270, 330), (340, 380), (360, 640)])
            c.polygon((255, 255, 255, 255), [(170, 330), (250, 330), (210, 420)])
            c.rect((226, 59, 78, 255), (198, 350, 24, 16))
            c.rect(skin, (185, 230, 50, 110))
            c.circle(skin, (210, 140), 96)
            c.polygon(hair, [(114, 140), (118, 80), (160, 44), (210, 36), (260, 44), (302, 80),
                             (306, 140), (270, 100), (210, 92), (150, 100)])
            c.circle((40, 36, 60, 255), (172, 150), 11)
            c.circle((40, 36, 60, 255), (248, 150), 11)
            c.circle((255, 255, 255, 255), (176, 146), 4)
            c.circle((255, 255, 255, 255), (252, 146), 4)
            c.circle((255, 170, 170, 255), (150, 182), 12)
            c.circle((255, 170, 170, 255), (270, 182), 12)
            c.rect((180, 80, 80, 255), (196, 192, 28, 6))
            return rv

    class SgFxBox(renpy.Displayable):
        """각진 상자. 테두리(edges: 왼쪽, 위, 오른쪽, 아래 두께)와 속을 단색으로 그린다. 가짜 대사창의 바탕이다."""

        def __init__(self, fill, line, edges=(4, 4, 4, 4), **properties):
            super(SgFxBox, self).__init__(**properties)
            self.fill = Solid(fill)
            self.line = Solid(line)
            self.edges = edges

        def render(self, width, height, st, at):
            width = int(width)
            height = int(height)
            left, top, right, bottom = self.edges
            rv = renpy.Render(width, height)
            rv.blit(renpy.render(self.line, width, height, st, at), (0, 0))
            rv.blit(renpy.render(self.fill, max(0, width - left - right), max(0, height - top - bottom), st, at), (left, top))
            return rv

    def sg_fx_demo_show_bg(key):
        """배경을 바꾼다. 진짜 배경 그림(images/bg/<key>.jpg)이 있으면 그것을, 없으면 도형으로 그린 교실을 쓴다."""
        path = "images/bg/%s.jpg" % key
        if renpy.loadable(path):
            renpy.show("sg_fx_demo_bg", what=renpy.displayable(path))
        else:
            renpy.show("sg_fx_demo_bg")
        renpy.restart_interaction()

    def sg_fx_demo_setup():
        """
        무대를 차린다: 배경과 스탠딩은 master 에, 가짜 대사창은 screens 에.
        진짜 그림이 있으면 그것을 쓴다. 도형 무대에서는 연출의 느낌을 가늠하기 어렵다.
        """
        ## 본편이 띄워 둔 무대와 화면을 걷고 시작한다
        sg_fx_clear()
        renpy.scene()
        renpy.scene("screens")
        renpy.show_layer_at([], layer="master")
        sg_fx_demo_show_bg("rooftop")

        ## 스탠딩: 진짜 그림, 자리표시 그림, 도형 순으로 찾는다
        found = None
        for folder in ("images/sprites/", "images/placeholder/sprites/"):
            names = sorted(f for f in renpy.list_files() if f.startswith(folder) and f.endswith("/neutral.png"))
            if names:
                found = names[0]
                break
        if found:
            height = renpy.image_size(found)[1]
            renpy.show("sg_fx_demo_girl", what=Transform(found, zoom=690.0 / height),
                       at_list=[Transform(xalign=0.5, yalign=1.0)])
        else:
            renpy.show("sg_fx_demo_girl", at_list=[Transform(xalign=0.5, yalign=1.0)])
        renpy.show_screen("sg_fx_demo_say")

    def sg_fx_demo_go(names, narration=None, line=None, expect=True):
        """가짜 대사창에 이름을 적고 연출을 건다. 걸린 것이 없으면 시험이 실패하게 오류를 낸다."""
        store.sg_fx_demo_line = line or ("연출: " + " + ".join(str(n) for n in names))
        sg_fx_play(names, sg_fx_demo_narration if narration is None else narration)
        renpy.restart_interaction()
        if expect and sg_fx_demo_clean():
            raise Exception("연출이 걸리지 않았다: %r" % (names,))

    def sg_fx_demo_rest():
        """가짜 대사창의 글을 처음 것으로 돌린다. 연출 전과 후의 캡처를 견주려는 것이다."""
        store.sg_fx_demo_line = "연출 없음"
        renpy.restart_interaction()

    def sg_fx_demo_clean():
        """걸린 것이 하나도 없으면 True: sg_fx 레이어가 비었고 master 에 건 transform 도 없다."""
        sls = renpy.display.scenelists.scene_lists()
        return (not sls.layers["sg_fx"]) and (not sls.layer_at_list["master"][1])

    def sg_fx_demo_save_all():
        """연출이 걸린 채로 저장해도 오류가 없는지 본다. 연출마다 걸고 바로 저장한다."""
        renpy.take_screenshot()
        for name in sg_fx_table:
            sg_fx_play([name], sg_fx_demo_narration)
            renpy.save("sg_fx_demo_test")
        sg_fx_clear()
        renpy.unlink_save("sg_fx_demo_test")

    ## 사람이 볼 때의 차례: (이름 목록, 다음으로 넘어가기 전에 기다리는 시간)
    sg_fx_demo_list = [
        (["꽃잎"], 3.6), (["반짝이"], 3.1), (["집중선"], 2.1), (["줌인"], 2.0), (["자막"], 3.5), (["하트"], 3.5),
        (["흔들림"], 1.5), (["암전"], 2.9), (["붉은 화면"], 2.9), (["흑백"], 3.3), (["비"], 4.1), (["번개"], 2.2),
        (["스포트라이트"], 3.7), (["화면 깨짐"], 2.2), (["가짜 오류창"], 4.6),
        (["꽃잎", "하트"], 3.6), (["흔들림", "흑백"], 3.3), (["줌인", "집중선"], 2.1),
        (["암전", "스포트라이트"], 3.7), (["화면 깨짐", "흑백"], 3.3), (["자막", "가짜 오류창"], 4.6),
    ]


image sg_fx_demo_bg = SgFxDemoArt("bg")
image sg_fx_demo_girl = SgFxDemoArt("girl")


## 가짜 대사창. 진짜 대사창과 같은 자리(아래 185픽셀)에, screens 레이어에 뜬다.
screen sg_fx_demo_say():
    frame:
        style "sg_fx_frame"
        background SgFxBox("#FFFFFF", sg_fx_ink, (0, 4, 0, 0))
        xfill True
        ysize 185
        yalign 1.0
        padding (268, 28, 268, 20)
        vbox:
            spacing 10
            text "시험장" font "fonts/Pretendard-Bold.otf" size 30 color sg_fx_ink
            text sg_fx_demo_line font "fonts/Pretendard-Regular.otf" size 22 color sg_fx_ink substitute False


## 사람이 보는 시험장. 연출을 차례로 틀고, 마지막에 sg_fx_clear 를 시험한다.
label sg_fx_demo:
    $ sg_fx_demo_setup()
    $ sg_fx_demo_i = 0
    while sg_fx_demo_i < len(sg_fx_demo_list):
        $ sg_fx_demo_go(sg_fx_demo_list[sg_fx_demo_i][0])
        $ renpy.pause(sg_fx_demo_list[sg_fx_demo_i][1])
        $ sg_fx_demo_i += 1

    $ sg_fx_demo_go(["비", "흑백", "흔들림"], line="sg_fx_clear: 비, 흑백, 흔들림을 걸고 0.5초 뒤에 전부 걷는다")
    $ renpy.pause(0.5, hard=True)
    $ sg_fx_clear()
    pause 1.5

    $ sg_fx_demo_done = True
    $ sg_fx_demo_line = "끝. 클릭하면 연출 없는 무대로 돌아간다"
    pause
    jump sg_fx_demo_stage


## 자동 시험이 쓰는 무대. 연출 없이 서서 기다린다.
label sg_fx_demo_stage:
    $ sg_fx_demo_setup()
    $ sg_fx_demo_line = "연출 없음"
    while True:
        pause


## 진짜 대사창으로 확인한다: 연출이 떠 있어도 클릭하면 대사가 넘어간다.
label sg_fx_demo_click:
    $ sg_fx_demo_setup()
    hide screen sg_fx_demo_say
    $ sg_fx_demo_step = 0
    $ sg_fx_play(["가짜 오류창", "꽃잎"], sg_fx_demo_narration)
    "첫째 줄. 연출이 떠 있어도 클릭하면 넘어가야 한다."
    $ sg_fx_demo_step = 1
    "둘째 줄."
    $ sg_fx_demo_step = 2
    "셋째 줄."
    $ sg_fx_demo_step = 3
    jump sg_fx_demo_stage


################################################################################
## 자동 시험. 연출마다 재생 도중의 캡처를 찍고, 끝난 뒤 화면이 원래대로인지 본다.
################################################################################

testsuite sg_fx_demo:

    setup:
        ## 게임은 주 메뉴 없이 곧장 본편으로 들어간다. 거기서 시험 무대로 건너뛴다
        run Jump("sg_fx_demo_stage")
        pause 1.0
        screenshot "fx_00_before.png"

    before testcase:
        $ sg_fx_clear()
        $ sg_fx_demo_rest()
        pause 0.3

    teardown:
        exit

    testcase petals:
        $ sg_fx_demo_go(["꽃잎"])
        pause 1.2
        screenshot "fx_01_petals.png"
        pause 2.2
        assert eval sg_fx_demo_clean()
        $ sg_fx_demo_rest()
        pause 0.3
        screenshot "fx_01_petals_after.png"

    testcase sparks:
        $ sg_fx_demo_go(["반짝이"])
        pause 1.0
        screenshot "fx_02_sparks.png"
        pause 1.9
        assert eval sg_fx_demo_clean()

    testcase lines:
        $ sg_fx_demo_go(["집중선"])
        pause 0.4
        screenshot "fx_03_lines.png"
        pause 1.5
        assert eval sg_fx_demo_clean()

    testcase zoom:
        $ sg_fx_demo_go(["줌인"])
        pause 0.05
        screenshot "fx_04_zoom_a.png"
        pause 0.5
        screenshot "fx_04_zoom_b.png"
        pause 1.3
        assert eval sg_fx_demo_clean()
        $ sg_fx_demo_rest()
        pause 0.3
        screenshot "fx_04_zoom_after.png"

    testcase caption:
        $ sg_fx_demo_go(["자막"])
        pause 1.0
        screenshot "fx_05_caption.png"
        pause 2.3
        assert eval sg_fx_demo_clean()

    testcase caption_nasty:
        $ sg_fx_demo_go(["자막"], sg_fx_demo_nasty, "연출: 자막 (특별한 글자가 섞인 지문)")
        pause 1.0
        screenshot "fx_05_caption_nasty.png"
        pause 2.3
        assert eval sg_fx_demo_clean()

    testcase caption_long:
        $ sg_fx_demo_go(["자막"], "그때, 급식실의 불이 꺼졌다. 누군가 식판을 떨어뜨렸고, 그 소리가 복도 끝까지 울렸다. 아스트라는 아무 말도 하지 않았다. 지구는 계속 돌고 있었다.", "연출: 자막 (긴 지문)")
        pause 1.0
        screenshot "fx_05_caption_long.png"
        pause 2.3
        assert eval sg_fx_demo_clean()

    testcase caption_empty:
        $ sg_fx_demo_go(["자막"], "", "연출: 자막 (지문이 없으면 아무 일도 없다)", expect=False)
        pause 0.3
        assert eval sg_fx_demo_clean()

    testcase hearts:
        $ sg_fx_demo_go(["하트"])
        pause 1.3
        screenshot "fx_06_hearts.png"
        pause 2.0
        assert eval sg_fx_demo_clean()

    testcase shake:
        $ sg_fx_demo_go(["흔들림"])
        screenshot "fx_07_shake_a.png"
        screenshot "fx_07_shake_b.png"
        screenshot "fx_07_shake_c.png"
        pause 1.2
        assert eval sg_fx_demo_clean()
        $ sg_fx_demo_rest()
        pause 0.3
        screenshot "fx_07_shake_after.png"

    testcase blackout:
        $ sg_fx_demo_go(["암전"])
        pause 0.15
        screenshot "fx_08_blackout_a.png"
        pause 0.8
        screenshot "fx_08_blackout_b.png"
        pause 1.8
        assert eval sg_fx_demo_clean()

    testcase red:
        $ sg_fx_demo_go(["붉은 화면"])
        pause 0.25
        screenshot "fx_09_red_a.png"
        pause 0.2
        screenshot "fx_09_red_b.png"
        pause 2.3
        assert eval sg_fx_demo_clean()

    testcase mono:
        $ sg_fx_demo_go(["흑백"])
        pause 1.0
        screenshot "fx_10_mono.png"
        pause 2.1
        assert eval sg_fx_demo_clean()
        $ sg_fx_demo_rest()
        pause 0.3
        screenshot "fx_10_mono_after.png"

    testcase rain:
        $ sg_fx_demo_go(["비"])
        pause 1.0
        screenshot "fx_11_rain.png"
        pause 2.9
        assert eval sg_fx_demo_clean()

    testcase bolt:
        $ sg_fx_demo_go(["번개"])
        screenshot "fx_12_bolt_a.png"
        pause 0.4
        screenshot "fx_12_bolt_b.png"
        pause 1.6
        assert eval sg_fx_demo_clean()

    testcase spot:
        $ sg_fx_demo_go(["스포트라이트"])
        pause 0.05
        screenshot "fx_13_spot_a.png"
        pause 1.2
        screenshot "fx_13_spot_b.png"
        pause 2.3
        assert eval sg_fx_demo_clean()

    testcase glitch:
        $ sg_fx_demo_go(["화면 깨짐"])
        screenshot "fx_14_glitch_a.png"
        pause 0.3
        screenshot "fx_14_glitch_b.png"
        pause 1.7
        assert eval sg_fx_demo_clean()
        $ sg_fx_demo_rest()
        pause 0.3
        screenshot "fx_14_glitch_after.png"

    testcase err:
        $ sg_fx_demo_go(["가짜 오류창"])
        pause 1.0
        screenshot "fx_15_err.png"
        pause 3.4
        assert eval sg_fx_demo_clean()

    testcase err_default:
        $ sg_fx_demo_go(["가짜 오류창"], "", "연출: 가짜 오류창 (지문이 없을 때)")
        pause 1.0
        screenshot "fx_15_err_default.png"

    testcase err_nasty:
        $ sg_fx_demo_go(["가짜 오류창"], sg_fx_demo_nasty + " 그리고 글이 길어지면 창이 아래로 늘어난다. 여섯 줄을 넘으면 잘린다.", "연출: 가짜 오류창 (특별한 글자가 섞인 긴 지문)")
        pause 1.0
        screenshot "fx_15_err_nasty.png"

    testcase err_ok_button:
        ## "확인" 을 누르면 그 창만 닫힌다
        $ sg_fx_demo_go(["가짜 오류창"])
        pause 0.6
        click "확인"
        pause 0.3
        assert eval sg_fx_demo_clean()

    testcase pair_petals_hearts:
        $ sg_fx_demo_go(["꽃잎", "하트"])
        pause 1.3
        screenshot "fx_20_pair_petals_hearts.png"
        pause 2.1
        assert eval sg_fx_demo_clean()

    testcase pair_shake_mono:
        $ sg_fx_demo_go(["흔들림", "흑백"])
        screenshot "fx_21_pair_shake_mono_a.png"
        pause 1.0
        ## 흔들림은 끝났고 흑백은 이어진다
        screenshot "fx_21_pair_shake_mono_b.png"
        pause 2.0
        assert eval sg_fx_demo_clean()
        $ sg_fx_demo_rest()
        pause 0.3
        screenshot "fx_21_pair_shake_mono_after.png"

    testcase pair_zoom_lines:
        $ sg_fx_demo_go(["줌인", "집중선"])
        pause 0.6
        screenshot "fx_22_pair_zoom_lines.png"
        pause 1.3
        assert eval sg_fx_demo_clean()

    testcase pair_blackout_spot:
        $ sg_fx_demo_go(["암전", "스포트라이트"])
        pause 1.0
        screenshot "fx_23_pair_blackout_spot.png"
        pause 2.5
        assert eval sg_fx_demo_clean()

    testcase pair_glitch_mono:
        $ sg_fx_demo_go(["화면 깨짐", "흑백"])
        screenshot "fx_24_pair_glitch_mono.png"
        pause 3.0
        assert eval sg_fx_demo_clean()

    testcase pair_caption_err:
        $ sg_fx_demo_go(["자막", "가짜 오류창"])
        pause 1.0
        screenshot "fx_25_pair_caption_err.png"
        pause 3.4
        assert eval sg_fx_demo_clean()

    testcase replay:
        ## 같은 연출을 다시 걸면 처음부터 다시 재생한다: 불빛이 다시 헛짚는 자리에 있어야 한다
        $ sg_fx_demo_go(["스포트라이트"])
        pause 1.2
        $ sg_fx_demo_go(["스포트라이트"], line="연출: 스포트라이트 (1.2초 뒤에 다시 건 직후)")
        pause 0.05
        screenshot "fx_30_replay.png"

    testcase twice:
        ## 끝난 연출을 다시 걸어도 다시 제 수명에 끝난다
        $ sg_fx_demo_go(["흔들림", "붉은 화면"])
        pause 2.7
        assert eval sg_fx_demo_clean()
        $ sg_fx_demo_go(["흔들림", "붉은 화면"])
        pause 2.7
        assert eval sg_fx_demo_clean()
        ## 도중에 다시 걸면 그때부터 다시 제 수명만큼 간다
        $ sg_fx_demo_go(["흑백"])
        pause 1.5
        $ sg_fx_demo_go(["흑백"])
        pause 1.5
        assert eval (not sg_fx_demo_clean())
        pause 1.6
        assert eval sg_fx_demo_clean()

    testcase clear:
        $ sg_fx_demo_go(["비", "흑백"], line="sg_fx_clear 직전: 비 + 흑백")
        pause 0.5
        screenshot "fx_31_clear_before.png"
        $ sg_fx_clear()
        $ sg_fx_demo_rest()
        assert eval sg_fx_demo_clean()
        pause 0.3
        screenshot "fx_31_clear_after.png"

    testcase unknown:
        ## 모르는 이름과 엉뚱한 값은 조용히 무시한다
        $ sg_fx_play(["없는 연출", 3, None], "지문")
        $ sg_fx_play(None)
        $ sg_fx_play([])
        $ sg_fx_play(7)
        pause 0.2
        assert eval sg_fx_demo_clean()
        ## 이름 하나를 글자 그대로 줘도 받는다. 모르는 이름은 빼고 아는 것만 튼다
        $ sg_fx_play("하트")
        assert eval (renpy.get_screen("sg_fx_hearts", layer="sg_fx") is not None)
        $ sg_fx_play(["없는 연출", "하트", "하트"], "지문")
        assert eval (renpy.get_screen("sg_fx_hearts", layer="sg_fx") is not None)
        $ sg_fx_clear()
        assert eval sg_fx_demo_clean()
        ## 서버 응답(JSON)에서 꺼낸 목록과 튜플도 받는다
        $ sg_fx_play(__import__("json").loads('{"fx": ["비", "없는 연출"]}')["fx"], "지문")
        assert eval (renpy.get_screen("sg_fx_rain", layer="sg_fx") is not None)
        $ sg_fx_play(("반짝이",))
        assert eval (renpy.get_screen("sg_fx_sparks", layer="sg_fx") is not None)
        assert eval (renpy.get_screen("sg_fx_rain", layer="sg_fx") is None)
        $ sg_fx_clear()
        assert eval sg_fx_demo_clean()

    testcase dark_background:
        ## 어두운 배경(도서관)에서도 잘 보이는지 본다. 진짜 배경 그림이 없으면 도형 무대 그대로 찍힌다
        $ sg_fx_demo_show_bg("library")
        $ sg_fx_demo_go(["꽃잎", "반짝이"], line="어두운 배경: 꽃잎 + 반짝이")
        pause 1.2
        screenshot "fx_40_dark_petals_sparks.png"
        $ sg_fx_demo_go(["비", "하트"], line="어두운 배경: 비 + 하트")
        pause 1.2
        screenshot "fx_41_dark_rain_hearts.png"
        $ sg_fx_demo_go(["자막", "집중선"], line="어두운 배경: 자막 + 집중선")
        pause 0.9
        screenshot "fx_42_dark_caption_lines.png"
        $ sg_fx_clear()
        $ sg_fx_demo_show_bg("rooftop")
        pause 0.3
        assert eval sg_fx_demo_clean()

    testcase save_while_playing:
        ## 연출이 걸린 채로 저장해도 오류가 없다
        $ sg_fx_demo_save_all()
        pause 0.2
        assert eval sg_fx_demo_clean()

    testcase click_through:
        ## 진짜 대사창: 연출(가짜 오류창, 꽃잎)이 떠 있어도 클릭 한 번에 한 줄씩 넘어간다
        run Jump("sg_fx_demo_click")
        pause 0.8
        assert eval (sg_fx_demo_step == 0)
        screenshot "fx_32_click_a.png"
        click pos (200, 300)
        pause 0.3
        assert eval (sg_fx_demo_step == 1)
        click pos (640, 640)
        pause 0.3
        assert eval (sg_fx_demo_step == 2)
        screenshot "fx_32_click_b.png"
        click pos (1000, 200)
        pause 0.5
        assert eval (sg_fx_demo_step == 3)

    testcase walkthrough:
        ## 사람이 보는 시험장(label sg_fx_demo)이 처음부터 끝까지 오류 없이 도는지 본다.
        ## 클릭 한 번에 다음 연출로 넘어간다
        $ sg_fx_demo_done = False
        run Jump("sg_fx_demo")
        pause 0.5
        click pos (100, 400) until eval sg_fx_demo_done
        pause 1.0
        assert eval sg_fx_demo_clean()

## 소개팅 화면들.
##
##   sg_select       캐릭터 고르기
##   sg_hud          대화 중 위쪽 표시: 진행, 장소, 호감도 게이지
##   sg_talk         턴 하나: 들린 말 → 지문 → 대사 → 선택지(또는 엔딩 보기)
##   sg_wait*        서버의 답을 기다리는 동안
##   sg_error        서버 오류 안내와 다시 시도
##   sg_ending       엔딩
##
## 배경과 스탠딩은 여기서 그리지 않는다. sg_core.rpy 가 master 레이어에 올린다.
## 서버에서 온 글은 sg_core.rpy 의 sg_build_view 가 sg_esc 를 거쳐서 넘겨준다.
## 이 파일에서 서버의 글을 직접 찍는 곳(캐릭터 카드)은 sg_esc 를 불러서 쓴다.


################################################################################
## 부품
################################################################################

init -3 python:

    def sg_box(radius, color, alpha=1.0, kind=""):
        """모서리가 둥근 네모에 색을 입힌 것. 바탕(background)으로 쓴다.

        radius는 8, 14, 20, 28 가운데 하나. kind에 "_line"을 주면 테두리만 그린다.
        """
        frame = Frame("images/ui/r%d%s.png" % (radius, kind), radius, radius)
        return Transform(frame, matrixcolor=TintMatrix(color), alpha=alpha)

    def sg_panel(radius, fill, fill_alpha=1.0, line=None, line_alpha=1.0, kind="_line"):
        """바탕색 위에 테두리를 겹친 것."""
        layers = [ sg_box(radius, fill, fill_alpha) ]
        if line is not None:
            layers.append(sg_box(radius, line, line_alpha, kind))
        return Fixed(*layers)

    def sg_icon(name, size, color, alpha=1.0):
        """images/ui 의 흰 그림에 색을 입힌 것."""
        return Transform("images/ui/%s.png" % name, xysize=(size, size),
                         matrixcolor=TintMatrix(color), alpha=alpha)

    def sg_textbox_bg(color):
        """대사창 바탕. 테두리에 캐릭터의 대표색이 돈다."""
        return sg_panel(20, "#12162e", 0.84, sg_on_dark(color), 0.9)

    def sg_nametag_bg(color):
        return sg_panel(14, color, 1.0, "#ffffff", 0.55)

    def sg_face_box(char_id, color, width, height, radius=14):
        """모서리가 둥근 얼굴 그림. 스탠딩이 없는 캐릭터면 물음표를 둔다."""
        layers = [ Solid(Color(color).tint(0.3).hexcode) ]
        portrait = sg_portrait(char_id, width, height)
        if portrait is not None:
            layers.append(portrait)
        else:
            layers.append(Text("?", size=height // 2, color="#ffffff", font=gui.name_text_font,
                               xalign=0.5, yalign=0.5))
        body = Fixed(*layers, xysize=(width, height))
        mask = Transform(Frame("images/ui/r%d.png" % radius, radius, radius), xysize=(width, height))
        return AlphaMask(body, mask)


## 대사 속 " [출처 필요]" 자리에 끼우는 딱지. 글줄 위쪽에 작게 붙는다.
image sg_cite = Fixed(
    Transform(sg_box(8, "#9fd8ff"), xysize=(84, 25), xpos=3),
    Text("출처 필요", size=16, color="#12305a", font="fonts/Pretendard-Bold.otf", xpos=45, xanchor=0.5, ypos=2),
    xysize=(92, 31))


################################################################################
## 움직임
################################################################################

## 스탠딩 자리. 그림 768x1152 를 0.7배로 줄여 세우면 머리가 화면 위쪽에 오고
## 가슴 아래는 대사창에 가린다.
transform sg_char_center:
    xpos 640 xanchor 0.5 ypos 846 yanchor 1.0 zoom 0.7

## 엔딩 화면에서는 왼쪽으로 비켜선다.
transform sg_char_left:
    xanchor 0.5 ypos 846 yanchor 1.0 zoom 0.7
    ease 0.5 xpos 250

## 통통 튀는 점. 기다리는 표시에 쓴다.
transform sg_bounce(delay=0.0):
    yoffset 0
    pause delay
    block:
        easeout 0.22 yoffset -10
        easein 0.22 yoffset 0
        pause 0.46
        repeat

## 눌러서 넘기라는 세모.
transform sg_ctc_blink:
    alpha 1.0 yoffset 0
    block:
        ease 0.5 yoffset 5 alpha 0.45
        ease 0.5 yoffset 0 alpha 1.0
        repeat

## 호감도 변화 글자가 튀어나온다.
transform sg_popup_in:
    alpha 0.0 yoffset 26 zoom 0.6
    easeout_back 0.38 alpha 1.0 yoffset 0 zoom 1.0

## 폭발하는 숫자는 잠깐 떤다.
transform sg_wild:
    xoffset 0
    block:
        linear 0.04 xoffset -5
        linear 0.04 xoffset 5
        repeat 12
    linear 0.04 xoffset 0

## 살짝 떠오르며 나타난다.
transform sg_rise(delay=0.0):
    alpha 0.0 yoffset 12
    pause delay
    easeout 0.25 alpha 1.0 yoffset 0

## 정해진 시간 뒤에 나타난다.
transform sg_after(delay):
    alpha 0.0
    pause delay
    linear 0.4 alpha 1.0

## 카드에 마우스를 올리면 살짝 들린다.
transform sg_card_lift:
    on idle:
        easein 0.12 yoffset 0
    on hover:
        easein 0.12 yoffset -8

## 엔딩 보기 단추가 천천히 숨 쉰다.
transform sg_breathe:
    zoom 1.0
    block:
        ease 0.7 zoom 1.04
        ease 0.7 zoom 1.0
        repeat


################################################################################
## 스타일
################################################################################

## 대사창 -------------------------------------------------------------------------

style sg_textbox:
    xpos 50
    ypos 536
    xysize (1180, 168)
    padding (44, 36, 44, 20)

style sg_say_text:
    font gui.interface_text_font
    size 26
    color gui.sg_paper
    line_spacing 6
    xsize 1092
    slow_abortable True
    # 투명한 테두리. 형광펜 자리에서만 색이 들어온다 (sg_core.rpy 의 SG_HL_OPEN)
    outlines [ (absolute(4), "#00000000", absolute(0), absolute(0)) ]

style sg_narration_text:
    font gui.text_font
    size 24
    color "#d5daf5"
    line_spacing 6
    xsize 1092
    slow_abortable True

style sg_nametag:
    padding (22, 7, 22, 8)
    ysize 44

style sg_nametag_text:
    font gui.name_text_font
    size 24
    color "#ffffff"
    yalign 0.5

style sg_tagnote:
    padding (14, 6, 14, 6)
    yalign 0.5
    background sg_box(14, "#12162e", 0.84)

style sg_tagnote_text:
    font gui.interface_text_font
    size 16
    color gui.sg_yellow

style sg_hint_text:
    font gui.text_font
    size 16
    color gui.sg_paper_soft

## 위쪽 표시 -----------------------------------------------------------------------

style sg_pill:
    padding (16, 7, 16, 7)
    ysize 40
    background sg_box(20, "#12162e", 0.78)

style sg_pill_text:
    font gui.interface_text_font
    size 18
    color gui.sg_paper
    yalign 0.5

style sg_pill_num is sg_pill_text:
    font gui.name_text_font
    size 22
    min_width 38
    textalign 1.0

style sg_ghost_button:
    padding (14, 7, 14, 7)
    ysize 40
    background sg_box(20, "#12162e", 0.45)
    hover_background sg_box(20, "#12162e", 0.9)
    keyboard_focus False

style sg_ghost_button_text:
    font gui.interface_text_font
    size 16
    color gui.sg_paper_soft
    hover_color "#ffffff"
    yalign 0.5

style sg_gauge:
    xysize (180, 16)
    yalign 0.5
    left_bar sg_box(8, gui.sg_pink)
    right_bar sg_box(8, "#ffffff", 0.3)

## 호감도 변화 ---------------------------------------------------------------------

style sg_popup_text:
    font gui.name_text_font
    outlines [ (absolute(7), "#171b3638", absolute(0), absolute(2)), (absolute(4), "#ffffff", absolute(0), absolute(0)) ]
    xalign 1.0

style sg_chip:
    padding (14, 6, 14, 7)
    xalign 1.0
    background sg_box(14, "#12162e", 0.8)

style sg_chip_text:
    font gui.interface_text_font
    size 17
    color gui.sg_paper
    xmaximum 262

style sg_note:
    padding (14, 6, 14, 7)
    xalign 1.0
    background sg_panel(14, gui.sg_yellow, 0.96, gui.sg_ink, 0.9)

style sg_note_text:
    font gui.name_text_font
    size 17
    color gui.sg_ink
    xmaximum 262

## 속마음 풍선 ---------------------------------------------------------------------

style sg_bubble:
    xpos 30
    ypos 126
    xsize 290
    padding (18, 12, 18, 16)
    background sg_box(20, "#ffffff", 0.95)

style sg_bubble_label:
    font gui.name_text_font
    size 14

style sg_bubble_text:
    font gui.interface_text_font
    size 19
    color gui.sg_ink
    line_spacing 4
    xsize 254

## 선택지와 직접 말하기 --------------------------------------------------------------

style sg_choice:
    xsize 600
    yminimum 52
    padding (26, 11, 26, 12)
    background sg_panel(14, "#12162e", 0.8, "#ffffff", 0.3)
    hover_background sg_panel(14, "#2c3468", 0.95, "#ffffff", 0.95)

style sg_choice_text:
    font gui.interface_text_font
    size 21
    color gui.sg_paper
    hover_color "#ffffff"
    xalign 0.5
    textalign 0.5
    yalign 0.5

style sg_input_box:
    xsize 600
    padding (20, 10, 12, 10)
    background sg_panel(14, "#ffffff", 0.95, "#ffffff", 1.0)

style sg_input:
    font gui.interface_text_font
    size 20
    color gui.sg_ink
    caret Solid("#ff5c8a", xysize=(2, 24))
    xmaximum 452
    adjust_spacing False

style sg_placeholder_text:
    font gui.interface_text_font
    size 20
    color "#8f96b8"

style sg_counter_text:
    font gui.text_font
    size 13
    color "#8f96b8"
    xalign 1.0

style sg_send:
    xysize (92, 36)
    xalign 1.0
    background sg_box(14, gui.sg_pink)
    hover_background sg_box(14, "#ff3d75")
    insensitive_background sg_box(14, "#c5c9dc")

style sg_send_text:
    font gui.name_text_font
    size 17
    color "#ffffff"
    xalign 0.5
    yalign 0.5

## 큰 단추 -----------------------------------------------------------------------

style sg_primary:
    padding (30, 13, 30, 14)
    background sg_panel(20, gui.sg_pink, 1.0, "#ffffff", 0.9)
    hover_background sg_panel(20, "#ff3d75", 1.0, "#ffffff", 1.0)

style sg_primary_text:
    font gui.name_text_font
    size 22
    color "#ffffff"
    xalign 0.5
    yalign 0.5

style sg_secondary:
    padding (26, 13, 26, 14)
    background sg_panel(20, "#ffffff", 1.0, "#171b36", 0.25)
    hover_background sg_panel(20, "#eef0ff", 1.0, "#171b36", 0.8)

style sg_secondary_text:
    font gui.name_text_font
    size 20
    color gui.sg_ink
    xalign 0.5
    yalign 0.5

## 가운데 창 (기다림, 오류, 확인) ------------------------------------------------------

style sg_modal_panel:
    xalign 0.5
    yalign 0.5
    padding (44, 34, 44, 34)
    background sg_panel(20, "#ffffff", 0.98, "#171b36", 0.12)

style sg_modal_title:
    font gui.name_text_font
    size 26
    color gui.sg_ink
    xalign 0.5

style sg_modal_text:
    font gui.interface_text_font
    size 20
    color gui.sg_ink
    xalign 0.5
    textalign 0.5
    line_spacing 6

style sg_modal_sub:
    font gui.text_font
    size 16
    color gui.sg_ink_soft
    xalign 0.5
    textalign 0.5

## 고르기 화면 ---------------------------------------------------------------------

style sg_title:
    font gui.name_text_font
    size 46
    color gui.sg_ink
    xalign 0.5

style sg_lead:
    font gui.interface_text_font
    size 21
    color gui.sg_ink_soft
    xalign 0.5

style sg_foot:
    font gui.text_font
    size 15
    color gui.sg_ink_soft

style sg_card:
    xysize (190, 446)
    padding (12, 12, 12, 12)
    background sg_panel(20, "#ffffff", 0.97, "#171b36", 0.1)

style sg_card_name:
    font gui.name_text_font
    size 26
    color gui.sg_ink

style sg_card_attr:
    font gui.name_text_font
    size 15

style sg_card_motif:
    font gui.interface_text_font
    size 14
    color gui.sg_ink_soft

style sg_card_intro:
    font gui.text_font
    size 15
    color "#3b4266"
    line_spacing 4
    xsize 166

## 엔딩 화면 ----------------------------------------------------------------------

style sg_end_card:
    xpos 500
    ypos 30
    xysize (748, 660)
    padding (44, 32, 44, 30)
    background sg_panel(20, "#ffffff", 0.96, "#171b36", 0.1)

style sg_end_kind:
    font gui.interface_text_font
    size 17
    color gui.sg_ink_soft

style sg_end_band:
    font gui.name_text_font
    size 24
    color "#ffffff"

style sg_end_title:
    font gui.name_text_font
    size 36
    color gui.sg_ink
    xsize 660

style sg_end_text:
    font gui.interface_text_font
    size 20
    color "#2b3156"
    line_spacing 6
    xsize 660

style sg_end_label:
    font gui.name_text_font
    size 15
    color gui.sg_ink_soft

style sg_end_score:
    font gui.name_text_font
    size 46
    color gui.sg_pink

style sg_end_nick:
    font gui.name_text_font
    size 22
    color gui.sg_ink

style sg_reveal_label:
    font gui.name_text_font
    size 15
    color "#ffffff"
    xalign 0.5
    yalign 0.5

style sg_reveal_masked:
    font gui.text_font
    size 16
    color "#8f96b8"
    xsize 730

style sg_reveal_text:
    font gui.interface_text_font
    size 19
    color gui.sg_ink
    line_spacing 4
    xsize 730


################################################################################
## 고르기 화면
################################################################################

screen sg_select(cards):

    ## 배경을 뿌옇게 덮어서 카드가 또렷이 보이게 한다.
    add Solid("#f1f4ffcc")

    vbox:
        xalign 0.5
        ypos 40
        spacing 8

        text "전학생 환영 소개팅" style "sg_title"
        text "오늘 ANN고에 전학 온 당신, 누구와 마주 앉을까요?" style "sg_lead"

    hbox:
        xalign 0.5
        ypos 168
        spacing 14

        for c in cards:
            use sg_card(c)

    text "실명과 학번은 적지 마세요." style "sg_foot" xalign 0.5 ypos 664


## 캐릭터 카드 한 장. c는 서버가 준 카드라서 글은 sg_esc 를 거쳐 찍는다.
screen sg_card(c):

    fixed:
        xysize (190, 446)

        ## 카드 밑의 그림자
        add Frame("images/ui/shadow20.png", 38, 38) xpos -16 ypos -8 xysize (222, 482) alpha 0.55

        button:
            style "sg_card"
            at sg_card_lift
            action Return(c)
            hover_background sg_panel(20, "#ffffff", 1.0, sg_on_light(c["color"]), 1.0, "_line3")

            vbox:
                spacing 7

                add sg_face_box(c["id"], c["color"], 166, 186)

                null height 1

                text sg_esc(c["name"]) style "sg_card_name"

                frame:
                    padding (10, 3, 10, 4)
                    background sg_box(8, c["color"])
                    text sg_esc(c["attribute"]) style "sg_card_attr" color sg_ink_on(c["color"])

                text ("모티프 · " + sg_esc(c["motif"])) style "sg_card_motif"

                text sg_esc(c["intro"]) style "sg_card_intro"


################################################################################
## 대화: 위쪽 표시
################################################################################

screen sg_hud():

    ## 대화 화면(sg_talk)보다 위에 둔다. 아래에 두면 화면 전체를 덮는 "눌러서 넘기기"
    ## 단추에 가려서 "엔딩 보러 가기"가 눌리지 않는다.
    zorder 10

    ## 왼쪽: 진행 표시, 장소, 그만두기
    hbox:
        xpos 28
        ypos 20
        spacing 10

        frame:
            style "sg_pill"

            hbox:
                spacing 12

                text sg_progress style "sg_pill_text"

                hbox:
                    spacing 5
                    yalign 0.5

                    for i in range(sg_total_turns):
                        if i < sg_turn_no:
                            add sg_icon("dot", 10, gui.sg_pink)
                        else:
                            add sg_icon("dot", 10, "#ffffff", 0.35)

        if sg_place:
            frame:
                style "sg_pill"
                text sg_esc(sg_place) style "sg_pill_text"

        if not sg_finale:
            textbutton "엔딩 보러 가기":
                style "sg_ghost_button"
                action Show("sg_confirm", message="여기서 끝내고 엔딩을 볼까요?",
                            yes_label="엔딩 보기", yes=Jump("sg_finish"), no_label="계속하기")

    ## 오른쪽: 호감도 게이지
    frame:
        style "sg_pill"
        xalign 1.0
        xoffset -28
        ypos 20

        hbox:
            spacing 10

            add sg_icon("heart", 20, gui.sg_pink) yalign 0.5
            text "호감도" style "sg_pill_text"
            bar value AnimatedValue(sg_score_shown, 100, 0.5) style "sg_gauge"
            text "[sg_score_shown]" style "sg_pill_num"


################################################################################
## 대화: 대사창
################################################################################

## 화면 위아래에 까는 옅은 그늘.
screen sg_shades():

    add "images/ui/shade_top.png" xysize (1280, 130)
    add "images/ui/shade_bottom.png" xysize (1280, 320) ypos 400


## 아래쪽 대사창과 이름표. 글은 부르는 쪽이 블록으로 넣는다.
## name과 note는 이미 안전하게 만든 글이어야 한다.
screen sg_textbox(name="", color="#5a6288", note=""):

    frame:
        style "sg_textbox"
        background sg_textbox_bg(color)

        transclude

    if name:
        hbox:
            xpos 84
            ypos 514
            spacing 10

            frame:
                style "sg_nametag"
                background sg_nametag_bg(color)
                text name style "sg_nametag_text" color sg_ink_on(color)

            if note:
                frame:
                    style "sg_tagnote"
                    text note style "sg_tagnote_text"


################################################################################
## 대화: 턴 하나
################################################################################
##
## v는 sg_build_view 가 만든 값이다. 단계(stage)는 이 순서로 넘어간다.
##
##   heard      가려진 채 들린 내 말 (드롭아웃 장치가 있을 때만)
##   narration  지문 (있을 때만)
##   say        대사. 이때 속마음 풍선과 호감도 변화가 같이 나온다
##   choices    선택지 3개와 직접 말하기. 마지막 답이면 대신 finale(엔딩 보기)
##
## 돌려주는 값: ("reply", 보낼 글) 또는 ("finish",)

screen sg_talk(v, first):

    zorder 5

    default stage = first

    $ nxt = sg_next_stage(v, stage)
    $ name = sg_esc(sg_char["name"])
    $ color = sg_char["color"]
    $ talking = stage in ("say", "choices", "finale")

    ## 위쪽 표시와 대사창 뒤를 어둡게 받쳐서 글이 잘 읽히게 한다.
    use sg_shades

    ## 화면 어디를 눌러도 다음 단계로 넘어간다. 대사가 나오는 중이면 먼저 대사가 다 나온다.
    if nxt:
        button:
            id "sg_advance"
            xysize (1280, 720)
            background None
            keyboard_focus False
            action [ SetScreenVariable("stage", nxt),
                     If(nxt == "say", SetVariable("sg_score_shown", v["score"]), NullAction()) ]

        key [ "K_SPACE", "K_RETURN", "K_KP_ENTER" ] action [
            SetScreenVariable("stage", nxt),
            If(nxt == "say", SetVariable("sg_score_shown", v["score"]), NullAction()) ]

    ## 속마음 풍선: 스탠딩의 왼쪽
    if talking and v["inner"]:
        frame:
            style "sg_bubble"
            at sg_rise(0.25)

            vbox:
                spacing 4
                text ("속마음" + (" · 일부 가려짐" if v["masked"] else "")):
                    style "sg_bubble_label"
                    color sg_on_light(color)
                text v["inner"] style "sg_bubble_text" size v["inner_size"]

        add "images/ui/bubble_tail.png" xpos 322 ypos 168 alpha 0.95 at sg_rise(0.25)

    ## 호감도 변화: 게이지 아래
    if talking and v["popup"]:
        vbox:
            xalign 1.0
            xoffset -30
            ypos 74
            spacing 6

            if v["popup_wild"]:
                text v["popup"] style "sg_popup_text" color v["popup_color"] size v["popup_size"] at sg_popup_in, sg_wild
            else:
                text v["popup"] style "sg_popup_text" color v["popup_color"] size v["popup_size"] at sg_popup_in

            if v["reason"]:
                frame:
                    style "sg_chip"
                    at sg_rise(0.3)
                    text ("사유: " + v["reason"]) style "sg_chip_text"

            for note in v["notes"]:
                frame:
                    style "sg_note"
                    at sg_rise(0.45)
                    text note style "sg_note_text"

    ## 대사창
    if stage == "heard":
        use sg_textbox("나", "#5a6288", name + "에게는 이렇게 들렸다"):
            text v["heard"] style "sg_say_text"

    elif stage == "narration":
        use sg_textbox():
            text v["narration"] style "sg_narration_text" size v["narration_size"] slow_cps sg_text_cps

    elif v["fallback"]:
        ## 대체 대사는 괄호로 싸인 지문이라 이름표 없이 지문처럼 보여 준다.
        use sg_textbox():
            text v["say"] style v["say_style"] size v["say_size"]

    else:
        use sg_textbox(name, color):
            if stage == "say":
                text v["say"] style v["say_style"] size v["say_size"] slow_cps sg_text_cps
            else:
                text v["say"] style v["say_style"] size v["say_size"]

    if nxt:
        add sg_icon("ctc", 22, "#ffffff") xpos 1180 ypos 668 at sg_ctc_blink

    ## 선택지와 직접 말하기: 대사창 바로 위, 가운데
    if stage == "choices":
        vbox:
            xpos 340
            yanchor 1.0
            ypos 508
            spacing 10

            for c in v["choices"]:
                button:
                    style "sg_choice"
                    at sg_rise(0.0)
                    action Return(("reply", c["raw"]))
                    text c["label"] style "sg_choice_text"

            frame:
                style "sg_input_box"
                at sg_rise(0.0)

                hbox:
                    spacing 12

                    fixed:
                        xsize 452
                        yfit True
                        yalign 0.5

                        if not sg_typed:
                            text "직접 말하기 (100자까지)" style "sg_placeholder_text"

                        input:
                            id "sg_input"
                            style "sg_input"
                            value SgTypedValue()
                            length 100

                    vbox:
                        xsize 92
                        yalign 0.5
                        spacing 3

                        text ("%d/100" % len(sg_typed)) style "sg_counter_text"

                        textbutton "보내기":
                            style "sg_send"
                            sensitive bool(sg_typed.strip())
                            action Return(("reply", sg_typed.strip()))

    ## 마지막 답 뒤에는 선택지 없이 엔딩 보기만 있다.
    elif stage == "finale":
        textbutton "엔딩 보기":
            style "sg_primary"
            xalign 0.5
            yanchor 1.0
            ypos 496
            at sg_breathe
            action Return(("finish",))


################################################################################
## 기다리는 화면
################################################################################

## 기다리는 동안 아래 화면의 단추가 눌리지 않게 막는 투명한 판.
## modal True 를 쓰면 안 된다. renpy.fetch 가 기다리는 동안 돌리는 renpy.pause 의
## 타이머까지 막혀서 게임이 그대로 멈춘다.
screen sg_shield():

    button:
        xysize (1280, 720)
        background None
        keyboard_focus False
        action NullAction()


## 통통 튀는 점 세 개.
screen sg_dots(color, size=12):

    hbox:
        spacing size // 2

        for i in range(3):
            add sg_icon("dot", size, color) at sg_bounce(i * 0.16)


## 가운데에 작은 창을 띄우고 기다린다. (명단 불러오기, 엔딩 불러오기)
screen sg_wait(message, dim=True):

    zorder 50

    use sg_shield

    if dim:
        add Solid("#12162e80")

    frame:
        style "sg_modal_panel"
        xminimum 420

        vbox:
            xalign 0.5
            spacing 18

            hbox:
                xalign 0.5
                use sg_dots(gui.sg_pink, 14)

            text message style "sg_modal_text"

            text "조금만 기다려 주세요. 길면 30초쯤 걸립니다." style "sg_modal_sub" at sg_after(6.0)


## 판을 시작할 때: 고른 캐릭터를 보여 주며 기다린다.
screen sg_wait_start(c):

    zorder 50

    use sg_shield

    add Solid("#f1f4ffcc")

    vbox:
        xalign 0.5
        yalign 0.45
        spacing 16

        add sg_face_box(c["id"], c["color"], 230, 258, 20) xalign 0.5

        text sg_esc(c["name"]) style "sg_title" size 38

        hbox:
            xalign 0.5
            spacing 14

            text "만나러 가는 중" style "sg_lead" yalign 0.5

            use sg_dots(sg_on_light(c["color"]), 12)

        text "조금만 기다려 주세요. 길면 30초쯤 걸립니다." style "sg_modal_sub" at sg_after(6.0)


## 내 말을 보낸 뒤: 대사창에 내 말을 띄우고, 스탠딩 옆에 대답을 고르는 말풍선을 띄운다.
screen sg_wait_reply(line):

    zorder 20

    use sg_shield

    $ name = sg_esc(sg_char["name"])

    use sg_shades

    frame:
        xpos 800
        ypos 150
        padding (24, 22, 24, 18)
        background sg_box(20, "#ffffff", 0.95)
        at sg_rise(0.0)

        use sg_dots(sg_on_light(sg_char["color"]), 13)

    add "images/ui/bubble_tail.png" xpos 792 ypos 196 xzoom -1.0 xanchor 1.0 alpha 0.95

    use sg_textbox("나", "#5a6288"):
        text sg_esc(line) style "sg_say_text"

    hbox:
        xalign 1.0
        xoffset -84
        ypos 668
        spacing 10

        text "조금만 기다려 주세요. 길면 30초쯤 걸립니다." style "sg_hint_text" at sg_after(6.0)
        text (name + "의 대답을 기다리는 중") style "sg_hint_text"


################################################################################
## 오류와 확인
################################################################################

## 가운데 창 하나에 안내와 단추 둘. message는 이미 안전하게 만든 글이어야 한다.
screen sg_confirm_panel(message, yes_label, yes_action, no_label, no_action):

    add Solid("#12162e99")

    frame:
        style "sg_modal_panel"
        xminimum 460

        vbox:
            xalign 0.5
            spacing 26

            text message style "sg_modal_text"

            hbox:
                xalign 0.5
                spacing 16

                textbutton yes_label style "sg_primary" action yes_action
                textbutton no_label style "sg_secondary" action no_action


## 게임 안의 확인 창. (도중에 엔딩으로 가기)
screen sg_confirm(message, yes_label, yes, no_label):

    modal True
    zorder 60

    use sg_confirm_panel(message, yes_label, [ Hide("sg_confirm"), yes ], no_label, Hide("sg_confirm"))


## 서버 오류 안내. buttons는 (단추 글, 돌려줄 값)의 목록이고 첫 단추가 강조된다.
## message는 이미 안전하게 만든 글이어야 한다 (SgResult.message).
screen sg_error(message, buttons):

    modal True
    zorder 70

    add Solid("#12162e99")

    frame:
        style "sg_modal_panel"
        xminimum 520

        vbox:
            xalign 0.5
            spacing 20

            text "연결에 문제가 생겼어요" style "sg_modal_title"

            text message style "sg_modal_text"

            hbox:
                xalign 0.5
                spacing 16

                for index, (label, value) in enumerate(buttons):
                    textbutton label:
                        style ("sg_primary" if index == 0 else "sg_secondary")
                        action Return(value)


################################################################################
## 엔딩
################################################################################
##
## e는 sg_build_ending 이 만든 값이다. 돌려주는 값: "again"(같은 캐릭터로 다시) 또는 "other"(첫 화면).

screen sg_ending(e):

    zorder 5

    default reveal = False

    add Solid("#12162e40")

    frame:
        style "sg_end_card"

        vbox:
            spacing 14

            ## 머리줄: 누구와의 소개팅인지, 등급 도장
            hbox:
                xfill True

                hbox:
                    spacing 10
                    yalign 0.5

                    text ("소개팅 성적표 · " + e["name"]) style "sg_end_kind"

                    if e["early"]:
                        text "(도중에 끝낸 판)" style "sg_end_kind"

                frame:
                    xalign 1.0
                    padding (20, 6, 20, 7)
                    background sg_box(14, e["band_color"])
                    text e["band"] style "sg_end_band"

            text e["title"] style "sg_end_title" size e["title_size"]

            if e["epilogue"]:
                text e["epilogue"] style "sg_end_text" size e["epilogue_size"]

            add Solid("#171b3622") xysize (660, 2)

            hbox:
                spacing 48

                vbox:
                    spacing 4

                    text "최종 호감도" style "sg_end_label"

                    hbox:
                        spacing 12

                        add sg_icon("heart", 30, gui.sg_pink) yalign 0.5
                        text str(e["score"]) style "sg_end_score"
                        bar value StaticValue(e["score"], 100):
                            style "sg_gauge"
                            xysize (170, 16)
                            right_bar sg_box(8, "#171b36", 0.14)

                if e["nickname"]:
                    vbox:
                        spacing 12

                        text "칭호" style "sg_end_label"

                        frame:
                            padding (16, 7, 16, 8)
                            background sg_panel(14, "#fff3c2", 1.0, "#e2b100", 1.0)
                            text e["nickname"] style "sg_end_nick"

            if e["best"]:
                vbox:
                    spacing 6

                    text "이번 판의 명대사" style "sg_end_label"

                    frame:
                        xsize 660
                        padding (20, 12, 20, 14)
                        background sg_box(14, "#eef0ff")
                        text e["best"] style "sg_end_text" size e["best_size"] xsize 620

    ## 단추
    hbox:
        xpos 544
        yanchor 1.0
        ypos 664
        spacing 14

        textbutton "다시 하기" style "sg_primary" action Return("again")
        textbutton "다른 캐릭터 고르기" style "sg_secondary" action Return("other")

        if e["reveal"]:
            textbutton "가려졌던 속마음 보기":
                style "sg_secondary"
                background sg_panel(20, "#171b36", 1.0, "#ffffff", 0.3)
                hover_background sg_panel(20, "#2c3468", 1.0, "#ffffff", 0.9)
                text_color "#ffffff"
                at sg_breathe
                action SetScreenVariable("reveal", True)

    ## 가려졌던 속마음의 원문. 속마음이 가려져 나온 판에서만 볼 수 있다.
    if reveal:
        button:
            xysize (1280, 720)
            background Solid("#12162ecc")
            keyboard_focus False
            action SetScreenVariable("reveal", False)

        frame:
            xalign 0.5
            yalign 0.5
            xysize (940, 620)
            padding (44, 30, 30, 28)
            background sg_panel(20, "#ffffff", 0.99, "#171b36", 0.12)

            vbox:
                spacing 12

                text "가려졌던 속마음" style "sg_modal_title" xalign 0.0
                text "대화 중에는 호감도만큼만 보였습니다. 아래가 원문입니다." style "sg_modal_sub" xalign 0.0

                viewport:
                    id "sg_reveal_list"
                    xysize (866, 428)
                    mousewheel True
                    draggable True
                    scrollbars "vertical"

                    vbox:
                        spacing 14

                        for r in e["reveal"]:
                            hbox:
                                spacing 16

                                frame:
                                    xysize (68, 30)
                                    background sg_box(14, "#171b36")
                                    text r["label"] style "sg_reveal_label"

                                vbox:
                                    spacing 3

                                    if r["masked"]:
                                        text r["masked"] style "sg_reveal_masked"

                                    text r["text"] style "sg_reveal_text"

                textbutton "닫기" style "sg_secondary" xalign 1.0 action SetScreenVariable("reveal", False)


################################################################################
## 입력 없음 감시
################################################################################
##
## 늘 떠 있는 보이지 않는 화면. 입력이 들어온 시각을 적고, 1초마다 얼마나 지났는지 본다.

screen sg_idle_watch():

    zorder 1000

    add SgIdleWatch()

    timer 1.0 repeat True action Function(sg_idle_tick, _update_screens=False)

init python:
    config.overlay_screens.append("sg_idle_watch")

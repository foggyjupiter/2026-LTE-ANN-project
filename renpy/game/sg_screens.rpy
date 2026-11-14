## 소개팅 화면들. 겉모습은 미소녀 게임풍이다.
##
##   sg_select       캐릭터 고르기 (히로인 선택)
##   sg_hud          대화 중 위쪽 표시: 진행, 장소 팻말, 하트 게이지
##   sg_talk         턴 하나: 들린 말 → 지문 → 대사 → 선택지(또는 엔딩 보기)
##   sg_wait*        서버의 답을 기다리는 동안
##   sg_error        서버 오류 안내와 다시 시도
##   sg_ending       엔딩
##
## 배경과 스탠딩은 여기서 그리지 않는다. sg_core.rpy 가 master 레이어에 올린다.
## 서버에서 온 글은 sg_core.rpy 의 sg_build_view 가 sg_esc 를 거쳐서 넘겨준다.
## 이 파일에서 서버의 글을 직접 찍는 곳(캐릭터 카드, 장소)은 sg_esc 를 불러서 쓴다.
##
## 장식 그림(images/ui/gal_*.png)은 renpy/dev/make_ui_art.py 가 만든다.
## 글꼴은 둘이다. 고정 문구(제목, 단추, 이름표)는 귀여운 Jua, 모델이 쓴 글은 Pretendard.
## Jua에는 한글이 2,367자뿐이라 서버에서 온 글에 쓸 때는 sg_cute 로 글자가 다 있는지 본다.
## 대사창과 풍선의 글 크기(1092x112, 254x250 등)는 sg_core.rpy 가 재므로 바꾸지 않는다.


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

    def sg_gal(name, left, top=None, right=None, bottom=None, tile=False):
        """미소녀 게임풍 장식 그림을 9칸으로 늘인 것."""
        if top is None:
            top = left
        if right is None:
            right, bottom = left, top
        return Frame("images/ui/gal_%s.png" % name, left, top, right, bottom, tile=tile)

    def sg_cute(text):
        """이 글을 귀여운 글꼴(Jua)로 찍을 수 있으면 그 글꼴, 아니면 Pretendard Bold.

        Jua에는 자주 쓰는 한글(KS X 1001의 2,350자)과 영문, 숫자만 있다.
        """
        for ch in str(text):
            if " " <= ch < "\x7f" and ch != "`":
                continue
            # 파이썬의 euc_kr 은 2,350자 밖의 한글도 여덟 바이트로 풀어서 바꿔 준다.
            # 두 바이트로 바뀌는 글자만 KS X 1001 에 있는 글자다.
            try:
                if "가" <= ch <= "힣" and len(ch.encode("euc_kr")) == 2:
                    continue
            except (LookupError, UnicodeError):
                pass
            return gui.name_text_font
        return gui.sg_cute_font

    def sg_textbox_bg(color):
        """대사창 바탕."""
        return sg_gal("textbox", 56)

    def sg_nametag_bg(color):
        """이름표 리본. 캐릭터의 대표색을 입히고 흰 바느질 선을 겹친다."""
        ribbon = Transform(sg_gal("nametag", 36, 0), matrixcolor=TintMatrix(color))
        return Fixed(ribbon, sg_gal("nametag_trim", 36, 0))

    def sg_ink_edge(color):
        """리본 위 글자에 두르는 테두리색. 대표색이 어떤 밝기여도 이름과 속성이 읽히게 한다.

        글자가 흰색이면(어두운 대표색) 리본색을 더 어둡게, 글자가 어두우면(밝은 대표색)
        리본색을 더 밝게 한 색이다. 글자색은 sg_core.rpy 의 sg_ink_on 이 밝기로 고른다.
        """
        if sg_ink_on(color) == "#ffffff":
            return Color(color).shade(0.55).hexcode
        return Color(color).tint(0.4).hexcode

    def sg_ribbon(color):
        """끝이 접힌 띠에 색을 입힌 것."""
        return Transform(sg_gal("ribbon", 22, 0), matrixcolor=TintMatrix(color))

    def sg_popup_shown(popup):
        """화면에 찍을 호감도 변화 글자. 마지막 답의 "NaN"은 컴퓨터 용어라 무한대 기호로 보여 준다."""
        return "∞" if popup == "NaN" else popup

    def sg_popup_kind(popup):
        """호감도 변화 글자를 보고 어떤 하트를 깔지 정한다."""
        if popup == "NaN":
            return "nan", "측정 불가?!"
        if popup.startswith("+"):
            return "up", "호감도 UP!"
        if popup.startswith("-"):
            return "down", "호감도 DOWN"
        return "zero", "변화 없음"

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
    Transform(sg_box(8, "#6db8f5"), xysize=(84, 25), xpos=3),
    Text("출처 필요", size=16, color="#ffffff", font="fonts/Pretendard-Bold.otf", xpos=45, xanchor=0.5, ypos=2),
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

## 통통 튀는 하트. 기다리는 표시에 쓴다.
transform sg_bounce(delay=0.0):
    yoffset 0
    pause delay
    block:
        easeout 0.22 yoffset -10
        easein 0.22 yoffset 0
        pause 0.46
        repeat

## 눌러서 넘기라는 하트.
transform sg_ctc_blink:
    yoffset 0
    block:
        easeout 0.28 yoffset -9
        easein 0.28 yoffset 0
        pause 0.3
        repeat

## 호감도 변화가 튀어나온다.
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

## 카드에 마우스를 올리면 떠오른다.
transform sg_card_lift:
    on idle:
        easein 0.12 yoffset 0
    on hover:
        easein 0.12 yoffset -10

## 선택지에 마우스를 올리면 살짝 커진다.
transform sg_choice_pop:
    xalign 0.5
    on idle:
        easein 0.1 zoom 1.0
    on hover:
        easein 0.1 zoom 1.03

## 엔딩 보기 단추가 천천히 숨 쉰다.
transform sg_breathe:
    zoom 1.0
    block:
        ease 0.7 zoom 1.04
        ease 0.7 zoom 1.0
        repeat

## 도장은 살짝 기울여서, 쾅 찍히듯 나타난다.
transform sg_stamp_in:
    rotate -13 alpha 0.0 zoom 1.6
    pause 0.5
    easein 0.16 alpha 1.0 zoom 0.84


################################################################################
## 스타일
################################################################################

## 대사창 -------------------------------------------------------------------------

## 대사창은 반투명하고, 높이는 글이 차지하는 만큼만 잡는다. (가장 길 때 166)
## 아래쪽에 붙어 있고 글이 길수록 위로 자란다. 자리는 sg_textbox 화면이 정한다.
style sg_textbox:
    xsize 1180
    yminimum 122
    padding (44, 34, 44, 20)

style sg_say_text:
    font gui.interface_text_font
    size 26
    color gui.sg_plum
    line_spacing 6
    xsize 1092
    slow_abortable True
    # 첫째는 투명한 테두리다. 형광펜 자리에서만 색이 들어온다 (sg_core.rpy 의 SG_HL_OPEN).
    # 둘째는 흰 테두리다. 대사창이 반투명해서 뒤에 무엇이 비쳐도 글이 읽히게 한다.
    outlines [ (absolute(4), "#00000000", absolute(0), absolute(0)), (absolute(2), "#fffffff2", absolute(0), absolute(0)) ]

style sg_narration_text:
    font gui.text_font
    size 24
    color "#6a4666"
    line_spacing 6
    xsize 1092
    slow_abortable True
    outlines [ (absolute(2), "#fffffff2", absolute(0), absolute(0)) ]

style sg_nametag:
    padding (44, 6, 44, 14)
    ysize 52

style sg_nametag_text:
    font gui.sg_cute_font
    size 26
    color "#ffffff"
    yalign 0.5

style sg_tagnote:
    padding (16, 6, 16, 7)
    yalign 0.3
    background sg_gal("plate", 22)

style sg_tagnote_text:
    font gui.interface_text_font
    size 16
    color "#c23a72"
    outlines [ (absolute(2), "#ffffffe6", absolute(0), absolute(0)) ]

style sg_hint_text:
    font gui.text_font
    size 16
    color "#9a7896"

## 위쪽 표시 -----------------------------------------------------------------------

style sg_pill:
    padding (18, 9, 18, 10)
    ysize 48
    background sg_gal("plate", 22)

style sg_pill_text:
    font gui.sg_cute_font
    size 21
    color gui.sg_plum
    outlines [ (absolute(2), "#ffffffe6", absolute(0), absolute(0)) ]
    yalign 0.5

style sg_pill_num is sg_pill_text:
    size 26
    color gui.sg_pink_deep
    min_width 42
    textalign 1.0

style sg_sign:
    padding (22, 20, 22, 8)
    ysize 58
    background sg_gal("sign", 26, 20, 26, 14)

style sg_sign_text:
    size 20
    color "#2c5d96"
    outlines [ (absolute(2), "#ffffffe6", absolute(0), absolute(0)) ]
    yalign 0.5

style sg_ghost_button:
    padding (16, 9, 16, 10)
    ysize 48
    background Transform(sg_gal("plate", 22), alpha=0.82)
    hover_background sg_gal("plate", 22)
    keyboard_focus False

style sg_ghost_button_text:
    font gui.sg_cute_font
    size 17
    color "#8a6486"
    hover_color gui.sg_pink_deep
    outlines [ (absolute(2), "#ffffffe6", absolute(0), absolute(0)) ]
    yalign 0.5

## 하트 열 개짜리 호감도 게이지. 채운 하트 줄을 점수만큼만 잘라서 빈 하트 줄 위에 보인다.
style sg_gauge:
    xysize (240, 24)
    yalign 0.5
    left_bar "images/ui/gal_hearts_full.png"
    right_bar "images/ui/gal_hearts_empty.png"

## 호감도 변화 ---------------------------------------------------------------------

style sg_popup_text:
    font gui.name_text_font
    outlines [ (absolute(7), "#4a2a4838", absolute(0), absolute(2)), (absolute(4), "#ffffff", absolute(0), absolute(0)) ]
    xalign 0.5
    yalign 0.5

style sg_popup_label:
    font gui.sg_cute_font
    size 22
    color "#ffffff"
    outlines [ (absolute(3), gui.sg_pink_deep, absolute(0), absolute(0)) ]
    xalign 0.5

style sg_chip:
    padding (16, 8, 16, 9)
    xalign 1.0
    background sg_gal("plate", 22)

style sg_chip_text:
    font gui.interface_text_font
    size 17
    color gui.sg_plum
    outlines [ (absolute(2), "#ffffffe6", absolute(0), absolute(0)) ]
    xmaximum 262

style sg_note:
    padding (14, 6, 14, 7)
    xalign 1.0
    background sg_panel(14, gui.sg_yellow, 0.97, "#b98a00", 1.0)

style sg_note_text:
    font gui.name_text_font
    size 17
    color gui.sg_plum
    xmaximum 262

## 속마음 풍선 ---------------------------------------------------------------------

style sg_bubble:
    xpos 4
    ypos 112
    xsize 326
    padding (36, 28, 36, 32)
    background sg_gal("cloud", 32, tile="integer")

style sg_bubble_label:
    font gui.sg_cute_font
    size 16

style sg_bubble_text:
    font gui.interface_text_font
    size 19
    color gui.sg_plum
    line_spacing 4
    xsize 254

## 선택지와 직접 말하기 --------------------------------------------------------------
##
## 선택지 그림에는 빛이 번질 자리가 둘레에 10픽셀씩 있다. 그래서 단추는 보이는 것보다 20픽셀 크다.

style sg_choice:
    xsize 540
    yminimum 72
    padding (56, 21, 56, 22)
    background sg_gal("choice", 46, 14)
    hover_background sg_gal("choice_hover", 46, 14)

style sg_choice_text:
    font gui.interface_text_font
    size 21
    color gui.sg_plum
    hover_color gui.sg_pink_deep
    outlines [ (absolute(2), "#fffffff2", absolute(0), absolute(0)) ]
    xalign 0.5
    textalign 0.5
    yalign 0.5

## 직접 말하기 칸은 말풍선이다. 아래 20픽셀은 꼬리가 차지한다.
style sg_input_box:
    xsize 530
    xalign 0.5
    padding (24, 13, 14, 32)
    background sg_gal("speech", 64, 24, 30, 38)

style sg_input:
    font gui.interface_text_font
    size 20
    color gui.sg_plum
    caret Solid("#f2558e", xysize=(2, 24))
    xmaximum 382
    adjust_spacing False

style sg_placeholder_text:
    font gui.sg_cute_font
    size 20
    color "#c9a9bf"

style sg_page_count:
    font gui.text_font
    size 15
    color "#b093ab"
    xpos 1150
    xanchor 1.0
    ypos 662

style sg_counter_text:
    font gui.text_font
    size 13
    color "#b093ab"
    xalign 1.0

style sg_send:
    xysize (92, 36)
    xalign 1.0
    background sg_panel(14, gui.sg_pink, 1.0, "#ffffff", 0.9)
    hover_background sg_panel(14, gui.sg_pink_deep, 1.0, "#ffffff", 1.0)
    insensitive_background sg_box(14, "#d8cdd6")

style sg_send_text:
    font gui.sg_cute_font
    size 18
    color "#ffffff"
    xalign 0.5
    yalign 0.5

## 큰 단추 -----------------------------------------------------------------------
##
## 단추 그림도 둘레 8픽셀이 빛이 번질 자리다.

style sg_primary:
    padding (40, 20, 40, 22)
    yminimum 72
    background sg_gal("btn", 30)
    hover_background sg_gal("btn_hover", 30)

style sg_primary_text:
    font gui.sg_cute_font
    size 24
    color "#ffffff"
    outlines [ (absolute(1), "#d63f7c", absolute(0), absolute(1)) ]
    xalign 0.5
    yalign 0.5

style sg_secondary:
    padding (36, 20, 36, 22)
    yminimum 72
    background sg_gal("btn2", 30)
    hover_background sg_gal("btn2_hover", 30)

style sg_secondary_text:
    font gui.sg_cute_font
    size 22
    color gui.sg_plum
    hover_color gui.sg_pink_deep
    xalign 0.5
    yalign 0.5

## 가운데 창 (기다림, 오류, 확인) ------------------------------------------------------

style sg_modal_panel:
    xalign 0.5
    yalign 0.5
    padding (58, 46, 58, 44)
    background sg_gal("card", 40)

style sg_modal_title:
    font gui.sg_cute_font
    size 30
    color gui.sg_pink_deep
    xalign 0.5

style sg_modal_text:
    font gui.interface_text_font
    size 20
    color gui.sg_plum
    xalign 0.5
    textalign 0.5
    line_spacing 6

style sg_modal_sub:
    font gui.text_font
    size 16
    color "#9a7896"
    xalign 0.5
    textalign 0.5

## 고르기 화면 ---------------------------------------------------------------------

style sg_lead:
    font gui.sg_cute_font
    size 23
    color gui.sg_plum
    outlines [ (absolute(3), "#ffffff", absolute(0), absolute(0)) ]
    xalign 0.5

style sg_title is sg_lead:
    size 40
    color gui.sg_pink_deep

style sg_foot:
    font gui.text_font
    size 15
    color "#7a5676"
    outlines [ (absolute(2), "#ffffffcc", absolute(0), absolute(0)) ]

## 카드 그림도 둘레 10픽셀이 빛이 번질 자리다.
style sg_card:
    xysize (210, 446)
    padding (22, 22, 22, 22)
    background sg_gal("card", 40)
    hover_background sg_gal("card_hover", 40)

style sg_card_name:
    size 28
    color gui.sg_plum

style sg_card_attr:
    size 16

## 속성 리본 밑의 한 줄. 꼬리표 없이 이 글만 나오므로 본문보다 조금 크고 분홍빛으로 찍는다.
style sg_card_motif:
    size 17
    color "#c2507f"

style sg_card_intro:
    font gui.text_font
    size 15
    color "#5d3d5a"
    line_spacing 4
    xsize 166

## 카드 맨 아래 안내 한 줄. 하이쿠처럼 화면에 장치가 있는 캐릭터만 붙는다
style sg_card_note:
    font gui.text_font
    size 14
    bold True
    color "#c2507f"
    line_spacing 3
    xsize 166
    top_margin 6
    language "korean-with-spaces"   # 낱말 가운데서 줄을 바꾸지 않는다 ("보여 / 요." 가 되지 않게)

## 엔딩 화면 ----------------------------------------------------------------------

style sg_end_card:
    xpos 490
    ypos 26
    xysize (768, 672)
    padding (54, 50, 54, 40)
    background sg_gal("card", 40)

style sg_end_kind:
    font gui.interface_text_font
    size 17
    color "#9a7896"

style sg_end_band:
    color "#d6263c"
    xalign 0.5
    yalign 0.5

## 제목은 오른쪽 위의 등급 도장(x 1124부터)에 가리지 않게 570까지만 쓴다
style sg_end_title:
    font gui.name_text_font
    size 36
    color gui.sg_plum
    xsize 570

style sg_end_text:
    font gui.interface_text_font
    size 20
    color "#5d3d5a"
    line_spacing 6
    xsize 660

style sg_end_label:
    font gui.sg_cute_font
    size 17
    color gui.sg_pink_deep

style sg_end_score:
    font gui.sg_cute_font
    size 46
    color gui.sg_pink_deep

style sg_end_nick:
    size 22
    color "#8a5a00"
    yalign 0.5

style sg_reveal_label:
    font gui.sg_cute_font
    size 16
    color "#ffffff"
    xalign 0.5
    yalign 0.5

style sg_reveal_masked:
    font gui.text_font
    size 16
    color "#b093ab"
    xsize 730

style sg_reveal_text:
    font gui.interface_text_font
    size 19
    color gui.sg_plum
    line_spacing 4
    xsize 730


################################################################################
## 고르기 화면
################################################################################

screen sg_select(cards):

    ## 배경을 뿌옇게 덮어서 카드가 또렷이 보이게 한다.
    add Solid("#fff3f8b8")

    ## 흩날리는 꽃잎
    add SnowBlossom("images/ui/gal_petal.png", count=18, xspeed=(20, 60), yspeed=(50, 110), fast=True)

    add "images/ui/gal_title.png" xalign 0.5 ypos 4

    text "오늘 ANN고에 전학 온 당신, 누구와 마주 앉을까요?" style "sg_lead" ypos 118

    hbox:
        xalign 0.5
        ypos 172
        spacing -6

        for c in cards:
            use sg_card(c)

    ## 대화는 바깥 모델에 보내므로 실명과 학번을 적지 않게 한다. 순위표의 학번과 이름은 이 컴퓨터에만 남는다
    text "대화에는 실명과 학번을 적지 마세요." style "sg_foot" xalign 0.5 ypos 664

    ## 오늘의 순위. 오른쪽 위 구석
    textbutton "오늘의 순위":
        style "sg_secondary"
        xalign 1.0
        xoffset -18
        ypos 18
        action Return("ranking")


## 캐릭터 카드 한 장. c는 서버가 준 카드라서 글은 sg_esc 를 거쳐 찍는다.
screen sg_card(c):

    button:
        style "sg_card"
        at sg_card_lift
        action Return(c)

        vbox:
            spacing 6

            add sg_face_box(c["id"], c["color"], 166, 186)

            text sg_esc(c["name"]) style "sg_card_name" font sg_cute(c["name"])

            ## 속성 리본
            frame:
                xoffset -8
                ysize 34
                padding (26, 3, 26, 9)
                background sg_ribbon(c["color"])
                text sg_esc(c["attribute"]):
                    style "sg_card_attr"
                    font sg_cute(c["attribute"])
                    color sg_ink_on(c["color"])
                    outlines [ (absolute(2), sg_ink_edge(c["color"]), absolute(0), absolute(0)) ]
                    yalign 0.5

            text sg_esc(c["motif"]) style "sg_card_motif" font sg_cute(c["motif"])   # 매력 한 줄

            text sg_esc(c["intro"]) style "sg_card_intro"

            if c.get("note"):
                text sg_esc(c["note"]) style "sg_card_note"


################################################################################
## 대화: 위쪽 표시
################################################################################

screen sg_hud():

    ## 대화 화면(sg_talk)보다 위에 둔다. 아래에 두면 화면 전체를 덮는 "눌러서 넘기기"
    ## 단추에 가려서 "엔딩 보러 가기"가 눌리지 않는다.
    zorder 10

    ## 왼쪽: 진행 표시(꽃), 장소 팻말, 그만두기
    hbox:
        xpos 24
        ypos 8
        spacing 10

        frame:
            style "sg_pill"
            yoffset 10

            hbox:
                spacing 12

                text sg_progress style "sg_pill_text"

                hbox:
                    spacing 3
                    yalign 0.5

                    for i in range(sg_total_turns):
                        if i < sg_turn_no:
                            add "images/ui/gal_flower_on.png"
                        else:
                            add "images/ui/gal_flower_off.png"

        if sg_place:
            frame:
                style "sg_sign"
                text sg_esc(sg_place) style "sg_sign_text" font sg_cute(sg_place)

        if not sg_finale:
            textbutton "엔딩 보러 가기":
                style "sg_ghost_button"
                yoffset 10
                action Show("sg_confirm", message="여기서 끝내고 엔딩을 볼까요?",
                            yes_label="엔딩 보기", yes=Jump("sg_finish"), no_label="계속하기")

    ## 오른쪽: 하트 게이지
    frame:
        style "sg_pill"
        xalign 1.0
        xoffset -24
        ypos 18

        hbox:
            spacing 10

            text "호감도" style "sg_pill_text" color gui.sg_pink_deep
            bar value AnimatedValue(sg_score_shown, 100, 0.5) style "sg_gauge"
            text sg_score_text(sg_score_shown) style "sg_pill_num"


################################################################################
## 대화: 대사창
################################################################################

## 예전에는 화면 위아래에 그늘을 깔았다. 지금은 창마다 바탕이 있어서 아무것도 깔지 않는다.
screen sg_shades():
    pass


## 아래쪽 대사창과 이름표 리본. 글은 부르는 쪽이 블록으로 넣는다.
## name과 note는 이미 안전하게 만든 글이어야 한다. raw_name은 글꼴을 고르는 데만 쓴다.
screen sg_textbox(name="", color="#8f96b8", note="", raw_name=""):

    vbox:
        xpos 50
        yanchor 1.0
        ypos 706
        spacing -22
        order_reverse True      # 먼저 적은 이름표가 대사창 위에 그려진다

        if name:
            hbox:
                xoffset 22
                spacing 6

                frame:
                    style "sg_nametag"
                    background sg_nametag_bg(color)

                    hbox:
                        spacing 7
                        yalign 0.5

                        add sg_icon("heart", 15, sg_ink_on(color), 0.9) yalign 0.5
                        text name:
                            style "sg_nametag_text"
                            font sg_cute(raw_name or name)
                            color sg_ink_on(color)
                            outlines [ (absolute(2), sg_ink_edge(color), absolute(0), absolute(0)) ]

                if note:
                    frame:
                        style "sg_tagnote"
                        text note style "sg_tagnote_text"

        frame:
            style "sg_textbox"
            background sg_textbox_bg(color)
            top_padding (34 if name else 24)

            transclude


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
    default page = 0              # 지문이나 대사가 여러 쪽이면 지금 쪽 (sg_pages)

    $ nxt = sg_next_stage(v, stage)
    $ pages = sg_stage_pages(v, stage)
    $ more = page + 1 < pages     # 이 단계에 남은 쪽이 있다
    $ name = sg_esc(sg_char["name"])
    $ color = sg_char["color"]
    $ talking = stage in ("say", "choices", "finale")
    ## 선택지와 결말 단계에서는 대사의 마지막 쪽을 띄워 둔다
    $ say_page = v["say_pages"][min(page, len(v["say_pages"]) - 1)] if stage == "say" else v["say_pages"][-1]
    $ narration_page = v["narration_pages"][min(page, len(v["narration_pages"]) - 1)]

    ## 화면 어디를 눌러도 다음 쪽, 다음 단계로 넘어간다. 대사가 나오는 중이면 먼저 대사가 다 나온다.
    if more:
        button:
            id "sg_advance"
            xysize (1280, 720)
            background None
            keyboard_focus False
            action [ Function(sg_sound, "sg_sfx", "next"), SetScreenVariable("page", page + 1) ]

        key [ "K_SPACE", "K_RETURN", "K_KP_ENTER" ] action [
            Function(sg_sound, "sg_sfx", "next"), SetScreenVariable("page", page + 1) ]

    elif nxt:
        button:
            id "sg_advance"
            xysize (1280, 720)
            background None
            keyboard_focus False
            action [ If(nxt == "say" and v["popup"],
                        Function(sg_sound, "sg_sfx_score", v["popup"]),
                        Function(sg_sound, "sg_sfx", "next")),
                     SetScreenVariable("stage", nxt),
                     SetScreenVariable("page", 0),
                     If(nxt == "say", SetVariable("sg_score_shown", v["score"]), NullAction()) ]

        key [ "K_SPACE", "K_RETURN", "K_KP_ENTER" ] action [
            If(nxt == "say" and v["popup"],
               Function(sg_sound, "sg_sfx_score", v["popup"]),
               Function(sg_sound, "sg_sfx", "next")),
            SetScreenVariable("stage", nxt),
            SetScreenVariable("page", 0),
            If(nxt == "say", SetVariable("sg_score_shown", v["score"]), NullAction()) ]

    ## 속마음: 스탠딩 왼쪽의 생각 풍선
    if talking and v["inner"]:
        frame:
            style "sg_bubble"
            at sg_rise(0.25)

            vbox:
                spacing 3
                ## 가려진 속마음은 드러난 글자의 비율이 그때의 호감도와 같다. 그 숫자를 함께 적는다
                text ("속마음" + ((" (호감도 %s%%만큼 보임)" % sg_score_text(v["score"])) if v["masked"] else "")):
                    style "sg_bubble_label"
                    color sg_on_light(color)
                text v["inner"] style "sg_bubble_text" size v["inner_size"]

        add "images/ui/gal_cloud_tail.png" xpos 326 ypos 176 at sg_rise(0.25)

    ## 호감도 변화: 게이지 아래에서 하트가 터진다. 선택지가 뜨면 치운다.
    ## 선택지는 오른쪽에 뜨므로 팝업의 사유와 알림 칸이 첫 선택지와 겹쳤다. 팝업은 대사 단계에서 이미 보였다
    if talking and stage != "choices" and v["popup"]:
        $ kind, label = sg_popup_kind(v["popup"])

        vbox:
            xalign 1.0
            xoffset -24
            ypos 76
            spacing 2

            fixed:
                xysize (250, 168)
                xalign 1.0
                at sg_popup_in

                add ("images/ui/gal_burst_%s.png" % kind) xalign 0.5 ypos 8

                if v["popup_wild"]:
                    text sg_popup_shown(v["popup"]) style "sg_popup_text" color v["popup_color"] size v["popup_size"] yoffset 10 at sg_wild
                else:
                    text sg_popup_shown(v["popup"]) style "sg_popup_text" color v["popup_color"] size v["popup_size"] yoffset 10

                text label style "sg_popup_label" ypos 0

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
        use sg_textbox("나", "#8f96b8", name + "에게는 이렇게 들렸다"):
            text v["heard"] style "sg_say_text"

    elif stage == "narration":
        use sg_textbox():
            text narration_page["text"] style "sg_narration_text" size narration_page["size"] slow_cps sg_text_cps

    elif v["fallback"]:
        ## 대체 대사는 괄호로 싸인 지문이라 이름표 없이 지문처럼 보여 준다.
        use sg_textbox():
            text say_page["text"] style v["say_style"] size say_page["size"]

    else:
        use sg_textbox(name, color, raw_name=sg_char["name"]):
            if stage == "say":
                text say_page["text"] style v["say_style"] size say_page["size"] slow_cps sg_text_cps
            else:
                text say_page["text"] style v["say_style"] size say_page["size"]

    ## 여러 쪽이면 몇 쪽째인지 대사창 오른쪽 아래에 적는다
    if pages > 1:
        text ("%d/%d" % (page + 1, pages)) style "sg_page_count"

    if more or nxt:
        add "images/ui/gal_ctc.png" xpos 1172 ypos 656 at sg_ctc_blink

    ## 선택지와 직접 말하기: 대사창 바로 위, 오른쪽. 가운데에 두면 캐릭터의 얼굴을 가렸다.
    ## 스탠딩은 가운데(640)에 서고 얼굴은 대략 x 530-730 이다. 선택지는 그 오른쪽에서 시작한다.
    if stage == "choices":
        vbox:
            xpos 728
            xsize 540
            yanchor 1.0
            ypos 512
            spacing -8

            for c in v["choices"]:
                button:
                    style "sg_choice"
                    at sg_choice_pop
                    action Return(("reply", c["raw"]))
                    text c["label"] style "sg_choice_text"

            null height 14

            frame:
                style "sg_input_box"

                hbox:
                    spacing 12

                    fixed:
                        xsize 382
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
            ypos 500
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


## 통통 튀는 하트 세 개.
screen sg_dots(color, size=12):

    hbox:
        spacing size // 3

        for i in range(3):
            add sg_icon("heart", size + 6, color) at sg_bounce(i * 0.16)


## 가운데에 작은 창을 띄우고 기다린다. (명단 불러오기, 엔딩 불러오기)
screen sg_wait(message, dim=True):

    zorder 50

    use sg_shield

    if dim:
        add Solid("#4a2a4866")

    frame:
        style "sg_modal_panel"
        xminimum 440

        vbox:
            xalign 0.5
            spacing 16

            hbox:
                xalign 0.5
                use sg_dots(gui.sg_pink, 16)

            text message style "sg_modal_title" size 26

            text "조금만 기다려 주세요. 길면 30초쯤 걸립니다." style "sg_modal_sub" at sg_after(6.0)


## 판을 시작할 때: 고른 캐릭터를 보여 주며 기다린다.
screen sg_wait_start(c):

    zorder 50

    use sg_shield

    add Solid("#fff3f8cc")

    add SnowBlossom("images/ui/gal_petal.png", count=14, xspeed=(20, 60), yspeed=(50, 110), fast=True)

    vbox:
        xalign 0.5
        yalign 0.45
        spacing 12

        frame:
            xalign 0.5
            padding (24, 24, 24, 24)
            background sg_gal("card", 40)
            add sg_face_box(c["id"], c["color"], 230, 258, 14)

        text sg_esc(c["name"]) style "sg_title" font sg_cute(c["name"])

        hbox:
            xalign 0.5
            spacing 14

            text "만나러 가는 중" style "sg_lead" yalign 0.5

            use sg_dots(gui.sg_pink, 13)

        text "조금만 기다려 주세요. 길면 30초쯤 걸립니다." style "sg_modal_sub" at sg_after(6.0)


## 내 말을 보낸 뒤: 대사창에 내 말을 띄우고, 스탠딩 옆에 대답을 고르는 말풍선을 띄운다.
screen sg_wait_reply(line):

    zorder 20

    use sg_shield

    $ name = sg_esc(sg_char["name"])

    frame:
        xpos 790
        ypos 140
        padding (30, 22, 30, 36)
        background Transform(sg_gal("speech", 64, 24, 30, 38), xzoom=1.0)
        at sg_rise(0.0)

        use sg_dots(gui.sg_pink, 14)

    frame:
        style "sg_tagnote"
        xpos 790
        ypos 222
        yanchor 0.0
        at sg_after(6.0)
        text "조금만 기다려 주세요. 길면 30초쯤 걸립니다." style "sg_tagnote_text"

    use sg_textbox("나", "#8f96b8", name + "의 대답을 기다리는 중"):
        text sg_esc(line) style "sg_say_text"


################################################################################
## 오류와 확인
################################################################################

## 가운데 창 하나에 안내와 단추 둘. message는 이미 안전하게 만든 글이어야 한다.
screen sg_confirm_panel(message, yes_label, yes_action, no_label, no_action):

    add Solid("#4a2a4880")

    frame:
        style "sg_modal_panel"
        xminimum 480

        vbox:
            xalign 0.5
            spacing 18

            text message style "sg_modal_text" size 22

            hbox:
                xalign 0.5
                spacing 0

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

    add Solid("#4a2a4880")

    frame:
        style "sg_modal_panel"
        xminimum 540

        vbox:
            xalign 0.5
            spacing 14

            text "앗, 연결에 문제가 생겼어요" style "sg_modal_title"

            text message style "sg_modal_text"

            hbox:
                xalign 0.5
                spacing 0

                for index, (label, value) in enumerate(buttons):
                    textbutton label:
                        style ("sg_primary" if index == 0 else "sg_secondary")
                        action Return(value)


################################################################################
## 엔딩
################################################################################
##
## e는 sg_build_ending 이 만든 값이다. 돌려주는 값: "rank"(순위표 등록), "again"(같은 캐릭터로 다시), "other"(첫 화면).

screen sg_ending(e):

    zorder 5

    default reveal = False

    add Solid("#4a2a4833")

    frame:
        style "sg_end_card"

        vbox:
            spacing 12

            ## 누구와의 소개팅인지
            hbox:
                spacing 10

                text e["name"] style "sg_end_kind"

                if e["early"]:
                    text "(도중에 끝낸 판)" style "sg_end_kind"

            text e["title"] style "sg_end_title" size e["title_size"]

            if e["epilogue"]:
                text e["epilogue"] style "sg_end_text" size e["epilogue_size"]

            add Solid("#f2558e33") xysize (660, 2)

            hbox:
                spacing 26

                vbox:
                    spacing 2

                    text "최종 호감도" style "sg_end_label"

                    hbox:
                        spacing 12

                        text sg_score_text(e["score"]) style "sg_end_score"
                        bar value StaticValue(e["score"], 100) style "sg_gauge"

                if e["nickname"]:
                    vbox:
                        spacing 4

                        text "칭호" style "sg_end_label"

                        ## 월계수 배지
                        hbox:
                            spacing 6

                            add "images/ui/gal_laurel.png" yalign 0.5 zoom 0.7
                            text e["nickname"] style "sg_end_nick" font gui.name_text_font
                            add "images/ui/gal_laurel.png" yalign 0.5 xzoom -0.7 yzoom 0.7

            if e["best"]:
                vbox:
                    spacing 6

                    text "이번 판의 명대사" style "sg_end_label"

                    frame:
                        xsize 660
                        padding (20, 12, 20, 14)
                        background sg_panel(14, "#fff0f6", 1.0, "#ffc3d9", 1.0)
                        text e["best"] style "sg_end_text" size e["best_size"] xsize 620

            ## 호감도 곡선: 등장부터 마지막 답까지. 점이 둘 이상일 때만
            if e.get("curve_box") is not None:
                vbox:
                    spacing 2

                    text ("호감도 곡선 (등장부터 답 %d까지)" % (len(e["curve"]) - 1)) style "sg_end_label"
                    add e["curve_box"]

    ## 카드 위의 리본 머리띠
    frame:
        xpos 874
        xanchor 0.5
        ypos 14
        ysize 40
        padding (44, 4, 44, 10)
        background sg_ribbon(gui.sg_pink)
        text "소개팅 성적표" font gui.sg_cute_font size 22 color "#ffffff" yalign 0.5

    ## 등급 도장. 빨간 인주로 살짝 기울여 찍는다.
    fixed:
        xpos 1124
        ypos 4
        xysize (150, 150)
        at sg_stamp_in

        add "images/ui/gal_stamp.png"
        text e["band"] style "sg_end_band" font sg_cute(e["band"]) size (48 if len(e["band"]) <= 2 else 36)

    ## 단추
    hbox:
        xpos 530
        yanchor 1.0
        ypos 680
        spacing -4

        ## 순위표 등록이 먼저다. 단추가 넷이 되어도(하이쿠) 카드 폭에 들어가게 이름을 짧게 쓴다
        textbutton "순위표 등록" style "sg_primary" at sg_breathe action Return("rank")
        textbutton "다시 하기" style "sg_secondary" action Return("again")
        textbutton "다른 캐릭터" style "sg_secondary" action Return("other")

        if e["reveal"]:
            textbutton "속마음 보기":
                style "sg_secondary"
                action SetScreenVariable("reveal", True)

    ## 가려졌던 속마음의 원문. 속마음이 가려져 나온 판에서만 볼 수 있다.
    if reveal:
        button:
            xysize (1280, 720)
            background Solid("#4a2a48b3")
            keyboard_focus False
            action SetScreenVariable("reveal", False)

        frame:
            xalign 0.5
            yalign 0.5
            xysize (960, 640)
            padding (56, 44, 42, 34)
            background sg_gal("card", 40)

            vbox:
                spacing 10

                text "가려졌던 속마음" style "sg_modal_title" xalign 0.0
                text "대화 중에는 호감도만큼만 보였습니다. 아래가 원문입니다." style "sg_modal_sub" xalign 0.0

                viewport:
                    id "sg_reveal_list"
                    xysize (862, 404)
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
                                    background sg_box(14, gui.sg_pink)
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

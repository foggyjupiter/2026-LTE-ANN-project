################################################################################
## 초기화
################################################################################

init offset = -1


################################################################################
## 기본 스타일
################################################################################
##
## 소개팅 화면의 스타일은 sg_screens.rpy 에 있다. 여기에는 Ren'Py가 바탕으로 삼는
## 스타일과, 엔진이 이름으로 찾는 화면(say, choice, confirm, notify)만 둔다.
## 부스용이라 주 메뉴, 저장, 불러오기, 환경설정, 기록, 빠른 메뉴 화면은 만들지 않았다.

style default:
    font gui.text_font
    size gui.text_size
    color gui.sg_paper
    language gui.language

style input:
    font gui.interface_text_font
    size gui.interface_text_size
    color gui.sg_ink
    adjust_spacing False

style gui_text:
    font gui.interface_text_font
    size gui.interface_text_size
    color gui.sg_paper

style button_text is gui_text:
    yalign 0.5

style label_text is gui_text:
    font gui.name_text_font

style frame:
    background None
    padding (0, 0)

style vscrollbar:
    xsize 10
    base_bar Transform(Frame("images/ui/r8.png", 8, 8), matrixcolor=TintMatrix("#171b36"), alpha=0.12)
    thumb Transform(Frame("images/ui/r8.png", 8, 8), matrixcolor=TintMatrix("#171b36"), alpha=0.5)
    unscrollable "hide"


################################################################################
## 엔진이 이름으로 찾는 화면
################################################################################

## Say 화면 #######################################################################
##
## 이 게임의 대사는 sg_talk 화면이 그린다. 이 화면은 누가 say 문을 썼을 때 오류가
## 나지 않도록 같은 모양으로 남겨 둔 것이다.

screen say(who, what):

    frame:
        id "window"
        style "sg_textbox"
        background Frame("images/ui/gal_textbox.png", 56, 56)

        text what id "what" style "sg_say_text"

    if who is not None:
        frame:
            style "sg_nametag"
            xpos 72
            ypos 504
            background Transform(Frame("images/ui/gal_nametag.png", 36, 0), matrixcolor=TintMatrix("#8f96b8"))
            text who id "who" style "sg_nametag_text"


## Choice 화면 ####################################################################

screen choice(items):

    vbox:
        xalign 0.5
        yanchor 1.0
        ypos 506
        spacing 10

        for i in items:
            button:
                style "sg_choice"
                action i.action
                text i.caption style "sg_choice_text"


## Confirm 화면 ###################################################################
##
## 엔진이 예/아니오를 물을 때 쓴다. 게임 안의 확인 창은 sg_confirm 이다.

screen confirm(message, yes_action, no_action):

    modal True
    zorder 200

    use sg_confirm_panel(_(message), _("네"), yes_action, _("아니오"), no_action)


## Notify 화면 ####################################################################

screen notify(message):

    zorder 100

    frame:
        xpos 28
        ypos 80
        padding (16, 8)
        background Frame("images/ui/gal_plate.png", 22, 22)
        text "[message!tq]" size 16 color gui.sg_plum

    timer 3.25 action Hide("notify")

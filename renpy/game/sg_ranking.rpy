## sg_ranking.rpy: 순위표. 엔딩 뒤 학번과 이름으로 순위표에 올리기와 오늘의 순위.
##
## 상품을 주려고 만든 순위표라 학번과 이름을 받는다. 서버(sogaeting/server.py, ranking.py)가 결과 파일에
## 그대로 적고 순위를 매긴다. 화면에 오는 순위표의 이름은 서버가 가운데를 가려 보낸다(김*수).
## 여기에는 화면과 화면용 값만 있다.
##   POST /api/session/<id>/rank {"student_id": 학번, "name": 이름}   순위표에 올리고 오늘의 순위표를 받는다
##   GET  /api/ranking                                              오늘의 순위표
## 흐름(어느 화면에서 어디로 가는지)은 script.rpy 의 sg_rank, sg_show_ranking 레이블에 있다.

default sg_rank_sid = ""          # 학번 입력칸의 글
default sg_rank_person = ""       # 이름 입력칸의 글
default sg_rank_error = ""        # 서버가 거절한 까닭. 입력 화면에 띄운다
default sg_board_view = None      # 순위표를 화면용으로 바꾼 값 (sg_build_board)

## 입력칸 글자 수 한도. 서버(sogaeting/ranking.py STUDENT_ID_RE, NAME_RE)가 받는 길이다
define sg_sid_max = 10
define sg_person_max = 12
## 1-3등의 등수 색
define sg_rank_colors = { 1: "#d4a017", 2: "#8f9bb3", 3: "#c0763a" }


init python:

    def sg_rank_ready():
        return bool(store.sg_rank_sid.strip() and store.sg_rank_person.strip())

    class SgSidValue(InputValue, FieldEquality):
        """학번 입력칸. 처음에 이 칸에 글이 들어간다. Enter를 누르면 이름 칸으로 넘어간다."""

        equality_fields = ( )
        identity_fields = ( )

        default = True
        editable = True
        returnable = True

        def get_text(self):
            return store.sg_rank_sid

        def set_text(self, s):
            store.sg_rank_sid = s
            renpy.restart_interaction()

        def enter(self):
            renpy.set_editable_input_value(SgPersonValue(), True)
            renpy.restart_interaction()
            raise renpy.IgnoreEvent()

    class SgPersonValue(InputValue, FieldEquality):
        """이름 입력칸. Enter를 누르면 두 칸이 다 차 있을 때 올린다."""

        equality_fields = ( )
        identity_fields = ( )

        default = False
        editable = True
        returnable = True

        def get_text(self):
            return store.sg_rank_person

        def set_text(self, s):
            store.sg_rank_person = s
            renpy.restart_interaction()

        def enter(self):
            if sg_rank_ready():
                sg_sound("sg_sfx", "send")
                return ("rank", store.sg_rank_sid.strip(), store.sg_rank_person.strip())
            raise renpy.IgnoreEvent()

    def sg_is_board(data):
        return isinstance(data, python_dict) and isinstance(data.get("rows"), python_list)

    def sg_board_row(item):
        """서버가 준 순위표 한 줄을 화면용으로. 모양이 이상하면 None."""
        if not isinstance(item, python_dict):
            return None
        rank = sg_int(item.get("rank"), 0)
        if rank <= 0:
            return None
        char_id = sg_str(item.get("character_id"))
        color = "#8f96b8"
        for card in store.sg_cards or [ ]:
            if card.get("id") == char_id:
                color = card.get("color") or color
        return {
            "rank": rank,
            "rank_color": sg_rank_colors.get(rank, gui.sg_plum),
            "student_id": sg_esc(sg_str(item.get("student_id"))),
            "name": sg_esc(sg_str(item.get("name")).strip()),
            "character": sg_esc(sg_str(item.get("character_name"))),
            "color": color,
            "score": sg_num(item.get("score"), 0.0),
            "band": sg_esc(sg_str(item.get("band"))),
            "you": bool(item.get("you")),
        }

    def sg_build_board(data):
        """서버가 준 순위표를 화면용 값으로."""
        rows = [ ]
        for item in data.get("rows") or [ ]:
            row = sg_board_row(item)
            if row is not None:
                rows.append(row)
        you = sg_board_row(data.get("you"))
        date = sg_str(data.get("date"))
        parts = date.split("-")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            date = "%d월 %d일" % (int(parts[1]), int(parts[2]))
        return {
            "date": sg_esc(date),
            "count": max(0, sg_int(data.get("count"), len(rows))),
            "rows": rows,
            # 내 줄이 위 줄들 안에 없으면 따로 한 줄 더 보인다
            "you_below": you if you is not None and not any(r["you"] for r in rows) else None,
            # 이번 판의 호감도. 같은 학번의 더 높은 기록이 있으면 순위에는 그 기록이 들어간다
            "this_game": sg_num(data.get("this_game"), None),
            "best": you["score"] if you is not None else None,
        }


## 학번과 이름 입력 ##########################################################

style sg_rank_hint:
    font gui.interface_text_font
    size 17
    color "#a07d98"
    xalign 0.5

style sg_rank_error:
    font gui.interface_text_font
    size 18
    color "#d63f5c"
    xalign 0.5

style sg_name_box:
    xsize 300
    padding (20, 12, 20, 12)
    background sg_panel(14, "#ffffff", 1.0, "#ffc3d9", 1.0)

style sg_field_label:
    font gui.sg_cute_font
    size 20
    color gui.sg_plum
    yalign 0.5
    min_width 54

## 입력칸 하나. value 는 SgSidValue 또는 SgPersonValue. 칸을 누르면 그 칸에 글이 들어간다
screen sg_rank_field(label, value, text, length, hint, field_id):

    hbox:
        xalign 0.5
        spacing 12

        text label style "sg_field_label"

        button:
            id field_id
            style "sg_name_box"
            action value.Enable()

            fixed:
                xfill True
                yfit True

                if not text:
                    text hint style "sg_placeholder_text"

                input:
                    style "sg_input"
                    value value
                    length length

screen sg_rank_entry(score, error=""):

    modal True
    zorder 60

    add Solid("#4a2a4880")

    frame:
        style "sg_modal_panel"
        xminimum 560

        vbox:
            xalign 0.5
            spacing 14

            text "순위표에 올리기" style "sg_modal_title"

            text ("최종 호감도 %s" % sg_score_text(score)) style "sg_modal_text" xalign 0.5

            text "상품을 드리려고 학번과 이름을 받아요. 이 컴퓨터에만 저장돼요." style "sg_rank_hint"
            text "순위표에는 이름 가운데 글자를 가려서 보여 줘요. (김민수 → 김*수)" style "sg_rank_hint"

            null height 2

            use sg_rank_field("학번", SgSidValue(), sg_rank_sid, sg_sid_max, "숫자만", "sg_rank_sid")
            use sg_rank_field("이름", SgPersonValue(), sg_rank_person, sg_person_max, "이름", "sg_rank_person")

            if error:
                text error style "sg_rank_error"

            hbox:
                xalign 0.5
                spacing 0

                textbutton "올리기":
                    style "sg_primary"
                    sensitive sg_rank_ready()
                    action Return(("rank", sg_rank_sid.strip(), sg_rank_person.strip()))
                textbutton "건너뛰기" style "sg_secondary" action Return(("skip",))


## 순위표 ####################################################################

style sg_rank_title:
    font gui.sg_cute_font
    size 34
    color gui.sg_pink_deep
    xalign 0.5

style sg_rank_sub:
    font gui.interface_text_font
    size 17
    color "#a07d98"
    xalign 0.5

style sg_rank_row:
    xsize 680
    ysize 40
    padding (18, 0, 22, 0)
    background sg_panel(14, "#fff7fb", 1.0, "#ffe0ec", 1.0)

style sg_rank_row_you is sg_rank_row:
    background sg_panel(14, "#ffe3ef", 1.0, gui.sg_pink, 1.0)

style sg_rank_cell:
    font gui.interface_text_font
    size 19
    color gui.sg_plum
    yalign 0.5

## 칸 너비는 min_width 로 맞춘다. 글(text)에 xsize 를 주면 칸이 고정되지 않아 줄마다 어긋났다
style sg_rank_num is sg_rank_cell:
    font gui.sg_cute_font
    size 22
    min_width 64

style sg_rank_score is sg_rank_cell:
    font gui.sg_cute_font
    size 22
    color gui.sg_pink_deep
    min_width 84
    textalign 1.0

## 순위표 한 줄
screen sg_rank_row(r):

    frame:
        style ("sg_rank_row_you" if r["you"] else "sg_rank_row")

        hbox:
            yalign 0.5
            spacing 10

            text ("%d위" % r["rank"]) style "sg_rank_num" color r["rank_color"]
            text r["student_id"] style "sg_rank_cell" min_width 96 bold r["you"]
            text r["name"] style "sg_rank_cell" min_width 130 bold r["you"]
            text r["character"] style "sg_rank_cell" min_width 120 color sg_on_light(r["color"])
            text r["band"] style "sg_rank_cell" min_width 70 size 16 color "#a07d98"
            text sg_score_text(r["score"]) style "sg_rank_score"

## b는 sg_build_board 가 만든 값이다. after_game 이 참이면 엔딩 뒤에 띄운 것이라 다음 판 단추를 준다.
## 돌려주는 값: "again"(같은 캐릭터로 다시), "other"(첫 화면), "close"(첫 화면에서 연 순위표 닫기)
screen sg_ranking(b, after_game=False):

    modal True
    zorder 60

    add Solid("#4a2a48b3")

    frame:
        xalign 0.5
        yalign 0.5
        xsize 800
        padding (60, 34, 60, 30)
        background sg_gal("card", 40)

        vbox:
            xalign 0.5
            spacing 6

            text "오늘의 순위" style "sg_rank_title"
            text ("%s · %d명 참가 · 한 사람의 가장 높은 기록으로 매겨요" % (b["date"], b["count"])) style "sg_rank_sub"

            null height 6

            if not b["rows"]:
                text "아직 순위표에 오른 사람이 없어요." style "sg_modal_text" xalign 0.5
            else:
                vbox:
                    xalign 0.5
                    spacing 3

                    for r in b["rows"]:
                        use sg_rank_row(r)

                    if b["you_below"] is not None:
                        text "..." style "sg_rank_sub"
                        use sg_rank_row(b["you_below"])

            ## 이번 판보다 높은 내 기록이 있으면 알려 준다
            if b["this_game"] is not None and b["best"] is not None and b["this_game"] < b["best"]:
                text ("이번 판 %s점. 순위에는 내 가장 높은 기록 %s점이 들어가요." % (sg_score_text(b["this_game"]), sg_score_text(b["best"]))):
                    style "sg_rank_sub"

            null height 6

            hbox:
                xalign 0.5
                spacing 0

                if after_game:
                    textbutton "다시 하기" style "sg_primary" action Return("again")
                    textbutton "다른 캐릭터 고르기" style "sg_secondary" action Return("other")
                else:
                    textbutton "닫기" style "sg_primary" action Return("close")

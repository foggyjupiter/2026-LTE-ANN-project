## 소개팅 화면의 뼈대.
##
##   1. 서버에서 온 글을 안전하게 만들기 (sg_esc)
##   2. 색 고르기
##   3. 서버 부르기 (renpy.fetch)
##   4. 서버가 준 턴과 엔딩을 화면용 값으로 바꾸기
##   5. 무대: 배경과 스탠딩을 master 레이어에 올리기
##   6. 연출 부르기 (sg_fx.rpy가 있으면)
##   7. 입력 없음 감시
##
## 대화 로직(점수, 장치, 엔딩 등급)은 여기에 없다. 전부 서버가 정해서 보내 준다.


################################################################################
## 판의 상태
################################################################################

default sg_cards = [ ]            # 고르기 화면의 캐릭터 카드. 서버에서 한 번 받아 둔다
default sg_char = None            # 지금 판의 캐릭터 카드
default sg_session = None         # 서버가 준 판 id
default sg_turn = None            # 서버가 준 마지막 턴
default sg_view = None            # 그 턴을 화면용으로 바꾼 값 (sg_build_view)
default sg_first_stage = "say"    # 대화 화면을 어느 단계부터 보여 줄지
default sg_answer = None          # 대화 화면이 돌려준 값: ("reply", 글) 또는 ("finish",)
default sg_result = None          # 마지막 서버 호출의 결과 (SgResult)
default sg_end_view = None        # 엔딩을 화면용으로 바꾼 값 (sg_build_ending)

default sg_place = ""             # 등장 장소. 첫 턴에만 온다
default sg_progress = "등장"      # 진행 표시: "등장", "답 3/10"
default sg_turn_no = 0
default sg_total_turns = 10
default sg_score_shown = 50       # 게이지에 보이는 호감도
default sg_finale = False         # 마지막 답까지 왔는가

default sg_inner_log = [ ]        # 턴마다, 속마음이 가려져 나왔으면 그 가려진 글(서버가 준 그대로), 아니면 None
default sg_score_log = [ ]        # 턴마다(등장이 0번) 그 턴을 반영한 호감도. 엔딩의 호감도 곡선에 쓴다
default sg_masked_seen = False    # 가려진 속마음이 한 번이라도 나왔는가

default sg_typed = ""             # 직접 말하기 입력칸의 글
default sg_in_play = False        # 고르기 화면이 아닌 곳에 있는가 (입력 없음 감시가 본다)
default sg_last_input = 0.0       # 마지막 입력이 들어온 시각


init -5 python:

    import re
    import time
    import urllib.parse

    import pygame_sdl2

    ## 주의: Ren'Py의 스크립트 안에서는 list 와 dict 라는 이름이 되감기용 자료형을 가리킨다.
    ## 서버의 JSON에서 온 보통 리스트와 딕셔너리는 isinstance(x, list) 로 걸러지지 않으므로
    ## 이 파일에서는 python_list 와 python_dict 로 확인한다.

    ############################################################################
    ## 1. 서버에서 온 글
    ############################################################################

    def sg_esc(value):
        """서버에서 온 글을 화면에 그대로 찍히는 Ren'Py 글로 바꾼다.

        Ren'Py는 "["를 변수 끼우기로, "{"를 글자 꾸미기 표시로 읽는다. 모델이 쓴 글에는
        이 글자들이 들어올 수 있으므로(" [출처 필요]"는 반드시 들어온다) 겹쳐 써서 막는다.
        서버에서 온 글은 화면에 넣기 전에 반드시 이 함수를 거친다. 다른 곳에서 따로 막지 않는다.
        """
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        return value.replace("[", "[[").replace("{", "{{")

    def sg_str(value):
        """문자열이 아니면 빈 문자열."""
        return value if isinstance(value, str) else ""

    def sg_int(value, fallback=0):
        """정수가 아니면 fallback."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return fallback
        try:
            return int(value)
        except (ValueError, OverflowError):
            return fallback

    ############################################################################
    ## 2. 색
    ############################################################################

    SG_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

    def sg_color(value, fallback="#5a6288"):
        """서버가 준 대표색. "#RRGGBB" 꼴이 아니면 fallback."""
        if isinstance(value, str) and SG_COLOR.match(value):
            return value
        return fallback

    def sg_lum(color):
        """색의 밝기. 0(검정)에서 1(흰색)."""
        r, g, b = Color(color).rgb
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def sg_ink_on(color):
        """이 색을 바탕으로 깔았을 때 위에 올릴 글자색."""
        return gui.sg_ink if sg_lum(color) > 0.55 else "#ffffff"

    def sg_on_dark(color):
        """어두운 바탕 위에서 테두리나 글자로 쓸 색. 너무 어두우면 밝힌다."""
        if sg_lum(color) < 0.28:
            return Color(color).tint(0.45).hexcode
        return color

    def sg_on_light(color):
        """밝은 바탕 위에서 테두리나 글자로 쓸 색. 너무 밝으면 어둡게 한다."""
        if sg_lum(color) > 0.5:
            return Color(color).shade(0.62).hexcode
        return color

    ############################################################################
    ## 3. 서버 부르기
    ############################################################################

    SG_MSG_DOWN = "서버에 연결할 수 없습니다.\n서버를 켠 터미널을 확인해 주세요."
    SG_MSG_SLOW = "서버의 답이 너무 늦습니다.\n잠시 뒤에 다시 시도해 주세요."
    SG_MSG_BROKEN = "서버의 답을 읽을 수 없습니다.\n서버를 켠 터미널을 확인해 주세요."
    SG_MSG_GONE = "이 판을 찾을 수 없습니다.\n처음부터 다시 시작해 주세요."

    class SgResult(object):
        """서버 호출 하나의 결과.

        ok       성공했는가
        status   HTTP 상태 코드. 연결 실패와 시간 초과는 0, 읽을 수 없는 답은 -1
        data     성공했을 때 서버가 준 JSON
        message  실패했을 때 화면에 보일 안내. 이미 sg_esc를 거친 글이다
        """

        def __init__(self, ok, status=200, data=None, message=""):
            self.ok = ok
            self.status = status
            self.data = data
            self.message = message

    def sg_api(path, body=None, method=None):
        """서버의 API 하나를 부른다. 예외를 던지지 않고 SgResult를 돌려준다.

        renpy.fetch는 답을 기다리는 동안 renpy.pause를 되풀이해서 화면이 멈추지 않는다.
        그래서 부르기 전에 기다리는 화면을 띄워 두면 그 화면이 계속 움직인다.
        """
        try:
            data = renpy.fetch(sg_server_url + path, method=method, json=body,
                               timeout=sg_timeout, result="json")
        except renpy.FetchError as error:
            # FetchError.status_code 는 오류 문장에서 세 자리 숫자를 아무거나 집어 오기 때문에
            # ("127.0.0.1"의 127 등) 믿을 수 없다. requests가 준 원래 예외에서 읽는다.
            cause = getattr(error, "original_exception", None)
            response = getattr(cause, "response", None)
            status = sg_int(getattr(response, "status_code", 0))
            if response is not None and status:
                message = ""
                try:
                    payload = response.json()
                    if isinstance(payload, python_dict):
                        message = sg_str(payload.get("error"))
                except Exception:
                    message = ""
                if not message:
                    message = "서버가 요청을 처리하지 못했습니다. (오류 %d)" % status
                return SgResult(False, status, None, sg_esc(message))
            if cause is None or isinstance(cause, ValueError):
                return SgResult(False, -1, None, SG_MSG_BROKEN)   # JSON이 아닌 답
            if "timeout" in type(cause).__name__.lower():
                return SgResult(False, 0, None, SG_MSG_SLOW)
            return SgResult(False, 0, None, SG_MSG_DOWN)
        return SgResult(True, 200, data, "")

    def sg_request(path, body=None, method=None, check=None, min_wait=0.0):
        """sg_api를 부르고, 답의 모양을 check로 확인하고, 적어도 min_wait초는 기다린다."""
        started = time.time()
        result = sg_api(path, body, method)
        if result.ok and check is not None and not check(result.data):
            result = SgResult(False, -1, None, SG_MSG_BROKEN)
        left = min_wait - (time.time() - started)
        if left > 0:
            renpy.pause(left, hard=True)
        return result

    def sg_is_turn(data):
        return isinstance(data, python_dict) and isinstance(data.get("say"), str)

    def sg_is_session(data):
        return (isinstance(data, python_dict) and isinstance(data.get("session_id"), str)
                and data.get("session_id") and sg_is_turn(data.get("turn")))

    def sg_is_finish(data):
        return isinstance(data, python_dict) and isinstance(data.get("ending"), python_dict)

    def sg_session_path(action):
        """/api/session/<id>/<action>"""
        return "/api/session/%s/%s" % (urllib.parse.quote(sg_str(store.sg_session), safe=""), action)

    def sg_fetch_cards():
        """GET /api/characters. 성공하면 data가 카드 목록이다."""
        result = sg_request("/api/characters")
        if not result.ok:
            return result
        cards = [ ]
        for item in result.data if isinstance(result.data, python_list) else [ ]:
            if not isinstance(item, python_dict) or not sg_str(item.get("id")):
                continue
            cards.append({
                "id": item["id"],
                "name": sg_str(item.get("name")) or item["id"],
                "attribute": sg_str(item.get("attribute")),
                "motif": sg_str(item.get("motif")),
                "intro": sg_str(item.get("intro")),
                "color": sg_color(item.get("color")),
            })
        if not cards:
            return SgResult(False, -1, None, SG_MSG_BROKEN)
        return SgResult(True, 200, cards, "")

    ############################################################################
    ## 4. 턴과 엔딩을 화면용 값으로
    ############################################################################

    SG_CITE = re.compile(r"\s?\[출처 필요\]")

    # 형광펜: 글자 둘레에 두꺼운 노란 테두리를 둘러서 칠한 것처럼 보이게 한다.
    # sg_say_text 스타일에 투명한 테두리가 깔려 있고, 여기서 그 색만 바꾼다.
    SG_HL_OPEN = "{outlinecolor=#ffe14d}{color=#171b36}"
    SG_HL_CLOSE = "{/color}{/outlinecolor}"

    def sg_mark_quotes(text, quotes):
        """text를 (글, 칠할지) 조각으로 나눈다. quotes에 든 글귀가 칠할 조각이다.

        sogaeting/web/app.js 의 appendHighlighted 와 같은 규칙이다.
        """
        pieces = [ ]
        rest = text
        while rest:
            best_at, best = -1, None
            for quote in quotes:
                at = rest.find(quote)
                if at != -1 and (best is None or at < best_at):
                    best_at, best = at, quote
            if best is None:
                pieces.append((rest, False))
                break
            if best_at > 0:
                pieces.append((rest[:best_at], False))
            pieces.append((best, True))
            rest = rest[best_at + len(best):]
        return pieces

    def sg_say_markup(turn):
        """대사에 출처 딱지와 형광펜을 입힌 Ren'Py 글. app.js 의 decorateSay 와 같은 규칙이다."""
        extras = turn.get("extras") if isinstance(turn.get("extras"), python_dict) else { }
        text = extras.get("say_marked")
        if not isinstance(text, str):
            text = sg_str(turn.get("say"))
        quotes = extras.get("highlights")
        quotes = [ q for q in quotes if isinstance(q, str) and q ] if isinstance(quotes, python_list) else [ ]
        out = [ ]
        parts = SG_CITE.split(text)
        for index, part in enumerate(parts):
            for piece, marked in sg_mark_quotes(part, quotes):
                if marked:
                    out.append(SG_HL_OPEN + sg_esc(piece) + SG_HL_CLOSE)
                else:
                    out.append(sg_esc(piece))
            if index < len(parts) - 1:
                out.append("{image=sg_cite}")
        return "".join(out)

    def sg_text_height(markup, style, width, size):
        """글을 width 폭에 size 크기로 썼을 때의 높이."""
        try:
            return Text(markup, style=style, size=size).size(width, 4096)[1]
        except Exception:
            # 크기를 잴 수 없으면 글자 수로 어림한다
            return (len(markup) * size / float(width) + 1) * size * 1.5

    def sg_fit_size(markup, style, width, height, sizes):
        """글이 width x height 안에 들어가는 가장 큰 글자 크기를 sizes에서 고른다."""
        for size in sizes:
            if sg_text_height(markup, style, width, size) <= height:
                return size
        return sizes[-1]

    def sg_curve_height(epilogue, epilogue_size, best, best_size):
        """엔딩 카드에 넣을 호감도 곡선의 높이. 후일담과 명대사가 길수록 낮춰서 아래 단추와 부딪치지 않게 한다.

        기준: 후일담 두 줄(62)과 명대사 한 줄(29)일 때 곡선 아래에 217픽셀까지 쓸 수 있었다(단추까지 20 남김).
        후일담은 112, 명대사는 78을 넘지 않게 글자 크기를 고르므로 가장 길 때도 98픽셀은 남는다.
        """
        epi_h = sg_text_height(epilogue, "sg_end_text", 660, epilogue_size) if epilogue else 0
        best_h = sg_text_height(best, "sg_end_text", 620, best_size) if best else 0
        extra = max(0, epi_h - 62) + max(0, best_h - 29)
        return int(max(80, min(170, 197 - extra)))

    def sg_popup_look(popup, wild):
        """호감도 변화 글자의 색과 크기."""
        if popup == "NaN":
            color = gui.sg_violet
        elif popup.startswith("+"):
            color = gui.sg_pink
        elif popup.startswith("-") or popup.startswith("−"):
            color = gui.sg_blue
        else:
            color = "#8a93b8"
        n = len(popup)
        size = 64 if n <= 4 else 52 if n <= 7 else 42 if n <= 10 else 34 if n <= 13 else 26
        return color, size

    def sg_build_view(turn):
        """서버가 준 턴(dict)을 화면이 그대로 그릴 값으로 바꾼다. 글은 여기서 전부 sg_esc를 거친다."""
        extras = turn.get("extras") if isinstance(turn.get("extras"), python_dict) else { }
        fallback = bool(turn.get("fallback"))
        finale = bool(turn.get("finale"))
        turn_no = max(0, sg_int(turn.get("turn")))
        total = max(1, sg_int(turn.get("total_turns"), 10))

        narration = sg_str(turn.get("narration")).strip()
        heard = sg_str(turn.get("heard")).strip()
        masked = extras.get("inner_masked") if isinstance(extras.get("inner_masked"), str) else None
        inner = (masked if masked is not None else sg_str(turn.get("inner"))).strip()

        # 대체 대사는 괄호로 싸인 지문 한 줄이다. 점수 표시가 없다
        popup = turn.get("popup")
        if fallback or popup is None:
            popup = None
        else:
            popup = str(popup)
        popup_color, popup_size = sg_popup_look(popup, "popup" in extras) if popup else ("#ffffff", 40)

        choices = turn.get("choices")
        choices = [ c.strip() for c in choices if isinstance(c, str) and c.strip() ] if isinstance(choices, python_list) else [ ]
        if finale:
            choices = [ ]

        say = sg_esc(sg_str(turn.get("say"))) if fallback else sg_say_markup(turn)
        say_style = "sg_narration_text" if fallback else "sg_say_text"
        inner_markup = sg_esc(inner)

        stages = [ ]
        if heard:
            stages.append("heard")
        if narration:
            stages.append("narration")
        stages.append("say")
        stages.append("finale" if finale else "choices")

        return {
            "turn": turn_no,
            "total": total,
            "progress": "등장" if turn_no == 0 else "답 %d/%d" % (turn_no, total),
            "stages": stages,
            "face": turn.get("face") if turn.get("face") in sg_faces else "neutral",
            "score": max(0, min(100, sg_int(turn.get("score"), 50))),
            "fallback": fallback,
            "finale": finale,
            "heard": sg_esc(heard),
            "narration": sg_esc(narration),
            "narration_size": sg_fit_size(sg_esc(narration), "sg_narration_text", 1092, 112, (24, 22, 20, 18)),
            "say": say,
            "say_style": say_style,
            "say_size": sg_fit_size(say, say_style, 1092, 112, (26, 24, 22, 20, 18, 16)),
            "inner": inner_markup,
            "inner_size": sg_fit_size(inner_markup, "sg_bubble_text", 254, 250, (19, 17, 15, 13)),
            "masked": masked is not None,
            "masked_raw": masked.strip() if masked is not None else None,   # 엔딩에서 원문과 나란히 보여 준다
            "popup": sg_esc(popup) if popup else "",
            "popup_color": popup_color,
            "popup_size": popup_size,
            "popup_wild": "popup" in extras,
            "reason": sg_esc(sg_str(turn.get("reason")).strip()),
            "notes": [ sg_esc(n) for n in (turn.get("notes") if isinstance(turn.get("notes"), python_list) else [ ])
                       if isinstance(n, str) and n ],
            # label은 화면에 찍을 글, raw는 서버에 그대로 보낼 글
            "choices": [ { "label": sg_esc(c), "raw": c } for c in choices[:3] ],
        }

    def sg_next_stage(view, stage):
        """대화 화면에서 눌렀을 때 넘어갈 다음 단계. 더 넘어갈 곳이 없으면 None."""
        stages = view["stages"]
        if stage in stages:
            index = stages.index(stage)
            if index + 1 < len(stages):
                return stages[index + 1]
        return None

    def sg_build_ending(ending):
        """서버가 준 엔딩(dict)을 화면용 값으로 바꾼다."""
        inners = ending.get("inners")
        inners = [ sg_str(s) for s in inners ] if isinstance(inners, python_list) else [ ]
        reveal = [ ]
        if store.sg_masked_seen:
            # 가려진 속마음이 나온 판만 원문을 공개한다. 화면에 보였던 가려진 글을 나란히 둔다
            paired = len(store.sg_inner_log) == len(inners)
            for index, text in enumerate(inners):
                if not text:
                    continue
                masked = store.sg_inner_log[index] if paired else None
                reveal.append({
                    "label": "등장" if index == 0 else "답 %d" % index,
                    "masked": sg_esc(masked) if masked else "",
                    "text": sg_esc(text),
                })
        band_id = sg_str(ending.get("band_id"))
        title = sg_esc(sg_str(ending.get("title")).strip())
        epilogue = sg_esc(sg_str(ending.get("epilogue")).strip())
        best = sg_esc(sg_str(ending.get("best_line")).strip())
        return {
            "name": sg_esc(sg_str(ending.get("character_name")) or (store.sg_char or { }).get("name", "")),
            "band_id": band_id,
            "band": sg_esc(sg_str(ending.get("band_name"))),
            "band_color": {
                "great": gui.sg_pink, "good": "#ff9838", "soso": "#7c86ad",
                "bad": gui.sg_blue, "worst": "#6a5a9c",
            }.get(band_id, "#7c86ad"),
            "title": title,
            "title_size": sg_fit_size(title, "sg_end_title", 570, 48, (36, 32, 28, 24, 20)),
            "epilogue": epilogue,
            "epilogue_size": sg_fit_size(epilogue, "sg_end_text", 660, 112, (20, 18, 16, 14)),
            "nickname": sg_esc(sg_str(ending.get("nickname")).strip()),
            "score": max(0, min(100, sg_int(ending.get("score"), 50))),
            "best": best,
            "best_size": sg_fit_size(best, "sg_end_text", 620, 78, (18, 16, 14, 12)),
            "early": bool(ending.get("early")),
            "reveal": reveal,
            "curve": [ max(0, min(100, sg_int(s, 50))) for s in store.sg_score_log ],
            "total": max(1, sg_int(store.sg_total_turns, 10)),
            # 곡선 그림은 엔딩마다 한 번만 만든다. 화면이 다시 그려질 때마다 만들면 그리는 움직임이 처음부터 되풀이된다
            "curve_box": sg_curve([ max(0, min(100, sg_int(s, 50))) for s in store.sg_score_log ],
                                  max(1, sg_int(store.sg_total_turns, 10)),
                                  height=sg_curve_height(
                                      epilogue, sg_fit_size(epilogue, "sg_end_text", 660, 112, (20, 18, 16, 14)),
                                      best, sg_fit_size(best, "sg_end_text", 620, 78, (18, 16, 14, 12)))),
        }

    ############################################################################
    ## 5. 무대
    ############################################################################
    ##
    ## 배경과 스탠딩은 master 레이어에 올린다. 연출 담당이 master 레이어 전체에
    ## 흔들림, 줌, 흑백을 걸기 때문이다. 대사창 같은 UI는 screens 레이어에 둔다.
    ##
    ## 스탠딩의 움직임, 만화 기호, 배경의 느린 움직임, 장소 제목 카드는 다른 파일(sg_stage.rpy)이
    ## 맡는다. 그 파일이 없어도 게임은 돌아간다(가만히 선 그림만 나온다).

    def sg_stage_call(name, *args, **kwargs):
        """sg_stage.rpy 의 함수를 부른다. 그 파일이 없으면 아무 일도 하지 않고 None 을 돌려준다."""
        f = getattr(store, name, None)
        if f is None:
            return None
        return f(*args, **kwargs)

    def sg_stage_trans(name, fallback):
        """sg_stage.rpy 가 정한 장면 전환. 없으면 fallback."""
        return getattr(store, "sg_stage_trans_" + name, None) or fallback

    def sg_show_bg(key):
        """배경을 바꾼다. 무대에 있던 것은 모두 치운다."""
        renpy.scene("master")
        sg_stage_call("sg_stage_reset")
        renpy.show("sg_bg", what=sg_bg_image(key),
                   at_list=sg_stage_call("sg_stage_bg_at") or [ ], layer="master")

    def sg_show_char(char_id, face, at=None):
        """스탠딩을 세우거나 표정을 바꾼다. 움직임(숨쉬기, 등장, 표정 동작)은 sg_stage.rpy 가 고른다."""
        place = at or store.sg_char_center
        renpy.show("sg_char", what=sg_sprite_image(char_id, face),
                   at_list=sg_stage_call("sg_stage_char_at", face, place) or [ place ], layer="master")

    def sg_hide_play_screens():
        for name in ("sg_hud", "sg_wait", "sg_wait_start", "sg_wait_reply", "sg_confirm"):
            renpy.hide_screen(name)

    def sg_enter_select():
        """고르기 화면으로 들어간다. 하던 판은 버린다."""
        sg_clear_fx()
        sg_hide_play_screens()
        store.sg_in_play = False
        store.sg_session = None
        store.sg_turn = None
        store.sg_view = None
        sg_show_bg(sg_default_bg)
        renpy.transition(sg_stage_trans("home", Dissolve(0.25)))

    def sg_enter_game():
        """새 판을 시작하기 직전. 판의 상태를 처음으로 돌린다."""
        sg_clear_fx()
        sg_hide_play_screens()
        store.sg_in_play = True
        store.sg_last_input = time.time()
        store.sg_session = None
        store.sg_turn = None
        store.sg_view = None
        store.sg_end_view = None
        store.sg_place = ""
        store.sg_progress = "등장"
        store.sg_turn_no = 0
        store.sg_score_shown = 50
        store.sg_finale = False
        store.sg_inner_log = [ ]
        store.sg_score_log = [ ]
        store.sg_masked_seen = False
        store.sg_typed = ""
        sg_show_bg(sg_default_bg)
        renpy.transition(Dissolve(0.25))

    def sg_enter_turn(turn):
        """턴 하나를 무대에 올린다: 화면용 값, 진행 표시, 배경, 표정, 연출."""
        view = sg_build_view(turn)
        store.sg_view = view
        store.sg_first_stage = view["stages"][0]
        store.sg_turn_no = view["turn"]
        store.sg_total_turns = view["total"]
        store.sg_progress = view["progress"]
        store.sg_finale = view["finale"]
        store.sg_typed = ""
        store.sg_inner_log.append(view["masked_raw"])
        # 턴 번호 자리에 넣는다. 다시 시도해서 같은 턴이 두 번 와도 점이 늘지 않는다
        store.sg_score_log = store.sg_score_log[:view["turn"]] + [ view["score"] ]
        if view["masked"]:
            store.sg_masked_seen = True
        # 점수는 대사가 나올 때 움직인다. 대사부터 시작하는 턴이면 지금 움직인다
        if store.sg_first_stage == "say":
            store.sg_score_shown = view["score"]
            sg_sound("sg_sfx_score", view["popup"])

        place = sg_str(turn.get("place"))
        first = view["turn"] == 0
        if first:                  # 등장: 장소에 맞는 배경으로 바꾼다
            store.sg_place = place
            sg_show_bg(sg_bg_key(place))
        sg_show_char(store.sg_char["id"], view["face"])
        # 표정과 호감도 변화에 맞는 만화 기호. 등장 턴이면 장소 제목 카드도 뜬다
        sg_stage_call("sg_stage_turn", view["face"], sg_int(turn.get("change")),
                      first=first, fallback=view["fallback"], place=place, score=view["score"])
        # 레이어를 지정한 전환(layer="master")은 쓰지 않는다. 시험 도구가 그 전환이
        # 끝난 것을 알아채지 못해서 다음 클릭에서 멈춘다.
        if first:
            renpy.transition(sg_stage_trans("scene", Dissolve(0.4)))
        else:
            renpy.transition(sg_stage_trans("turn", Dissolve(0.2)))

        fx = turn.get("fx")
        fx = [ name for name in fx if isinstance(name, str) ] if isinstance(fx, python_list) else [ ]
        sg_call_fx(fx, sg_str(turn.get("narration")))

    def sg_enter_ending(ending):
        """엔딩 화면으로 들어간다. 연출을 걷고 스탠딩을 왼쪽으로 옮긴다."""
        sg_clear_fx()
        sg_hide_play_screens()
        store.sg_end_view = sg_build_ending(ending)
        face = sg_band_face.get(store.sg_end_view["band_id"], "neutral")
        sg_show_char(store.sg_char["id"], face, at=store.sg_char_left)
        sg_stage_call("sg_stage_ending", store.sg_end_view["band_id"])
        renpy.transition(sg_stage_trans("ending", Dissolve(0.3)))
        sg_sound("sg_sfx_ending", store.sg_end_view["band_id"])

    ############################################################################
    ## 6. 연출
    ############################################################################
    ##
    ## 연출은 다른 파일(sg_fx.rpy)이 맡는다. 그 파일이 없어도 게임은 돌아간다.

    def sg_sound(name, *args):
        """소리를 낸다. 소리는 다른 파일(sg_audio.rpy)이 맡는다. 그 파일이 없어도 게임은 돌아간다."""
        f = getattr(store, name, None)
        if f is None:
            return
        try:
            f(*args)
        except Exception:
            pass

    def sg_call_fx(names, narration=""):
        f = getattr(store, "sg_fx_play", None)
        if f is not None:
            f(list(names or []), narration=narration or "")

    def sg_clear_fx():
        f = getattr(store, "sg_fx_clear", None)
        if f is not None:
            f()

    ############################################################################
    ## 7. 입력 없음 감시
    ############################################################################

    SG_INPUT_EVENTS = (
        pygame_sdl2.MOUSEBUTTONDOWN, pygame_sdl2.KEYDOWN, pygame_sdl2.TEXTINPUT,
        pygame_sdl2.TEXTEDITING, pygame_sdl2.FINGERDOWN,
    )

    class SgIdleWatch(renpy.Displayable):
        """마우스 단추나 글쇠가 눌릴 때마다 그 시각을 적는다. 아무것도 그리지 않는다."""

        def render(self, width, height, st, at):
            return renpy.Render(0, 0)

        def event(self, ev, x, y, st):
            if ev.type in SG_INPUT_EVENTS:
                store.sg_last_input = time.time()
            return None

    def sg_idle_tick():
        """판을 하는 중에 sg_idle_seconds초 동안 입력이 없었으면 고르기 화면으로 보낸다."""
        if store.sg_in_play and time.time() - store.sg_last_input >= sg_idle_seconds:
            renpy.jump("sg_idle")

    ############################################################################
    ## 직접 말하기 입력칸
    ############################################################################

    class SgTypedValue(InputValue, FieldEquality):
        """직접 말하기 입력칸의 글을 store.sg_typed 에 둔다. Enter를 누르면 그 글을 보낸다."""

        equality_fields = ( )
        identity_fields = ( )

        default = True
        editable = True
        returnable = True

        def get_text(self):
            return store.sg_typed

        def set_text(self, s):
            store.sg_typed = s
            renpy.restart_interaction()

        def enter(self):
            text = store.sg_typed.strip()
            if text:
                sg_sound("sg_sfx", "send")
                return ("reply", text)
            raise renpy.IgnoreEvent()

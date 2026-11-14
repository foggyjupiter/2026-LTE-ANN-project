## sg_stage.rpy: 무대 위의 연기.
##
##   1. 스탠딩의 움직임: 숨쉬기, 등장, 표정이 바뀔 때의 짧은 동작
##   2. 만화 기호: 머리 근처에 톡 튀어나왔다가 사라지는 하트, 빠직, 땀방울 ...
##   3. 배경의 아주 느린 움직임
##   4. 등장 턴에 잠깐 뜨는 장소 제목 카드
##   5. 장면 전환
##
## 바깥에서 쓰는 것 (sg_core.rpy 의 무대 부분이 부른다. 이 파일이 없어도 게임은 돌아간다)
##   sg_stage_char_at(face, place)   스탠딩에 걸 transform 목록(자리, 숨쉬기, 동작)
##   sg_stage_bg_at()                배경에 걸 transform 목록
##   sg_stage_turn(face, change, first, fallback, place, score)   턴에 맞는 기호와 제목 카드
##   sg_stage_ending(band_id)        엔딩 화면에 맞는 기호
##   sg_stage_reset()                기호와 제목 카드를 치우고 표정 기억을 지운다
##
## 레이어 약속
##   스탠딩(sg_char), 배경(sg_bg), 기호(sg_emote0 ...)는 모두 master 레이어의 그림이다.
##   움직임은 그림 하나하나(태그)에 건다. "show layer master" 자리는 연출(sg_fx.rpy)의 것이라
##   여기서는 쓰지 않는다. 그래서 줌인, 흔들림 같은 연출이 걸리면 기호도 같이 움직인다.
##   제목 카드만 screens 레이어의 화면이다(대화 화면보다 아래).
##
## 기호 그림은 images/emote/*.png 에 있고 renpy/dev/make_emote_art.py 가 만든다.
## 이 파일의 이름은 전부 sg_stage 로 시작한다. 효과음은 없다.


################################################################################
## 고칠 수 있는 값
################################################################################

## 얼굴 한가운데. x는 스탠딩이 선 자리(가운데 640, 엔딩 250)에서의 거리, y는 화면 높이.
## 스탠딩 768x1152 를 0.7배로 세웠을 때 얼굴은 그림 위쪽 가운데쯤에 온다.
define sg_stage_head = (0, 225)

## 기호가 뜨는 자리. 얼굴 한가운데에서의 거리다. 얼굴을 가리지 않게 머리 둘레에만 둔다.
define sg_stage_spots = {
    "right": (168, -118),        # 머리 오른쪽 위
    "left": (-168, -118),        # 머리 왼쪽 위
    "top": (54, -168),           # 머리 위
    "right_low": (184, -6),      # 오른쪽 뺨 옆
    "left_low": (-184, -6),      # 왼쪽 뺨 옆
    "right_far": (228, -64),     # 오른쪽 조금 멀리
    "left_far": (-228, -64),     # 왼쪽 조금 멀리
    "above": (0, -217),          # 머리 꼭대기 위(세로줄이 여기서 내려온다)
}

## 기호 그림과 화면에서의 크기(그림 192픽셀에 곱하는 값).
define sg_stage_emote_art = {
    "heart": ("images/emote/heart.png", 0.46),
    "vein": ("images/emote/vein.png", 0.50),
    "sweat": ("images/emote/sweat.png", 0.48),
    "exclaim": ("images/emote/exclaim.png", 0.62),
    "question": ("images/emote/question.png", 0.56),
    "sparkle": ("images/emote/sparkle.png", 0.50),
    "steam": ("images/emote/steam.png", 0.56),
    "dots": ("images/emote/dots.png", 0.54),
    "note": ("images/emote/note.png", 0.50),
    "gloom": ("images/emote/gloom.png", 0.78),
}

## 호감도가 이만큼 움직이면 크게 움직인 것으로 본다. 서버(sogaeting/director.py의 POINTS)는 바라던 말(+2)에
## 캐릭터마다 5-8점(hit_points), 다정한 말(+1)에 2점, -1에 5점, -2에 10점을 움직이고, 여기에 반응의 세기에 따라
## 다정한 말과 내리는 말은 0.6-1.4배, 바라던 말은 설렘에 따라 0.4-1.25배를 곱한다(STRENGTH_SCALE, HIT_STRENGTH_SCALE).
## 그래서 다정한 말은 1.2-2.8점, 바라던 말은 2.0-10.0점이다. 바라던 말이라도 설렘이 약하면(1-2) 작게 오른 것으로 본다.
## 오를 때는 3점부터 크게 움직인 것으로 본다(다정한 말은 3점에 못 미친다). 내릴 때는 -1(3.0-7.0점)보다 크고 -2(6.0-14.0점)의
## 대부분이 들어오는 8로 둔다.
define sg_stage_big_up = 3
define sg_stage_big_down = 8

## 한 번에 띄우는 기호의 수.
define sg_stage_emote_max = 5

## 배경을 아주 느리게 움직일지. 눈에 거슬리면 False 로 바꾼다(배경이 가만히 깔린다).
define sg_stage_bg_move = True

## 숨쉬기: 한 번 들이쉬고 내쉬는 시간(초)과 키가 늘어나는 비율.
define sg_stage_breath_period = 4.6
define sg_stage_breath_amount = 0.009

## 동작이 끝난 뒤에 머무는 자세: 표정마다 (기울기, 아래로 내려앉는 픽셀, 크기).
define sg_stage_rest = {
    "pout": (1.3, 0, 1.0),
    "dark": (0.0, 12, 0.985),
}

## 엔딩 등급마다 띄울 기호: (기호, 자리, 움직임).
define sg_stage_band_emotes = {
    "great": [ ("heart", "right", "float"), ("heart", "left", "float"), ("heart", "top", "float") ],
    "good": [ ("note", "right", "sway"), ("sparkle", "left", "twinkle") ],
    "soso": [ ("dots", "right", "pop") ],
    "bad": [ ("vein", "right", "throb") ],
    "worst": [ ("gloom", "above", "sink") ],
}

## 장면 전환. 레이어를 지정하지 않는 전환만 쓴다(sg_core.rpy 의 주석 참고).
define sg_stage_trans_scene = Dissolve(0.5)       # 등장: 장소가 바뀐다
define sg_stage_trans_turn = Dissolve(0.2)        # 턴이 바뀔 때: 표정만 바뀐다
define sg_stage_trans_ending = Dissolve(0.6)      # 엔딩으로
define sg_stage_trans_home = Fade(0.22, 0.04, 0.42, color="#f6f2fb")   # 첫 화면으로: 하얗게 한 번 감았다 뜬다

## 지금 무대에 선 스탠딩의 표정. 같은 표정이 이어지면 큰 동작을 되풀이하지 않으려고 적어 둔다.
default sg_stage_face = None

## 대사가 나올 때까지 미뤄 둔 호감도 기호: (그때의 점수, 기호 목록, 몇 번째 태그부터 쓸지) 또는 None.
default sg_stage_later = None


################################################################################
## 1. 스탠딩의 움직임
################################################################################
##
## 스탠딩에는 transform 세 겹을 건다: 자리(sg_char_center 등) → 숨쉬기 → 동작.
## 숨쉬기와 동작은 자리(xpos 등)를 건드리지 않고 크기, 기울기, 밀어내기(offset)만 쓴다.
## transform_anchor 를 켜서 발밑 가운데(자리 transform 의 anchor)를 축으로 커지고 기운다.

init -4 python:

    import math

    def sg_stage_breathe_fn(trans, st, at):
        """숨쉬기. 아주 느리고 작게 키가 늘었다 준다.

        at 은 같은 태그로 그림을 바꿔도 이어지는 시간이다. 그래서 표정이 바뀌어도 숨이 끊기지 않는다.
        """
        k = (1.0 - math.cos(at * 2.0 * math.pi / sg_stage_breath_period)) / 2.0
        trans.yzoom = 1.0 + sg_stage_breath_amount * k
        trans.xzoom = 1.0 - sg_stage_breath_amount * 0.3 * k
        return 0

    def sg_stage_bg_fn(trans, st, at):
        """배경이 아주 느리게 다가왔다 물러난다. 조금 크게 깔아 두어서 가장자리가 드러나지 않는다."""
        k = (1.0 - math.cos(at * 2.0 * math.pi / 36.0)) / 2.0
        trans.zoom = 1.025 + 0.02 * k
        trans.xoffset = -7.0 + 14.0 * k
        return 0


transform sg_stage_breathe:
    subpixel True
    transform_anchor True
    function sg_stage_breathe_fn

## 등장: 아래에서 살짝 올라오며 나타난다.
transform sg_stage_act_enter:
    subpixel True
    transform_anchor True
    xoffset 0 yoffset 46 rotate 0 zoom 1.0 alpha 0.0
    easein 0.5 yoffset 0 alpha 1.0
    ease 0.14 yoffset 5
    ease 0.18 yoffset 0

## 같은 표정이 이어질 때: 큰 동작 없이 그 표정의 자세로 머문다.
transform sg_stage_act_keep(r=0.0, y=0, z=1.0):
    subpixel True
    transform_anchor True
    ease 0.2 xoffset 0 yoffset y rotate r zoom z alpha 1.0

## neutral: 제자리로 돌아와 작게 끄덕인다.
transform sg_stage_act_neutral:
    subpixel True
    transform_anchor True
    ease 0.22 xoffset 0 yoffset 0 rotate 0 zoom 1.0 alpha 1.0
    ease 0.12 yoffset 5
    ease 0.16 yoffset 0

## smile: 작게 폴짝.
transform sg_stage_act_smile:
    subpixel True
    transform_anchor True
    ease 0.06 xoffset 0 yoffset 0 rotate 0 zoom 1.0 alpha 1.0
    easein 0.13 yoffset -22
    easeout 0.13 yoffset 0
    easein 0.08 yoffset -8
    easeout 0.08 yoffset 0

## blush: 움찔하고 살짝 움츠렸다가 풀린다.
transform sg_stage_act_blush:
    subpixel True
    transform_anchor True
    ease 0.06 xoffset 0 yoffset 0 rotate 0 zoom 1.0 alpha 1.0
    easein 0.07 yoffset -7
    ease 0.12 yoffset 0 zoom 0.972
    linear 0.04 xoffset 3
    linear 0.05 xoffset -3
    linear 0.05 xoffset 2
    linear 0.04 xoffset 0
    pause 0.12
    ease 0.3 zoom 1.0

## pout: 홱 돌리듯 옆으로 기울이고 조금 기운 채로 머문다.
transform sg_stage_act_pout:
    subpixel True
    transform_anchor True
    ease 0.06 xoffset 0 yoffset 0 rotate 0 zoom 1.0 alpha 1.0
    easein 0.11 rotate 3.4 xoffset 8
    pause 0.26
    ease 0.3 rotate 1.3 xoffset 0

## shock: 펄쩍 뛰고 잠깐 떤다.
transform sg_stage_act_shock:
    subpixel True
    transform_anchor True
    ease 0.05 xoffset 0 yoffset 0 rotate 0 zoom 1.0 alpha 1.0
    easein 0.09 yoffset -34
    easeout 0.11 yoffset 0
    linear 0.035 xoffset 6
    linear 0.045 xoffset -6
    linear 0.045 xoffset 5
    linear 0.045 xoffset -4
    linear 0.045 xoffset 3
    linear 0.04 xoffset -2
    linear 0.03 xoffset 0

## dark: 천천히 가라앉아 그대로 머문다.
transform sg_stage_act_dark:
    subpixel True
    transform_anchor True
    ease 0.1 xoffset 0 rotate 0 alpha 1.0
    ease 0.7 yoffset 12 zoom 0.985


################################################################################
## 2. 만화 기호
################################################################################
##
## 움직임마다 transform 하나. x, y 는 화면에서의 자리, z 는 크기, delay 는 늦추는 시간.
## 같은 태그의 앞선 기호에서 값을 이어받으므로 처음에 전부 다시 정한다.

## 톡 튀어나와 잠깐 머물고 사라진다.
transform sg_stage_emote_pop(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.5 xoffset 0 yoffset 0 rotate 0
    alpha 0.0 zoom (z * 0.3)
    pause delay
    alpha 1.0
    easein 0.12 zoom (z * 1.24)
    easeout 0.08 zoom (z * 0.93)
    ease 0.07 zoom z
    pause 0.95
    ease 0.3 alpha 0.0 yoffset -12

## 튀어나와 두 번 불끈거린다. (빠직)
transform sg_stage_emote_throb(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.5 xoffset 0 yoffset 0 rotate 8
    alpha 0.0 zoom (z * 0.3)
    pause delay
    alpha 1.0
    easein 0.1 zoom (z * 1.3)
    easeout 0.08 zoom z
    pause 0.1
    ease 0.09 zoom (z * 1.2)
    ease 0.09 zoom z
    pause 0.08
    ease 0.09 zoom (z * 1.2)
    ease 0.09 zoom z
    pause 0.5
    ease 0.3 alpha 0.0

## 튀어나와 좌우로 떤다. (느낌표)
transform sg_stage_emote_shake(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.5 xoffset 0 yoffset 14 rotate 0
    alpha 0.0 zoom (z * 0.3)
    pause delay
    alpha 1.0
    easein 0.1 zoom (z * 1.3) yoffset -6
    easeout 0.08 zoom z yoffset 0
    linear 0.04 xoffset 5
    linear 0.05 xoffset -5
    linear 0.05 xoffset 4
    linear 0.05 xoffset -3
    linear 0.04 xoffset 0
    pause 0.75
    ease 0.3 alpha 0.0

## 튀어나와 갸웃갸웃 흔들린다. (음표, 물음표)
transform sg_stage_emote_sway(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.5 xoffset 0 yoffset 0 rotate -10
    alpha 0.0 zoom (z * 0.3)
    pause delay
    alpha 1.0
    easein 0.12 zoom (z * 1.2)
    easeout 0.08 zoom z
    ease 0.22 rotate 10 yoffset -5
    ease 0.22 rotate -8 yoffset 0
    ease 0.22 rotate 8 yoffset -5
    ease 0.22 rotate 0 yoffset 0
    pause 0.2
    ease 0.3 alpha 0.0 yoffset -12

## 돌면서 켜졌다가 한 번 더 빛나고 꺼진다. (반짝임)
transform sg_stage_emote_twinkle(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.5 xoffset 0 yoffset 0 rotate -40
    alpha 0.0 zoom (z * 0.2)
    pause delay
    alpha 1.0
    easein 0.18 zoom (z * 1.15) rotate 0
    ease 0.14 zoom (z * 0.8)
    ease 0.16 zoom (z * 1.08)
    ease 0.14 zoom (z * 0.86)
    ease 0.16 zoom z
    pause 0.3
    ease 0.3 alpha 0.0 zoom (z * 0.6) rotate 30

## 살랑살랑 떠오르며 사라진다. (하트 여러 개)
transform sg_stage_emote_float(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.5 xoffset 0 yoffset 26 rotate 0
    alpha 0.0 zoom (z * 0.45)
    pause delay
    parallel:
        easein 0.2 alpha 1.0 zoom (z * 1.08)
        ease 0.12 zoom z
        pause 0.75
        ease 0.4 alpha 0.0
    parallel:
        easein 1.47 yoffset -44
    parallel:
        ease 0.37 xoffset 9
        ease 0.37 xoffset -9
        ease 0.37 xoffset 7
        ease 0.36 xoffset 0

## 맺혔다가 주르륵 흘러내린다. (땀방울)
transform sg_stage_emote_drop(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.5 xoffset 0 yoffset -12 rotate 0
    alpha 0.0 zoom (z * 0.6)
    pause delay
    easein 0.14 alpha 1.0 zoom z yoffset 0
    pause 0.28
    easeout 0.55 yoffset 30
    ease 0.25 alpha 0.0 yoffset 38

## 뿌우 하고 피어올라 흩어진다. (김)
transform sg_stage_emote_puff(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.5 xoffset 0 yoffset 18 rotate 0
    alpha 0.0 zoom (z * 0.5)
    pause delay
    parallel:
        easein 0.16 alpha 1.0
        pause 0.75
        ease 0.4 alpha 0.0
    parallel:
        easein 0.22 zoom (z * 1.1)
        ease 0.16 zoom z
        ease 0.93 zoom (z * 1.12)
    parallel:
        easein 1.31 yoffset -26

## 위에서 스르르 내려와 드리웠다가 걷힌다. (우울한 세로줄)
transform sg_stage_emote_sink(x, y, z, delay=0.0):
    subpixel True
    xpos x ypos y xanchor 0.5 yanchor 0.0 xoffset 0 yoffset -22 rotate 0
    alpha 0.0 zoom z
    pause delay
    ease 0.55 alpha 1.0 yoffset 0
    pause 1.25
    ease 0.6 alpha 0.0 yoffset 10


init -4 python:

    def sg_stage_oops(where):
        """무대 연기는 조용히 실패한다(부스에서 게임이 멈추면 안 된다). log.txt 에만 남긴다.

        시험(sg_stage_demo)은 기호의 수를 세므로 여기서 삼킨 오류도 시험에서는 드러난다.
        """
        try:
            import traceback
            renpy.display.log.write("sg_stage: %s 에서 문제가 생겨 건너뛴다.", where)
            renpy.display.log.write("%s", traceback.format_exc())
        except Exception:
            pass

    def sg_stage_pick_parts(face, change=0, first=False, fallback=False):
        """표정과 호감도 변화에 맞는 기호를 고른다. (표정 기호 목록, 호감도 기호 목록)을 돌려준다.

        목록의 항목은 (기호, 자리, 움직임)이다. 표정이 먼저 기호를 정하고, 호감도가 크게
        움직였으면 하트 여러 개나 땀방울을 더한다. 뒤의 것은 호감도 숫자가 뜨는 순간에 나온다.
        """
        if fallback:
            # 대체 대사: 점수도 표정도 없는 지문 한 줄이다
            return [ ("dots", "right", "pop") ], [ ]

        up, down = change > 0, change < 0
        out = [ ]

        if face == "smile":
            out.append(("note", "right", "sway"))
            if up:
                out.append(("sparkle", "left", "twinkle"))
        elif face == "blush":
            out.append(("steam", "top", "puff"))
            if change < sg_stage_big_up:
                out.append(("heart", "right", "pop"))
        elif face == "pout":
            out.append(("vein", "right", "throb"))
            if down:
                out.append(("steam", "left", "puff"))
        elif face == "shock":
            out.append(("exclaim", "right", "shake"))
            if down:
                out.append(("sweat", "left_low", "drop"))
            elif not up and not first:
                out.append(("question", "left", "sway"))
        elif face == "dark":
            out.append(("gloom", "above", "sink"))
        else:
            # neutral
            if down:
                out.append(("sweat", "right_low", "drop"))
            elif up:
                out.append(("sparkle", "right", "twinkle"))
            elif not first:
                out.append(("dots", "right", "pop"))

        more = [ ]
        if change >= sg_stage_big_up:
            # 크게 올랐다: 하트 여러 개가 떠오른다
            more.append(("heart", "right_far", "float"))
            more.append(("heart", "left_far", "float"))
            more.append(("heart", "left", "float") if face in ("smile", "pout") else ("heart", "right", "float"))
        elif change <= -sg_stage_big_down:
            # 크게 내렸다: 땀방울, 그리고 아직 없으면 세로줄
            if not any(e[0] == "sweat" for e in out):
                more.append(("sweat", "right_low", "drop"))
            if face not in ("dark", "pout", "shock"):
                more.append(("gloom", "above", "sink"))

        # 같은 자리에 둘이 겹치지 않게 뒤에 온 것을 빈자리로 옮긴다
        seen = set()
        spare = [ "right", "left", "right_far", "left_far", "top" ]
        parts = [ ]
        left = sg_stage_emote_max
        for group in (out, more):
            placed = [ ]
            for kind, spot, move in group:
                if len(placed) >= left:
                    break
                if spot in seen:
                    free = [ s for s in spare if s not in seen ]
                    if not free:
                        continue
                    spot = free[0]
                seen.add(spot)
                placed.append((kind, spot, move))
            left -= len(placed)
            parts.append(placed)
        return parts[0], parts[1]

    def sg_stage_pick_emotes(face, change=0, first=False, fallback=False):
        """한 턴에 뜨는 기호 전부. (기호, 자리, 움직임) 목록."""
        now, later = sg_stage_pick_parts(face, change, first, fallback)
        return now + later

    def sg_stage_clear_emotes():
        """떠 있는 기호를 전부 치운다."""
        for i in range(sg_stage_emote_max):
            tag = "sg_emote%d" % i
            if renpy.showing(tag, layer="master"):
                renpy.hide(tag, layer="master")

    def sg_stage_show_emotes(emotes, cx=640, delay=0.15, step=0.14, start=0):
        """기호를 master 레이어에 띄운다.

        cx 는 스탠딩이 선 자리, delay 는 첫 기호를 늦추는 시간. start 가 0이면 떠 있던 기호를
        먼저 치우고, 0이 아니면 그 번호의 태그부터 이어서 띄운다.
        """
        try:
            if not start:
                sg_stage_clear_emotes()
            hx, hy = sg_stage_head
            for i, (kind, spot, move) in enumerate(list(emotes)[:sg_stage_emote_max - start], start):
                art = sg_stage_emote_art.get(kind)
                motion = getattr(store, "sg_stage_emote_" + move, None)
                if art is None or motion is None or spot not in sg_stage_spots or not renpy.loadable(art[0]):
                    continue
                dx, dy = sg_stage_spots[spot]
                at = motion(x=int(cx + hx + dx), y=int(hy + dy), z=art[1], delay=delay + step * (i - start))
                renpy.show("sg_emote%d" % i, what=Image(art[0]), at_list=[ at ], layer="master", zorder=5)
        except Exception:
            sg_stage_oops("sg_stage_show_emotes")

    def sg_stage_char_at(face, place):
        """스탠딩에 걸 transform 목록: 자리, 숨쉬기, 동작.

        무대에 처음 서면 등장, 표정이 바뀌면 그 표정의 동작, 같은 표정이면 큰 동작 없이 머문다.
        """
        try:
            if face not in sg_faces:
                face = "neutral"
            if not renpy.showing("sg_char", layer="master"):
                act = store.sg_stage_act_enter
            elif face == store.sg_stage_face:
                r, y, z = sg_stage_rest.get(face, (0.0, 0, 1.0))
                act = store.sg_stage_act_keep(r=r, y=y, z=z)
            else:
                act = getattr(store, "sg_stage_act_" + face)
            store.sg_stage_face = face
            return [ place, store.sg_stage_breathe, act ]
        except Exception:
            sg_stage_oops("sg_stage_char_at")
            return [ place ]

    def sg_stage_bg_at():
        """배경에 걸 transform 목록."""
        return [ store.sg_stage_bg_drift ] if sg_stage_bg_move else [ ]

    def sg_stage_turn(face, change=0, first=False, fallback=False, place="", score=None):
        """턴 하나에 맞는 기호를 띄운다. 등장 턴이면 장소 제목 카드도 띄운다.

        표정 기호는 표정이 바뀌는 지금 나온다. 호감도 기호(하트 여러 개, 땀방울, 세로줄)는
        score 를 주면 게이지가 그 점수로 움직이는 순간, 곧 대사와 호감도 숫자가 뜰 때 나온다.
        (대화 화면이 대사 단계에서 sg_score_shown 을 바꾼다. sg_stage_interact 가 그것을 본다)
        """
        try:
            now, later = sg_stage_pick_parts(face, change, first, fallback)
            store.sg_stage_later = None
            if later and score is not None and store.sg_score_shown != score:
                store.sg_stage_later = (score, later, len(now))
            else:
                now = now + later
            # 등장 턴은 스탠딩이 올라온 뒤에 기호가 나온다
            sg_stage_show_emotes(now, delay=0.6 if first else 0.15)
            renpy.hide_screen("sg_stage_title")
            if first and place:
                renpy.show_screen("sg_stage_title", place=sg_esc(place))
        except Exception:
            sg_stage_oops("sg_stage_turn")

    def sg_stage_ending(band_id):
        """엔딩 화면: 스탠딩이 왼쪽(250)으로 비켜선 뒤에 등급에 맞는 기호를 띄운다."""
        try:
            renpy.hide_screen("sg_stage_title")
            store.sg_stage_later = None
            sg_stage_show_emotes(sg_stage_band_emotes.get(band_id, [ ]), cx=250, delay=0.7)
        except Exception:
            sg_stage_oops("sg_stage_ending")

    def sg_stage_reset():
        """기호와 제목 카드를 치우고 표정 기억을 지운다. 판이 바뀔 때 부른다."""
        try:
            sg_stage_clear_emotes()
            renpy.hide_screen("sg_stage_title")
            store.sg_stage_face = None
            store.sg_stage_later = None
        except Exception:
            sg_stage_oops("sg_stage_reset")

    def sg_stage_interact():
        """미뤄 둔 호감도 기호를 게이지가 움직인 순간에 띄운다.

        화면이 새로 그려지기 시작할 때마다 불린다(config.interact_callbacks). 대화 화면이
        대사 단계로 넘어가면서 sg_score_shown 을 바꾸면 화면이 새로 그려지므로 그때 걸린다.
        """
        later = getattr(store, "sg_stage_later", None)
        if later is None:
            return
        try:
            score, emotes, start = later
            if store.sg_score_shown != score:
                return
            store.sg_stage_later = None
            sg_stage_show_emotes(emotes, delay=0.1, start=start)
        except Exception:
            store.sg_stage_later = None
            sg_stage_oops("sg_stage_interact")

    config.interact_callbacks.append(sg_stage_interact)


################################################################################
## 3. 배경
################################################################################

## 아주 느리게 다가왔다 물러나며 옆으로 조금 흐른다. 한 번 오가는 데 36초.
transform sg_stage_bg_drift:
    subpixel True
    xpos 640 ypos 360 xanchor 0.5 yanchor 0.5
    function sg_stage_bg_fn


################################################################################
## 4. 장소 제목 카드
################################################################################
##
## 등장 턴에 장소 이름이 잠깐 떴다가 사라진다. 얼굴 아래, 대사창 위에 뜬다.
## place 는 sg_esc 를 거친 글이어야 한다. 누를 수 있는 것이 없어서 클릭을 가로채지 않는다.

transform sg_stage_title_card:
    alpha 0.0 xzoom 0.86
    pause 0.25
    easein 0.4 alpha 1.0 xzoom 1.0
    pause 1.5
    ease 0.5 alpha 0.0

transform sg_stage_title_name:
    alpha 0.0 yoffset 8
    pause 0.4
    easein 0.35 alpha 1.0 yoffset 0

style sg_stage_title_text:
    font "fonts/Pretendard-Bold.otf"
    size 30
    color "#ffffff"
    kerning 5
    outlines [ (2, "#1b255999", 0, 1) ]

screen sg_stage_title(place):

    zorder 4      # 대화 화면(5)보다 아래

    timer 2.8 action Hide("sg_stage_title")

    fixed:
        xysize (720, 96)
        xpos 640 xanchor 0.5
        ypos 470 yanchor 0.5
        at sg_stage_title_card

        add "images/emote/title_band.png"
        text place style "sg_stage_title_text" xalign 0.5 yalign 0.5 at sg_stage_title_name

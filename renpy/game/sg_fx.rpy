## sg_fx.rpy: 소개팅 화면 연출 15종.
##
## 서버는 턴마다 "fx"(연출 이름 0-2개)를 준다. 이 파일은 그 이름을 받아 화면에 건다.
## 연출마다 무엇을 얼마 동안 보여 주는지는 브라우저판(sogaeting/web/fx.js, fx.css)이
## 기준이다. 겉모습은 브라우저판의 픽셀 그림이 아니라 매끄러운 미연시 연출로 만들었다.
##
## 바깥에서 쓰는 것
##   sg_fx_play(names, narration="")  연출을 건다. 앞서 걸린 것은 먼저 걷는다
##   sg_fx_clear()                    걸려 있는 연출을 전부 즉시 걷는다
##   sg_fx_focus, sg_fx_focus_size    스탠딩의 얼굴 자리. 줌인, 집중선, 스포트라이트, 암전이 쓴다
##   sg_fx_ui_top                     대사창이 시작하는 높이. 자막과 가짜 오류창이 그 위에서 가운데를 잡는다
##
## 레이어 약속
##   sg_fx   master 와 screens 사이의 레이어. 덮는 연출(꽃잎, 비, 암전 ...)을 여기에 그린다.
##           대사창은 screens 에 있으므로 연출에 가리지 않는다.
##   master  흔들림, 줌인, 흑백, 화면 깨짐은 "show layer master" 자리에 transform 을 건다.
##           연출이 끝나면 그 자리를 비운다. camera 자리는 건드리지 않는다.
##
## 연출은 클릭을 가로채지 않는다. 하나만 다르다: 가짜 오류창의 "확인" 단추는 누르면
## 그 창만 닫는다(fx.js 와 같다). 다른 곳을 누르면 평소처럼 대사가 넘어간다.
##
## 그림은 images/fx/sg_fx_*.png 에 있다. 꽃잎, 하트, 반짝이는 여러 장을 한 줄로 이어 붙인
## 그림이고 여기서 한 칸씩 잘라 쓴다.
##
## 이 파일의 이름(화면, transform, 스타일, 함수, 변수)은 전부 sg_fx 로 시작한다.
## 효과음은 없다.

init -10 python:

    ## master, transient, sg_fx, screens, overlay 순서가 된다.
    renpy.add_layer("sg_fx", below="screens", menu_clear=True, sticky=False)


## 색
define sg_fx_ink = "#1B2559"
define sg_fx_red = "#E23B4E"
define sg_fx_marker = "#FFE65A"
define sg_fx_paper = "#F4F7FB"
define sg_fx_dark = "#0B1030"

## 가짜 오류창에 지문이 없을 때 넣는 글
define sg_fx_default_error = "두근거림이 허용 범위를 넘었습니다"

## 스탠딩의 얼굴 한가운데(화면 좌표)와 그 둘레 상자의 크기.
## 스탠딩 자리가 바뀌면 화면 쪽에서 "$ sg_fx_focus = (x, y)" 로 바꾼다.
default sg_fx_focus = (640, 220)
default sg_fx_focus_size = (300, 300)

## 대사창 윗변의 높이. 이 위쪽을 무대로 본다.
default sg_fx_ui_top = 535


################################################################################
## 그림과 도구
################################################################################

init python:

    ## 한 번 만든 그림을 다시 쓴다. 이름표(key)가 같으면 같은 그림이다.
    sg_fx_cache = {}

    def sg_fx_cut(key, path, rect, zoom=1.0):
        """이어 붙인 그림(path)에서 한 칸(rect)을 잘라 zoom 배로 쓴다."""
        d = sg_fx_cache.get(key)
        if d is None:
            d = Transform(path, crop=rect, zoom=zoom)
            sg_fx_cache[key] = d
        return d

    def sg_fx_rgba(c, alpha=1.0):
        """색과 불투명도로 (r, g, b, a) 를 만든다."""
        c = renpy.easy.color(c)
        return (c[0], c[1], c[2], int(round(255 * alpha)))

    class SgFxBox(renpy.Displayable):
        """
        각진 상자. 테두리와 속, 오른쪽 아래로 떨어진 그림자를 단색으로 그린다.
        frame 과 button 의 background 로 쓴다.

        edges   왼쪽, 위, 오른쪽, 아래 테두리의 두께
        shadow  그림자가 오른쪽과 아래로 나가는 길이
        """

        def __init__(self, fill, line, edges=(4, 4, 4, 4), shadow=(0, 0), **properties):
            super(SgFxBox, self).__init__(**properties)
            self.fill = Solid(fill)
            self.line = Solid(line)
            self.edges = edges
            self.shadow = shadow

        def render(self, width, height, st, at):
            width = int(width)
            height = int(height)
            rv = renpy.Render(width, height)

            sx, sy = self.shadow
            w = max(0, width - sx)
            h = max(0, height - sy)
            left, top, right, bottom = self.edges

            line = renpy.render(self.line, w, h, st, at)
            if sx or sy:
                rv.blit(line, (sx, sy))
            rv.blit(line, (0, 0))
            rv.blit(renpy.render(self.fill, max(0, w - left - right), max(0, h - top - bottom), st, at), (left, top))
            return rv

        def visit(self):
            return [self.fill, self.line]


    class SgFxSprites(renpy.Displayable):
        """
        작은 그림 여러 장을 시간에 맞춰 옮겨 그린다. 꽃잎, 반짝이, 하트, 비가 쓴다.

        kind   움직이는 법 ("petal", "spark", "heart", "drop")
        items  낱개마다의 숫자 묶음
        life   이 시간이 지나면 아무것도 그리지 않는다
        """

        def __init__(self, kind, items, life, **properties):
            super(SgFxSprites, self).__init__(**properties)
            self.kind = kind
            self.items = items
            self.life = life

        def at_petal(self, it, t):
            ## 좌우로 살랑이며 비스듬히 한 번 떨어진다. 떨어지는 동안 돌며 뒤집힌다
            import math
            tt = t - it["delay"]
            if not (0 <= tt < it["dur"]):
                return None
            p = tt / it["dur"]
            x = it["x"] + it["dx"] * p + it["sway"] * math.sin((p * it["waves"] + it["phase"]) * 2 * math.pi)
            f = int((tt / it["spin"] + it["phase"]) * 16) % 16
            return it["frames"][f], x, it["y"] + it["dy"] * p

        def at_spark(self, it, t):
            ## 제자리에서 커졌다 작아지기를 두 번 한다
            tt = t - it["delay"]
            if not (0 <= tt < 1.0):
                return None
            f = int((tt % 0.5) / 0.5 * 10) % 10
            return it["frames"][f], it["x"], it["y"]

        def at_heart(self, it, t):
            ## 처음엔 빠르게, 갈수록 천천히 떠오르다가 옅어지며 사라진다
            import math
            tt = t - it["delay"]
            if not (0 <= tt < it["dur"]):
                return None
            p = tt / it["dur"]
            up = 1.0 - (1.0 - p) ** 2
            x = it["x"] + it["drift"] * p + it["sway"] * math.sin((tt / it["swing"] + it["phase"]) * 2 * math.pi)
            level = 0 if p < 0.7 else min(3, 1 + int((p - 0.7) / 0.3 * 3))
            return it["frames"][level], x, it["y"] - it["rise"] * up

        def at_drop(self, it, t):
            ## 같은 길을 되풀이해 떨어진다
            p = ((t - it["delay"]) % it["dur"]) / it["dur"]
            return it["frames"][0], it["x"] + it["dx"] * p, it["y"] + it["dy"] * p

        def render(self, width, height, st, at):
            rv = renpy.Render(width, height)
            if st >= self.life:
                return rv

            place = getattr(self, "at_" + self.kind)
            for it in self.items:
                got = place(it, st)
                if got is None:
                    continue
                d, x, y = got
                cr = renpy.render(d, width, height, 0, 0)
                w, h = cr.get_size()
                if x + w <= 0 or y + h <= 0 or x >= width or y >= height:
                    continue
                rv.blit(cr, (int(round(x)), int(round(y))))

            renpy.redraw(self, 0)
            return rv

        def visit(self):
            seen = []
            for it in self.items:
                for d in it["frames"]:
                    if d not in seen:
                        seen.append(d)
            return seen


    class SgFxBars(renpy.Displayable):
        """화면 깨짐이 쓰는 색 막대. step 초마다 다른 장을 그린다."""

        def __init__(self, colors, frames, step, life, **properties):
            super(SgFxBars, self).__init__(**properties)
            self.solids = [Solid(c) for c in colors]
            self.frames = frames
            self.step = step
            self.life = life

        def render(self, width, height, st, at):
            rv = renpy.Render(width, height)
            if st >= self.life:
                return rv
            i = int(st / self.step)
            if i < len(self.frames):
                for color, x, y, w, h in self.frames[i]:
                    rv.blit(renpy.render(self.solids[color], w, h, st, at), (x, y))
            renpy.redraw(self, self.step - (st % self.step))
            return rv

        def visit(self):
            return list(self.solids)


    class SgFxFitText(renpy.Displayable):
        """
        글을 정해진 줄 수 안에 들어오는 가장 큰 글자로 그린다. 그래도 넘치면 아래를 자른다.

        글은 모델이 쓴 것이다. "[" 는 변수로 읽지 않게 하고(substitute=False),
        "{" 는 글자 꾸밈 표시로 읽지 않게 겹쳐 쓴다.

        sizes  큰 것부터 시도할 글자 크기
        lines  크기마다 허용하는 줄 수
        """

        def __init__(self, what, sizes, lines, maxw, **text_properties):
            super(SgFxFitText, self).__init__()
            what = what.replace("{", "{{")
            self.maxw = maxw
            self.texts = [Text(what, size=s, substitute=False, **text_properties) for s in sizes]
            ## 그 크기로 허용한 줄 수만큼 썼을 때의 높이를 재는 데 쓴다
            self.probes = [
                Text("\n".join(["가"] * n), size=s, substitute=False, **text_properties)
                for s, n in zip(sizes, lines)
            ]

        def render(self, width, height, st, at):
            cr = None
            limit = 0
            for text, probe in zip(self.texts, self.probes):
                cr = renpy.render(text, self.maxw, height, st, at)
                limit = renpy.render(probe, self.maxw, height, st, at).get_size()[1]
                if cr.get_size()[1] <= limit:
                    break

            w, h = cr.get_size()
            if h > limit:
                h = limit
                cr = cr.subsurface((0, 0, w, h))
            rv = renpy.Render(w, h)
            rv.blit(cr, (0, 0))
            return rv

        def visit(self):
            return self.texts + self.probes


    class SgFxErrBack(renpy.Displayable):
        """
        가짜 오류창의 바탕. 같은 크기의 창 석 장을 22픽셀씩 비껴 겹쳐 그린다.
        맨 앞 장의 속(아이콘, 글, 단추)은 이 바탕을 쓰는 frame 이 채운다.
        뒤의 두 장은 제목 줄만 있는 빈 창이다. 0초, 0.08초, 0.16초에 한 장씩 뜬다.
        """

        STEP = 22
        BORDER = 4
        SHADOW = 8
        BAR = 44

        def __init__(self, life, **properties):
            super(SgFxErrBack, self).__init__(**properties)
            self.life = life
            self.ink = Solid(sg_fx_ink)
            self.paper = Solid(sg_fx_paper)
            self.title = Text("오류", font="fonts/Pretendard-Bold.otf", size=22, color=sg_fx_paper)
            self.close = renpy.displayable("images/fx/sg_fx_close.png")

        def render(self, width, height, st, at):
            width = int(width)
            height = int(height)
            rv = renpy.Render(width, height)
            if st >= self.life:
                return rv

            border = self.BORDER
            w = width - 2 * self.STEP - self.SHADOW
            h = height - 2 * self.STEP - self.SHADOW

            edge = renpy.render(self.ink, w, h, st, at)
            inside = renpy.render(self.paper, w - 2 * border, h - 2 * border, st, at)
            bar = renpy.render(self.ink, w - 2 * border, self.BAR, st, at)
            title = renpy.render(self.title, w, self.BAR, st, at)
            close = renpy.render(self.close, 22, 22, st, at)

            for i, start in enumerate((0.0, 0.08, 0.16)):
                if st < start:
                    renpy.redraw(self, start - st)
                    break
                o = i * self.STEP
                rv.blit(edge, (o + self.SHADOW, o + self.SHADOW))
                rv.blit(edge, (o, o))
                rv.blit(inside, (o + border, o + border))
                rv.blit(bar, (o + border, o + border))
                rv.blit(title, (o + border + 11, o + border + (self.BAR - title.get_size()[1]) // 2))
                rv.blit(close, (o + w - border - 11 - 22, o + border + 11))
            return rv

        def visit(self):
            return [self.ink, self.paper, self.title, self.close]


################################################################################
## 화면 깨짐이 쓰는 셰이더
################################################################################

init python:

    ## 무대(master 레이어)를 가로 조각으로 어긋나게 하고 빨강과 청록으로 색을 가른다.
    ## u_sg_fx_level  2: 크게 어긋남, 1: 살짝, 0: 멀쩡
    ## u_sg_fx_seed   값이 바뀌면 어긋나는 조각과 거리가 바뀐다
    renpy.register_shader("sg_fx.glitch", variables="""
        uniform sampler2D tex0;
        uniform vec2 u_model_size;
        uniform float u_sg_fx_seed;
        uniform float u_sg_fx_level;
        varying vec2 v_tex_coord;
    """, fragment_functions="""
        float sg_fx_hash(vec2 p) {
            return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
        }
    """, fragment_300="""
        vec2 sg_fx_uv = v_tex_coord;
        float sg_fx_y = sg_fx_uv.y * u_model_size.y;
        float sg_fx_slab = floor(sg_fx_y / 66.0);
        float sg_fx_row = floor(sg_fx_y / 22.0);
        float sg_fx_on = step(0.5, u_sg_fx_level);
        float sg_fx_big = step(1.5, u_sg_fx_level);
        float sg_fx_reach = mix(16.0, 90.0, sg_fx_big);
        float sg_fx_odds = mix(0.12, 0.30, sg_fx_big);
        float sg_fx_pick1 = step(sg_fx_hash(vec2(sg_fx_slab, u_sg_fx_seed)), sg_fx_odds);
        float sg_fx_pick2 = step(sg_fx_hash(vec2(sg_fx_row + 31.0, u_sg_fx_seed + 7.0)), sg_fx_odds * 0.5);
        float sg_fx_move1 = (sg_fx_hash(vec2(sg_fx_slab, u_sg_fx_seed + 13.0)) * 2.0 - 1.0) * sg_fx_reach;
        float sg_fx_move2 = (sg_fx_hash(vec2(sg_fx_row, u_sg_fx_seed + 29.0)) * 2.0 - 1.0) * sg_fx_reach;
        float sg_fx_shift = sg_fx_on * mix(sg_fx_pick2 * sg_fx_move2, sg_fx_move1, sg_fx_pick1);
        float sg_fx_split = sg_fx_on * mix(4.0, 8.0, sg_fx_big);
        sg_fx_uv.x = fract(sg_fx_uv.x + sg_fx_shift / u_model_size.x);
        vec2 sg_fx_d = vec2(sg_fx_split / u_model_size.x, 0.0);
        vec4 sg_fx_a = texture2D(tex0, sg_fx_uv + sg_fx_d);
        vec4 sg_fx_b = texture2D(tex0, sg_fx_uv - sg_fx_d);
        gl_FragColor = vec4(sg_fx_a.r, sg_fx_b.g, sg_fx_b.b, max(sg_fx_a.a, sg_fx_b.a));
    """)


################################################################################
## 움직임 (ATL)
################################################################################

## t0 초부터 t1 초까지만 보인다.
transform sg_fx_t_between(t0, t1):
    alpha 0.0
    pause t0
    alpha 1.0
    pause (t1 - t0)
    alpha 0.0

## a 초 동안 부드럽게 나타나 hold 초 머물고 b 초 동안 부드럽게 사라진다.
transform sg_fx_t_fade(a, hold, b):
    alpha 0.0
    ease a alpha 1.0
    pause hold
    ease b alpha 0.0

## 자막 띠: 세 단계로 펴졌다가 세 단계로 접힌다. 2.8초
transform sg_fx_t_caption_band(y):
    ypos y
    yanchor 0.5
    yzoom 0.2
    pause 0.084
    yzoom 0.6
    pause 0.084
    yzoom 1.0
    pause 2.464
    yzoom 0.6
    pause 0.084
    yzoom 0.2
    pause 0.084
    alpha 0.0

## 집중선 한 장: 세 장이 0.09초씩 번갈아 보이게 lead 만큼 늦게 시작한다.
transform sg_fx_t_flick(x, y, z, lead):
    anchor (0.5, 0.5)
    pos (x, y)
    zoom z
    alpha 0.0
    pause lead
    block:
        alpha 1.0
        pause 0.09
        alpha 0.0
        pause 0.18
        repeat

## 암전 속의 눈: 0.6초에 뜨고 한 번 깜빡인 뒤 1.8초에 사라진다.
transform sg_fx_t_eyes(x, y):
    pos (x, y)
    anchor (0.5, 0.5)
    alpha 0.0
    pause 0.6
    linear 0.1 alpha 1.0
    pause 0.38
    ease 0.07 yzoom 0.1
    ease 0.07 yzoom 1.0
    pause 0.4
    linear 0.18 alpha 0.0

## 붉은 화면: 막이 덮이고 맥박처럼 두 번 뛴다. 2.2초
## 번쩍이지 않게 브라우저판보다 옅게, 부드럽게 오르내린다.
transform sg_fx_t_red_film:
    alpha 0.0
    linear 0.12 alpha 0.36
    pause 0.32
    easein 0.1 alpha 0.5
    pause 0.08
    easeout 0.2 alpha 0.36
    pause 0.236
    easein 0.1 alpha 0.5
    pause 0.08
    easeout 0.2 alpha 0.36
    pause 0.384
    linear 0.38 alpha 0.0

transform sg_fx_t_red_frame:
    alpha 0.0
    linear 0.12 alpha 1.0
    pause 1.7
    linear 0.38 alpha 0.0

transform sg_fx_t_red_beat:
    alpha 0.0
    pause 0.44
    easein 0.1 alpha 0.6
    pause 0.08
    easeout 0.2 alpha 0.0
    pause 0.236
    easein 0.1 alpha 0.6
    pause 0.08
    easeout 0.2 alpha 0.0

## 번개: 한 번만 옅게 번쩍이고, 번개 줄기는 깜빡이지 않고 한 번 떴다가 사라진다. 1.5초
## 브라우저판은 두 번 세게 번쩍이지만 여기서는 번쩍임을 줄였다.
transform sg_fx_t_bolt_flash:
    alpha 0.5
    linear 0.25 alpha 0.0

transform sg_fx_t_bolt_dark:
    alpha 0.0
    linear 0.12 alpha 0.5
    linear 1.0 alpha 0.3
    linear 0.38 alpha 0.0

transform sg_fx_t_bolt_line(x, z):
    xanchor 0.5
    pos (x, 0)
    zoom z
    alpha 1.0
    pause 0.9
    linear 0.3 alpha 0.0

## 스포트라이트: 불빛이 자리를 찾느라 두 번 헛짚고 얼굴에 멎는다. 3초
transform sg_fx_t_spot(x, y, z):
    anchor (0.5, 0.5)
    zoom z
    pos (x - 90, y + 30)
    alpha 0.0
    easein 0.18 alpha 0.7
    ease 0.22 pos (x + 48, y - 18) alpha 1.0
    ease 0.22 pos (x, y)
    pause 2.0
    easeout 0.38 alpha 0.0


## ---------- master 레이어에 거는 것 ----------

## 흔들림: 좌우로 덜컹거리다 잦아든다. 0.8초
## 흔드는 동안 무대를 1.05배로 키워 가장자리가 드러나지 않게 한다. (ox, oy) 는 키운 무대를
## 한가운데에 두는 자리다.
transform sg_fx_t_shake(ox, oy):
    zoom 1.05
    yoffset oy
    xoffset (ox - 24)
    pause 0.08
    xoffset (ox + 20)
    pause 0.08
    xoffset (ox - 16)
    pause 0.08
    xoffset (ox + 12)
    pause 0.08
    xoffset (ox - 8)
    pause 0.08
    xoffset (ox + 6)
    pause 0.08
    xoffset (ox - 3)
    pause 0.08
    xoffset ox
    linear 0.24 zoom 1.0 xoffset 0 yoffset 0

## 줌인: (fx, fy) 를 붙잡고 두 단계로 확 커졌다가 돌아온다. 1.3초
transform sg_fx_t_zoom(fx, fy, k1, k2):
    zoom k1
    xoffset int(-(k1 - 1.0) * fx)
    yoffset int(-(k1 - 1.0) * fy)
    pause 0.2
    zoom k2
    xoffset int(-(k2 - 1.0) * fx)
    yoffset int(-(k2 - 1.0) * fy)
    pause 1.1
    zoom 1.0
    xoffset 0
    yoffset 0

## 흑백: 색이 부드럽게 빠졌다가 돌아온다. 2.6초
transform sg_fx_t_mono:
    matrixcolor SaturationMatrix(1.0)
    linear 0.3 matrixcolor SaturationMatrix(0.0)
    pause 2.0
    linear 0.3 matrixcolor SaturationMatrix(1.0)

## 화면 깨짐: 0.1초마다 크게(2), 살짝(1), 멀쩡(0)을 오간다. 1.5초
transform sg_fx_t_glitch(seed):
    mesh True
    shader "sg_fx.glitch"
    u_sg_fx_seed (seed + 0.0)
    u_sg_fx_level 2.0
    pause 0.1
    u_sg_fx_seed (seed + 1.0)
    u_sg_fx_level 2.0
    pause 0.1
    u_sg_fx_seed (seed + 2.0)
    u_sg_fx_level 1.0
    pause 0.1
    u_sg_fx_level 0.0
    pause 0.1
    u_sg_fx_seed (seed + 4.0)
    u_sg_fx_level 2.0
    pause 0.1
    u_sg_fx_seed (seed + 5.0)
    u_sg_fx_level 2.0
    pause 0.1
    u_sg_fx_level 0.0
    pause 0.1
    u_sg_fx_seed (seed + 7.0)
    u_sg_fx_level 1.0
    pause 0.1
    u_sg_fx_seed (seed + 8.0)
    u_sg_fx_level 2.0
    pause 0.1
    u_sg_fx_level 0.0
    pause 0.2
    u_sg_fx_seed (seed + 11.0)
    u_sg_fx_level 2.0
    pause 0.1
    u_sg_fx_seed (seed + 12.0)
    u_sg_fx_level 2.0
    pause 0.1
    u_sg_fx_seed (seed + 13.0)
    u_sg_fx_level 1.0
    pause 0.1
    u_sg_fx_level 0.0


################################################################################
## 스타일
################################################################################

style sg_fx_frame is empty

style sg_fx_label_text is empty:
    font "fonts/Pretendard-Bold.otf"
    size 22
    color sg_fx_ink

style sg_fx_zoom_label is empty:
    background SgFxBox(sg_fx_marker, sg_fx_ink, (2, 2, 2, 2), (4, 4))
    padding (13, 3, 17, 7)

style sg_fx_caption_band is empty:
    background SgFxBox(sg_fx_marker, sg_fx_ink, (0, 4, 0, 4), (0, 8))
    xfill True
    padding (0, 26, 0, 34)

style sg_fx_err_frame is empty:
    xsize 536
    padding (48, 92, 12, 12)

style sg_fx_err_ok is empty:
    background SgFxBox(sg_fx_paper, sg_fx_ink, (2, 2, 2, 2), (4, 4))
    hover_background SgFxBox(sg_fx_marker, sg_fx_ink, (2, 2, 2, 2), (4, 4))
    xminimum 136
    ysize 48
    padding (24, 2, 28, 6)
    keyboard_focus False


################################################################################
## 화면. 연출 하나에 화면 하나이고 전부 sg_fx 레이어에 뜬다.
## 화면마다 제 수명이 지나면 스스로 내려간다. zorder 는 겹칠 때의 순서다:
## 막 < 입자 < 글자 < 오류창
################################################################################

## 꽃잎: 벚꽃잎이 팔랑거리며 위에서 비스듬히 떨어진다. 2.9초
screen sg_fx_petals(d):
    layer "sg_fx"
    zorder 40
    add d
    timer 2.9 action Function(sg_fx_end, "꽃잎")

## 반짝이: 네 갈래 반짝임이 여기저기서 커졌다 작아진다. 2.4초
screen sg_fx_sparks(d):
    layer "sg_fx"
    zorder 42
    add d
    timer 2.4 action Function(sg_fx_end, "반짝이")

## 집중선: 가장자리에서 얼굴 쪽으로 모이는 남색 선. 세 장을 번갈아 보여 준다. 1.4초
screen sg_fx_lines(x, y, z):
    layer "sg_fx"
    zorder 30
    add "images/fx/sg_fx_lines_1.png" at sg_fx_t_flick(x, y, z, 0.0)
    add "images/fx/sg_fx_lines_2.png" at sg_fx_t_flick(x, y, z, 0.09)
    add "images/fx/sg_fx_lines_3.png" at sg_fx_t_flick(x, y, z, 0.18)
    timer 1.4 action Function(sg_fx_end, "집중선")

## 줌인: 무대가 얼굴 쪽으로 두 단계 커지는 동안 모서리 표시와 배율 딱지를 띄운다. 1.3초
screen sg_fx_zoom(boxes):
    layer "sg_fx"
    zorder 50

    for i, b in enumerate(boxes):
        fixed:
            at sg_fx_t_between(i * 0.2, 0.2 + i * 1.1)
            pos (b[0], b[1])
            xysize (b[2], b[3])

            add Solid(sg_fx_ink, xysize=(44, 8))
            add Solid(sg_fx_ink, xysize=(8, 44))
            add Solid(sg_fx_ink, xysize=(44, 8)) xalign 1.0
            add Solid(sg_fx_ink, xysize=(8, 44)) xalign 1.0
            add Solid(sg_fx_ink, xysize=(44, 8)) yalign 1.0
            add Solid(sg_fx_ink, xysize=(8, 44)) yalign 1.0
            add Solid(sg_fx_ink, xysize=(44, 8)) xalign 1.0 yalign 1.0
            add Solid(sg_fx_ink, xysize=(8, 44)) xalign 1.0 yalign 1.0

            frame:
                style "sg_fx_zoom_label"
                xalign 1.0
                ypos (b[3] + 4)
                text b[4] style "sg_fx_label_text"

    timer 1.3 action Function(sg_fx_end, "줌인")

## 자막: 지문을 형광펜 띠 위에 크게 띄운다. 2.8초
screen sg_fx_caption(d, y):
    layer "sg_fx"
    zorder 60

    frame:
        style "sg_fx_caption_band"
        at sg_fx_t_caption_band(y)
        add d xalign 0.5 at sg_fx_t_between(0.17, 2.63)

    timer 2.8 action Function(sg_fx_end, "자막")

## 하트: 통통한 하트가 아래에서 떠오른다. 2.8초
screen sg_fx_hearts(d):
    layer "sg_fx"
    zorder 44
    add d
    timer 2.8 action Function(sg_fx_end, "하트")

## 흔들림: 무대만 흔든다. 덮는 그림은 없고 수명만 잰다. 0.8초
screen sg_fx_shake():
    layer "sg_fx"
    zorder 26
    timer 0.8 action Function(sg_fx_end, "흔들림")

## 암전: 부드럽게 어두워졌다가 돌아온다. 어둠 속에서 눈만 깜빡인다. 2.2초
screen sg_fx_blackout(x, y):
    layer "sg_fx"
    zorder 10
    add Solid(sg_fx_dark) at sg_fx_t_fade(0.4, 1.4, 0.4)
    add "images/fx/sg_fx_eyes.png" at sg_fx_t_eyes(x, y)
    timer 2.2 action Function(sg_fx_end, "암전")

## 붉은 화면: 붉은 막이 덮이고 맥박처럼 두 번 뛴다. 2.2초
screen sg_fx_red():
    layer "sg_fx"
    zorder 12
    add Solid(sg_fx_red) at sg_fx_t_red_film
    ## 가장자리의 붉은 물듦. 맥박이 뛸 때 한 겹 더 짙어진다
    add Transform("images/fx/sg_fx_vignette_red.png", zoom=4.0) at sg_fx_t_red_frame
    add Transform("images/fx/sg_fx_vignette_red.png", zoom=4.0) at sg_fx_t_red_beat
    timer 2.2 action Function(sg_fx_end, "붉은 화면")

## 흑백: 무대의 색이 빠지는 동안 가장자리가 옅게 어두워진다. 2.6초
screen sg_fx_mono():
    layer "sg_fx"
    zorder 14
    add Transform("images/fx/sg_fx_vignette.png", zoom=4.0) at sg_fx_t_fade(0.3, 2.0, 0.3)
    timer 2.6 action Function(sg_fx_end, "흑백")

## 비: 비스듬한 빗줄기가 쏟아지고 화면이 조금 어두워진다. 3.4초
screen sg_fx_rain(d):
    layer "sg_fx"
    zorder 20
    fixed:
        at sg_fx_t_fade(0.3, 2.7, 0.4)
        add Solid(sg_fx_rgba(sg_fx_ink, 0.2))
        add d
    timer 3.4 action Function(sg_fx_end, "비")

## 번개: 화면이 한 번 옅게 번쩍이고 번개 한 줄기가 내리친다. 1.5초
screen sg_fx_bolt(d, x, z):
    layer "sg_fx"
    zorder 22
    add Solid(sg_fx_dark) at sg_fx_t_bolt_dark
    add Solid("#FFFFFF") at sg_fx_t_bolt_flash
    add d at sg_fx_t_bolt_line(x, z)
    timer 1.5 action Function(sg_fx_end, "번개")

## 스포트라이트: 얼굴 둘레만 남기고 어두워진다. 3초
screen sg_fx_spot(x, y, z):
    layer "sg_fx"
    zorder 16
    add "images/fx/sg_fx_spot.png" at sg_fx_t_spot(x, y, z)
    timer 3.0 action Function(sg_fx_end, "스포트라이트")

## 화면 깨짐: 무대가 가로 조각으로 어긋나는 동안 색 막대가 튄다. 1.5초
screen sg_fx_glitch(d):
    layer "sg_fx"
    zorder 24
    add d
    timer 1.5 action Function(sg_fx_end, "화면 깨짐")

## 가짜 오류창: 옛 운영체제 모양의 오류창이 석 장 겹쳐 뜬다.
## "확인" 을 누르거나 3.9초가 지나면 닫힌다. 게임 화면 안에 그린 그림일 뿐이다.
screen sg_fx_err(d, back, y):
    layer "sg_fx"
    zorder 70

    frame:
        style "sg_fx_err_frame"
        background back
        ## 맨 앞 장이 무대 한가운데에 오게 한다. 뒤의 두 장은 왼쪽 위로 삐져나온다
        xpos 0.5
        xanchor 286
        ypos y
        yanchor 0.5
        yoffset -18

        vbox:
            at sg_fx_t_between(0.16, 3.9)

            frame:
                style "sg_fx_frame"
                padding (22, 22, 22, 22)
                hbox:
                    spacing 22
                    add "images/fx/sg_fx_err_icon.png"
                    add d

            frame:
                style "sg_fx_frame"
                xfill True
                padding (22, 0, 22, 22)
                button:
                    style "sg_fx_err_ok"
                    xalign 0.5
                    action Function(sg_fx_end, "가짜 오류창")
                    text "확인" style "sg_fx_label_text" xalign 0.5 yalign 0.5

    timer 3.9 action Function(sg_fx_end, "가짜 오류창")


################################################################################
## 연출을 걸고 걷는 함수
################################################################################

init python:

    def sg_fx_build_petals(env):
        import random

        W, H = env["W"], env["H"]
        items = []
        for i in range(56):
            sheet = "ab"[i % 2]
            size = random.choice([0, 1, 1, 2])
            zoom = (0.7, 0.95, 1.25)[size]
            px = 64 * zoom
            dur = random.uniform(1.5, 2.1)
            items.append({
                "frames": [
                    sg_fx_cut("petal-%s-%d-%d" % (sheet, size, k),
                              "images/fx/sg_fx_petal_%s.png" % sheet, (k * 64, 0, 64, 64), zoom)
                    for k in range(16)
                ],
                "x": random.uniform(-0.3 * W, 0.95 * W),
                "y": -px,
                "dx": random.uniform(0.15, 0.4) * H,
                "dy": H + 2 * px,
                "dur": dur,
                ## 처음부터 화면이 차 있고, 2.9초 전에 마지막 장이 빠진다
                "delay": random.uniform(-0.8 * dur, 2.85 - dur),
                "sway": random.uniform(6, 22),
                "waves": random.uniform(0.8, 1.8),
                "phase": random.random(),
                "spin": random.uniform(0.9, 1.5),
            })
        return {"d": SgFxSprites("petal", items, 2.9)}, None

    def sg_fx_build_sparks(env):
        import random

        W = env["W"]
        items = []
        for i in range(24):
            size = random.choice([0, 1, 1, 2])
            zoom = (0.8, 1.1, 1.5)[size]
            px = 72 * zoom
            items.append({
                "frames": [
                    sg_fx_cut("spark-%d-%d" % (size, k), "images/fx/sg_fx_spark.png", (k * 72, 0, 72, 72), zoom)
                    for k in range(10)
                ],
                "x": random.uniform(0, W - px),
                "y": random.uniform(0, max(1, env["ui_top"] - px)),
                "delay": random.uniform(0, 1.3),
            })
        return {"d": SgFxSprites("spark", items, 2.4)}, None

    def sg_fx_build_lines(env):
        ## 그림은 비워 두는 반지름 186픽셀을 기준으로 절반 크기로 그려져 있다
        z = 2.0 * max(env["pw"], env["ph"]) * 0.62 / 186.0
        return {"x": env["cx"], "y": env["cy"], "z": z}, None

    def sg_fx_build_zoom(env):
        ## 무대 전체를 키우면 어차피 가장자리가 잘린다. 브라우저판의 작은 쪽 배율을 쓴다
        steps = (1.25, 1.5)
        W, cx, cy = env["W"], env["cx"], env["cy"]

        boxes = []
        for k in steps:
            w = int(round(env["pw"] * k)) + 44
            h = int(round(env["ph"] * k)) + 44
            ## 모서리 표시가 화면 밖이나 대사창 뒤로 나가지 않게 당긴다
            x0 = max(8, int(cx - w / 2))
            y0 = max(8, int(cy - h / 2))
            x1 = min(W - 8, int(cx + w / 2))
            y1 = min(env["ui_top"] - 52, int(cy + h / 2))
            boxes.append((x0, y0, max(96, x1 - x0), max(96, y1 - y0), "%g배" % k))
        return {"boxes": boxes}, sg_fx_t_zoom(cx, cy, steps[0], steps[1])

    def sg_fx_build_caption(env):
        ## 지문이 없으면 아무 일도 없다
        if not env["text"]:
            return None
        d = SgFxFitText(
            env["text"], [56, 42, 28], [2, 2, 3], int(env["W"] * 0.86),
            font="fonts/Pretendard-Bold.otf", color=sg_fx_ink, textalign=0.5,
            layout="subtitle", language="korean-with-spaces", line_leading=6, line_spacing=6)
        ## 가짜 오류창과 함께 오면 창에 가리지 않게 위로 비킨다
        y = 104 if "가짜 오류창" in env["names"] else env["ui_top"] // 2
        return {"d": d, "y": y}, None

    def sg_fx_build_hearts(env):
        import random

        W, H = env["W"], env["H"]
        items = []
        for i in range(18):
            size = random.choice([0, 1, 1, 2, 3])
            zoom = (0.5, 0.7, 0.9, 1.1)[size]
            px = 80 * zoom
            tilt = random.randrange(3)
            items.append({
                ## 기울기 하나를 골라 불투명도 네 단계를 쓴다
                "frames": [
                    sg_fx_cut("heart-%d-%d-%d" % (size, tilt, col),
                              "images/fx/sg_fx_heart.png", (col * 80, tilt * 80, 80, 80), zoom)
                    for col in range(4)
                ],
                "x": random.uniform(0.03 * W, 0.97 * W - px),
                "y": H + 4,
                "rise": random.uniform(0.45, 0.95) * H + px,
                "drift": random.uniform(-30, 30),
                "sway": random.uniform(4, 12),
                "swing": random.uniform(0.7, 1.1),
                "phase": random.random(),
                "dur": random.uniform(1.5, 2.1),
                "delay": random.uniform(0, 0.7),
            })
        return {"d": SgFxSprites("heart", items, 2.8)}, None

    def sg_fx_build_shake(env):
        return {}, sg_fx_t_shake(-int(env["W"] * 0.025), -int(env["H"] * 0.025))

    def sg_fx_build_blackout(env):
        return {"x": env["cx"], "y": env["cy"]}, None

    def sg_fx_build_red(env):
        return {}, None

    def sg_fx_build_mono(env):
        return {}, sg_fx_t_mono

    def sg_fx_build_rain(env):
        import random

        W, H = env["W"], env["H"]
        near = renpy.displayable("images/fx/sg_fx_drop_near.png")
        far = renpy.displayable("images/fx/sg_fx_drop_far.png")

        items = []
        for i in range(84):
            is_near = (i % 2 == 0)
            h = 72 if is_near else 44
            dy = H + 2 * h
            items.append({
                "frames": [near if is_near else far],
                "x": random.uniform(0, W + 0.26 * dy),
                "y": -h,
                ## 그림 속 빗줄기의 기울기와 같은 쪽으로 떨어진다
                "dx": -0.26 * dy,
                "dy": dy,
                "dur": random.uniform(0.42, 0.58) if is_near else random.uniform(0.7, 0.95),
                "delay": -random.uniform(0, 1.0),
            })
        return {"d": SgFxSprites("drop", items, 3.4)}, None

    def sg_fx_build_bolt(env):
        import random

        ## 세 가지 줄기 가운데 하나를 골라 좌우를 뒤집거나 그대로 쓴다.
        ## 그림은 대사창 윗변이 535 일 때를 기준으로 그려져 있다
        d = Transform("images/fx/sg_fx_bolt_%d.png" % random.randint(1, 3), xzoom=random.choice([-1.0, 1.0]))
        return {"d": d, "x": int(env["W"] * random.uniform(0.3, 0.7)), "z": env["ui_top"] / 535.0}, None

    def sg_fx_build_spot(env):
        import math
        ## 그림은 반지름 208픽셀을 기준으로 1/8 크기로 그려져 있다
        radius = math.sqrt(env["pw"] ** 2 + env["ph"] ** 2) / 2 * 0.98
        return {"x": env["cx"], "y": env["cy"], "z": 8.0 * radius / 208.0}, None

    def sg_fx_build_glitch(env):
        import random

        W = env["W"]
        cell = 22
        colors = [sg_fx_red, sg_fx_marker, sg_fx_ink, "#2FD3E6", "#2FD3E6", sg_fx_paper]
        ## sg_fx_t_glitch 와 같은 차례다. 2: 크게 어긋남, 1: 살짝, 0: 멀쩡
        script = [2, 2, 1, 0, 2, 2, 0, 1, 2, 0, 0, 2, 2, 1, 0]

        frames = []
        for level in script:
            bars = []
            for b in range({2: 6, 1: 2, 0: 0}[level]):
                bw = random.randint(3, 24) * cell
                bars.append((
                    random.randrange(len(colors)),
                    random.randint(-4, W // cell) * cell - bw // 2,
                    random.randint(0, max(0, env["ui_top"] // 4 - 6)) * 4,
                    bw,
                    random.choice([4, 8, 8, 12, 22]),
                ))
            frames.append(bars)
        return {"d": SgFxBars(colors, frames, 0.1, 1.5)}, sg_fx_t_glitch(float(random.randint(1, 40)))

    def sg_fx_build_err(env):
        d = SgFxFitText(
            env["text"] or sg_fx_default_error, [22], [6], 366,
            font="fonts/Pretendard-Medium.otf", color=sg_fx_ink,
            language="korean-with-spaces", line_spacing=7)
        ## 자막과 함께 오면 자막 띠 아래로 비킨다
        y = env["ui_top"] // 2 + (72 if "자막" in env["names"] else 0)
        return {"d": d, "back": SgFxErrBack(3.9), "y": y}, None

    ## 연출 이름 -> (화면 이름의 뒷부분, 준비하는 함수).
    ## 준비하는 함수는 (화면에 넘길 값, master 에 걸 transform 또는 None) 을 돌려준다.
    ## 걸 것이 없으면 None 을 돌려준다.
    sg_fx_table = {
        "꽃잎": ("petals", sg_fx_build_petals),
        "반짝이": ("sparks", sg_fx_build_sparks),
        "집중선": ("lines", sg_fx_build_lines),
        "줌인": ("zoom", sg_fx_build_zoom),
        "자막": ("caption", sg_fx_build_caption),
        "하트": ("hearts", sg_fx_build_hearts),
        "흔들림": ("shake", sg_fx_build_shake),
        "암전": ("blackout", sg_fx_build_blackout),
        "붉은 화면": ("red", sg_fx_build_red),
        "흑백": ("mono", sg_fx_build_mono),
        "비": ("rain", sg_fx_build_rain),
        "번개": ("bolt", sg_fx_build_bolt),
        "스포트라이트": ("spot", sg_fx_build_spot),
        "화면 깨짐": ("glitch", sg_fx_build_glitch),
        "가짜 오류창": ("err", sg_fx_build_err),
    }

    ## master 에 transform 을 거는 연출. 안쪽에 걸리는 것부터 적는다.
    sg_fx_master_order = ["흑백", "화면 깨짐", "줌인", "흔들림"]

    def sg_fx_oops(where):
        """연출은 조용히 실패한다. 무슨 일이 있었는지만 log.txt 에 남긴다."""
        try:
            import traceback
            renpy.display.log.write("sg_fx: %s 에서 문제가 생겨 건너뛴다.", where)
            renpy.display.log.write("%s", traceback.format_exc())
        except Exception:
            pass

    def sg_fx_env(names, narration):
        """연출들이 함께 쓰는 치수와 지문, 이번에 함께 거는 이름들."""
        text = narration.strip() if isinstance(narration, str) else ""
        cx, cy = sg_fx_focus
        pw, ph = sg_fx_focus_size
        return {
            "names": names,
            "W": config.screen_width,
            "H": config.screen_height,
            "cx": int(cx),
            "cy": int(cy),
            "pw": int(pw),
            "ph": int(ph),
            "ui_top": int(sg_fx_ui_top),
            "text": text,
        }

    def sg_fx_showing(name):
        """그 연출의 화면이 떠 있는가."""
        return renpy.get_screen("sg_fx_" + sg_fx_table[name][0], layer="sg_fx") is not None

    def sg_fx_end(name):
        """연출 하나가 수명을 다했을 때 그 화면이 부른다. 그 연출만 걷는다."""
        try:
            if name not in sg_fx_table:
                return
            renpy.hide_screen("sg_fx_" + sg_fx_table[name][0], layer="sg_fx")
            ## master 에 걸었던 것은 그런 연출이 전부 끝났을 때 한꺼번에 뗀다.
            ## 하나만 먼저 떼면 남은 것이 처음부터 다시 재생되기 때문이다.
            if (name in sg_fx_master_order) and not any(sg_fx_showing(n) for n in sg_fx_master_order):
                renpy.show_layer_at([], layer="master")
            renpy.restart_interaction()
        except Exception:
            sg_fx_oops("sg_fx_end")

    def sg_fx_clear():
        """걸려 있는 연출을 전부 즉시 걷는다."""
        try:
            changed = False
            master = False
            for name in sg_fx_table:
                if sg_fx_showing(name):
                    renpy.hide_screen("sg_fx_" + sg_fx_table[name][0], layer="sg_fx")
                    changed = True
                    if name in sg_fx_master_order:
                        master = True
            if master:
                renpy.show_layer_at([], layer="master")
            if changed:
                renpy.restart_interaction()
        except Exception:
            sg_fx_oops("sg_fx_clear")

    def sg_fx_play(names, narration=""):
        """
        연출을 건다.

        names      서버가 준 연출 이름 목록(0-2개, 한글 이름 그대로). 모르는 이름은 무시한다
        narration  그 턴의 지문. "자막" 과 "가짜 오류창" 이 쓴다

        앞서 걸린 연출은 먼저 걷는다. 같은 연출을 다시 걸면 처음부터 다시 재생한다.
        대화를 막지 않고, 끝나면 스스로 사라진다. 어떤 경우에도 오류를 내지 않는다.
        """
        try:
            sg_fx_clear()

            ## 목록의 종류는 따지지 않는다. 서버 응답(JSON)에서 온 목록은 Ren'Py 가 쓰는
            ## 목록과 종류가 달라서 isinstance(names, list) 로는 걸러지고 만다.
            if isinstance(names, str):
                names = [names]
            try:
                names = [name for name in names]
            except TypeError:
                names = []
            want = []
            for name in names:
                if isinstance(name, str) and (name in sg_fx_table) and (name not in want):
                    want.append(name)
            if not want:
                return

            env = sg_fx_env(want, narration)
            masters = {}
            for name in want:
                ident, build = sg_fx_table[name]
                try:
                    made = build(env)
                    if made is None:
                        continue
                    scope, master = made
                    renpy.show_screen("sg_fx_" + ident, _layer="sg_fx", **scope)
                    if master is not None:
                        masters[name] = master
                except Exception:
                    sg_fx_oops(name)

            if masters:
                renpy.show_layer_at([masters[n] for n in sg_fx_master_order if n in masters], layer="master")
            renpy.restart_interaction()
        except Exception:
            sg_fx_oops("sg_fx_play")

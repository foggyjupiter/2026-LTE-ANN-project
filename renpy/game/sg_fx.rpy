## sg_fx.rpy: 소개팅 화면 연출 15종.
##
## 서버는 턴마다 "fx"(연출 이름 0-2개)를 준다. 이 파일은 그 이름을 받아 화면에 건다.
## 연출마다 무엇을 얼마 동안 보여 주는지는 브라우저판(sogaeting/web/fx.js, fx.css)이
## 기준이고, 여기서는 그것을 Ren'Py 방식으로 옮겼다.
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
## 이 파일의 이름(화면, transform, 스타일, 함수, 변수)은 전부 sg_fx 로 시작한다.
## 효과음은 없다.

init -10 python:

    ## master, transient, sg_fx, screens, overlay 순서가 된다.
    renpy.add_layer("sg_fx", below="screens", menu_clear=True, sticky=False)


## 색 (브라우저판과 같다)
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

    ## 픽셀 그림. 글자 하나가 픽셀 하나이고 "." 은 빈칸이다. fx.js 의 그림 그대로다.
    sg_fx_art = {
        ## 꽃잎 한 장이 팔랑 도는 장면: 정면, 비스듬히, 옆. 곧게 선 것과 기운 것 두 벌
        "petal_a": [
            "....d....",
            "...dld...",
            "..dllpd..",
            ".dllppqd.",
            ".dlpppqd.",
            ".dlpppqd.",
            "..dppqd..",
            "...dqd...",
            "....d....",
        ],
        "petal_b": [
            "....d....",
            "...dld...",
            "..dlpqd..",
            "..dlpqd..",
            "..dlpqd..",
            "..dlpqd..",
            "..dlpqd..",
            "...dqd...",
            "....d....",
        ],
        "petal_c": [
            "....d....",
            "....d....",
            "...dpd...",
            "...dpd...",
            "...dpd...",
            "...dpd...",
            "...dpd...",
            "....d....",
            "....d....",
        ],
        "petal_da": [
            "......dd.",
            "....ddpqd",
            "...dlppqd",
            "..dllppqd",
            ".dllpppd.",
            ".dlpppqd.",
            "dlpppqd..",
            "dpqqdd...",
            ".ddd.....",
        ],
        "petal_db": [
            ".......dd",
            ".....ddpd",
            "....dlppd",
            "...dlppd.",
            "..dlppd..",
            ".dlppd...",
            "dlppd....",
            "dppd.....",
            ".dd......",
        ],
        "petal_dc": [
            ".........",
            ".......d.",
            "......dpd",
            ".....dpd.",
            "....dpd..",
            "...dpd...",
            "..dpd....",
            ".dpd.....",
            "..d......",
        ],
        "heart": [
            ".oo...oo.",
            "orro.orro",
            "orwrorrro",
            "orrrrrrso",
            ".orrrrso.",
            "..orrso..",
            "...oso...",
            "....o....",
        ],
        "spark_s": [
            "...........",
            "...........",
            "...........",
            "...........",
            ".....y.....",
            "....ywy....",
            ".....y.....",
            "...........",
            "...........",
            "...........",
            "...........",
        ],
        "spark_m": [
            "...........",
            "...........",
            ".....y.....",
            ".....y.....",
            "....yyy....",
            "..yyywyyy..",
            "....yyy....",
            ".....y.....",
            ".....y.....",
            "...........",
            "...........",
        ],
        "spark_l": [
            ".....y.....",
            ".....y.....",
            ".....y.....",
            "....yyy....",
            "...yywyy...",
            "yyyywwwyyyy",
            "...yywyy...",
            "....yyy....",
            ".....y.....",
            ".....y.....",
            ".....y.....",
        ],
        "drop": [
            "...b", "...b", "...b",
            "..b.", "..b.", "..b.",
            ".b..", ".b..", ".b..",
            "b...", "b...", "b...",
        ],
        "saw": [
            "k.....",
            "kk....",
            "kkk...",
            "kkkk..",
            "kkkkk.",
            "kkkkkk",
            "kkkkkk",
            "kkkkk.",
            "kkkk..",
            "kkk...",
            "kk....",
            "k.....",
        ],
        "err_icon": [
            "...ooooo...",
            "..orrrrro..",
            ".orrrrrrro.",
            "orrwrrrwrro",
            "orrrwrwrrro",
            "orrrrwrrrro",
            "orrrwrwrrro",
            "orrwrrrwrro",
            ".orrrrrrro.",
            "..orrrrro..",
            "...ooooo...",
        ],
        ## 닫기 단추: 바탕색 네모 안의 가위표
        "close": [
            "ppppppppppp",
            "ppppppppppp",
            "ppppppppppp",
            "pppkpppkppp",
            "ppppkpkpppp",
            "pppppkppppp",
            "ppppkpkpppp",
            "pppkpppkppp",
            "ppppppppppp",
            "ppppppppppp",
            "ppppppppppp",
        ],
    }

    def sg_fx_mirrored(rows):
        """그림을 좌우로 뒤집는다."""
        return [r[::-1] for r in rows]

    def sg_fx_transposed(rows):
        """그림의 가로와 세로를 바꾼다."""
        return ["".join(r[x] for r in rows) for x in range(len(rows[0]))]

    def sg_fx_turned(rows, quarters):
        """그림을 시계 방향으로 90도씩 quarters 번 돌린다."""
        for i in range(quarters % 4):
            h = len(rows)
            rows = ["".join(rows[h - 1 - y][x] for y in range(h)) for x in range(len(rows[0]))]
        return rows

    def sg_fx_outlined(rows, ch):
        """그림 둘레에 한 픽셀짜리 테두리를 두른다."""
        h = len(rows)
        w = len(rows[0])

        def filled(x, y):
            return 0 <= y < h and 0 <= x < w and rows[y][x] != "."

        out = []
        for y in range(-1, h + 1):
            line = ""
            for x in range(-1, w + 1):
                if filled(x, y):
                    line += rows[y][x]
                elif filled(x - 1, y) or filled(x + 1, y) or filled(x, y - 1) or filled(x, y + 1):
                    line += ch
                else:
                    line += "."
            out.append(line)
        return out

    def sg_fx_ring_rows(widths):
        """화면 가장자리를 두르는 띠 그림. widths 는 바깥부터 띠마다의 칸 수다."""
        total = sum(widths)
        n = total * 2 + 1
        rows = []
        for y in range(n):
            line = ""
            for x in range(n):
                d = min(x, y, n - 1 - x, n - 1 - y)
                ch = "."
                edge = 0
                for i, width in enumerate(widths):
                    edge += width
                    if d < edge:
                        ch = "123"[i]
                        break
                line += ch
            rows.append(line)
        return rows

    def sg_fx_png(rows, pal, scale=1, repeat=(1, 1)):
        """픽셀 그림을 PNG 바이트로 만든다. scale 배로 키우고 repeat 만큼 이어 붙인다."""
        import struct
        import zlib

        colors = {}
        for ch, c in pal.items():
            c = renpy.easy.color(c)
            colors[ch] = bytes(bytearray([c[0], c[1], c[2], c[3]]))
        blank = b"\x00\x00\x00\x00"

        lines = []
        for row in rows:
            line = b"".join(colors.get(ch, blank) * scale for ch in row) * repeat[0]
            lines.extend([b"\x00" + line] * scale)
        raw = b"".join(lines) * repeat[1]

        w = len(rows[0]) * scale * repeat[0]
        h = len(rows) * scale * repeat[1]

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9))
                + chunk(b"IEND", b""))

    ## 한 번 만든 그림을 다시 쓴다. 이름표(key)가 같으면 같은 그림이다.
    sg_fx_cache = {}

    def sg_fx_pix(key, rows, pal, scale=1, repeat=(1, 1)):
        """픽셀 그림을 Ren'Py 그림으로 만든다. rows 는 그림이거나 그림을 돌려주는 함수다."""
        d = sg_fx_cache.get(key)
        if d is None:
            if callable(rows):
                rows = rows()
            d = im.Data(sg_fx_png(rows, pal, scale, repeat), "sg_fx/" + key + ".png")
            sg_fx_cache[key] = d
        return d

    def sg_fx_rgba(c, alpha=1.0):
        """색과 불투명도로 (r, g, b, a) 를 만든다."""
        c = renpy.easy.color(c)
        return (c[0], c[1], c[2], int(round(255 * alpha)))

    def sg_fx_dither(level):
        """
        암전이 쓰는 모눈 막. level 은 네 칸 가운데 칠한 칸 수(1-3)다.
        다 칠한 단계는 이 막을 겹치지 않고 단색 한 장으로 덮는다. 창 크기가 화면과 다르면
        칸 사이로 무대가 실금처럼 비치기 때문이다.
        """
        key = "dither-%d" % level
        d = sg_fx_cache.get("tile-" + key)
        if d is None:
            rows = {1: [".k", ".."], 2: [".k", "k."], 3: [".k", "kk"]}[level]
            d = Tile(sg_fx_pix(key, rows, {"k": sg_fx_dark}, 22, (10, 10)))
            sg_fx_cache["tile-" + key] = d
        return d

    def sg_fx_tone():
        """흑백이 쓰는 망점 막."""
        d = sg_fx_cache.get("tile-tone")
        if d is None:
            rows = ["kk....", "kk....", "......", "......", "......", "......"]
            d = Tile(sg_fx_pix("tone", rows, {"k": sg_fx_rgba(sg_fx_ink, 0.22)}, 1, (40, 40)))
            sg_fx_cache["tile-tone"] = d
        return d

    def sg_fx_ring(widths, alphas):
        """붉은 화면이 쓰는 테두리. 가운데는 비어 있고 화면 크기에 맞게 늘어난다."""
        key = "ring-" + "-".join(str(i) for i in widths)
        d = sg_fx_cache.get("frame-" + key)
        if d is None:
            pal = dict(("123"[i], sg_fx_rgba(sg_fx_red, a)) for i, a in enumerate(alphas))
            edge = sum(widths) * 22
            d = Frame(sg_fx_pix(key, lambda: sg_fx_ring_rows(widths), pal, 22), edge, edge)
            sg_fx_cache["frame-" + key] = d
        return d

    def sg_fx_saw(side):
        """흔들림이 쓰는 톱니 띠. 화면 높이보다 길게 이어 붙인 한 장이다."""
        if side == "left":
            return sg_fx_pix("saw-left", sg_fx_art["saw"], {"k": sg_fx_ink}, 4, (1, 18))
        return sg_fx_pix("saw-right", lambda: sg_fx_mirrored(sg_fx_art["saw"]), {"k": sg_fx_ink}, 4, (1, 18))


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
        픽셀 그림 여러 장을 시간에 맞춰 옮겨 그린다. 꽃잎, 반짝이, 하트, 비가 쓴다.
        움직임은 브라우저판처럼 뚝뚝 끊어서 옮긴다.

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
            ## 한 장이 같은 길을 두 번 떨어진다. 떨어지는 동안 팔랑 돈다
            tt = t - it["delay"]
            if tt < 0:
                return None
            loop = int(tt // it["dur"])
            if loop >= 2:
                return None
            k = int((tt - loop * it["dur"]) / it["dur"] * it["n"])
            f = int((tt % it["spin"]) / it["spin"] * 12) % 12
            return it["frames"][f], it["x"] + it["sx"] * k, it["y"] + it["sy"] * k

        def at_spark(self, it, t):
            ## 제자리에서 작게, 크게, 작게 두 번 깜빡인다
            tt = t - it["delay"]
            if not (0 <= tt < 1.0):
                return None
            f = int((tt % 0.5) / 0.5 * 5) % 5
            return it["frames"][f], it["x"], it["y"]

        def at_heart(self, it, t):
            ## 좌우로 한 픽셀씩 흔들리며 떠오르다가 사라진다
            tt = t - it["delay"]
            if not (0 <= tt < it["dur"]):
                return None
            k = int(tt / it["dur"] * it["n"])
            sway = -it["unit"] if (tt % 0.4) < 0.2 else it["unit"]
            return it["frames"][0], it["x"] + it["sx"] * k + sway, it["y"] - it["sy"] * k

        def at_drop(self, it, t):
            ## 같은 길을 되풀이해 떨어진다
            tt = t - it["delay"]
            k = int((tt % it["dur"]) / it["dur"] * it["n"])
            return it["frames"][0], it["x"] + it["sx"] * k, it["y"] + it["sy"] * k

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


    class SgFxLines(renpy.Displayable):
        """
        집중선. 가장자리에서 얼굴 쪽으로 모이는 남색 쐐기를 낮은 해상도로 그린다.
        서로 다른 세 장을 0.09초씩 번갈아 보여 준다. 바깥에서 unit 배로 키워 쓴다.
        """

        STEP = 0.09

        def __init__(self, W, H, cx, cy, clear, unit, life, **properties):
            super(SgFxLines, self).__init__(**properties)
            import math
            self.cw = int(math.ceil(W / float(unit)))
            self.ch = int(math.ceil(H / float(unit)))
            self.life = life
            self.color = sg_fx_rgba(sg_fx_ink)
            self.frames = [
                self.make(cx / float(unit), cy / float(unit), clear / float(unit))
                for i in range(3)
            ]

        def make(self, cx, cy, clear):
            import math
            import random

            bins = 1440
            far = float(self.cw + self.ch)
            ## 위아래로 눌린 타원 둘레를 비워 둔다
            squash = 1.0 / math.sqrt(1.35)

            def point(r, angle):
                return (int(round(cx + r * math.cos(angle))), int(round(cy + r * math.sin(angle) * squash)))

            polys = []
            a = random.randint(0, 10)
            while a < bins:
                width = random.randint(3, 13)
                tip = clear * random.uniform(1.0, 1.8)
                taper = clear * random.uniform(0.5, 1.4)
                a0 = a / float(bins) * 2 * math.pi
                a1 = (a + width) / float(bins) * 2 * math.pi
                polys.append([
                    point(tip, (a0 + a1) / 2),
                    point(tip + taper, a0),
                    point(far, a0),
                    point(far, a1),
                    point(tip + taper, a1),
                ])
                a += width + random.randint(8, 26)
            return polys

        def render(self, width, height, st, at):
            rv = renpy.Render(self.cw, self.ch)
            if st >= self.life:
                return rv
            canvas = rv.canvas()
            for points in self.frames[int(st / self.STEP) % len(self.frames)]:
                canvas.polygon(self.color, points)
            renpy.redraw(self, self.STEP - (st % self.STEP))
            return rv


    class SgFxBolt(renpy.Displayable):
        """
        번개 한 줄기. 길게 내리긋고 옆으로 짧게 꺾이기를 되풀이하는 지그재그에 가지 하나가 붙는다.
        남색 테두리, 형광 노랑, 흰 심의 세 겹이고 아래로 갈수록 가늘다.
        낮은 해상도로 그리고 바깥에서 unit 배로 키워 쓴다.
        """

        def __init__(self, W, H, reach, unit, **properties):
            super(SgFxBolt, self).__init__(**properties)
            import math
            import random

            self.cw = int(math.ceil(W / float(unit)))
            self.ch = int(math.ceil(H / float(unit)))

            way = random.choice([-1, 1])
            x = self.cw * random.uniform(0.3, 0.7)
            y = -4.0
            y_end = reach / float(unit) * random.uniform(0.6, 0.74)
            pts = [(x, y)]
            while y < y_end:
                y += random.uniform(17, 25)
                x += way * random.uniform(7, 12)
                pts.append((x, y))
                y += random.uniform(0, 2)
                x -= way * random.uniform(10, 15)
                pts.append((x, y))
            y += random.uniform(16, 22)
            x += way * random.uniform(8, 12)
            pts.append((x, y))

            ## 꺾이는 자리에서 뻗는 가지 하나
            at = 2 * random.randint(1, max(1, (len(pts) - 3) // 2))
            bx, by = pts[at]
            mid = (bx - way * random.uniform(9, 13), by + random.uniform(10, 14))
            tip = (mid[0] - way * random.uniform(4, 7), mid[1] + random.uniform(11, 14) * 0.6)
            branch = [(bx, by), mid, tip]

            self.rects = []
            self.stroke(pts, 8, sg_fx_rgba(sg_fx_ink))
            self.stroke(branch, 5, sg_fx_rgba(sg_fx_ink))
            self.stroke(pts, 5, sg_fx_rgba(sg_fx_marker))
            self.stroke(branch, 2, sg_fx_rgba(sg_fx_marker))
            self.stroke(pts, 2, sg_fx_rgba("#FFFFFF"))

        def stroke(self, path, size, color):
            import math
            last = len(path) - 1
            for i in range(last):
                x0, y0 = path[i]
                x1, y1 = path[i + 1]
                steps = max(1, int(math.ceil(max(abs(x1 - x0), abs(y1 - y0)))))
                for s in range(steps + 1):
                    t = s / float(steps)
                    whole = (i + t) / float(last)
                    b = max(1, int(round(size * (1 - 0.5 * whole))))
                    px = int(round(x0 + (x1 - x0) * t - b / 2.0))
                    py = int(round(y0 + (y1 - y0) * t - b / 2.0))
                    self.rects.append((color, (px, py, b, b)))

        def render(self, width, height, st, at):
            rv = renpy.Render(self.cw, self.ch)
            canvas = rv.canvas()
            for color, rect in self.rects:
                canvas.rect(color, rect)
            return rv


    class SgFxSpot(renpy.Displayable):
        """
        스포트라이트의 어두운 막. 얼굴 둘레의 동그라미만 뚫려 있고, 위에서 내려오는
        빛기둥 자리는 조금 덜 어둡다. 낮은 해상도로 그리고 바깥에서 unit 배로 키워 쓴다.
        막을 조금 움직여도 가장자리가 드러나지 않게 사방으로 pad 칸씩 넉넉히 그린다.
        """

        def __init__(self, W, H, cx, cy, radius, unit, pad, **properties):
            super(SgFxSpot, self).__init__(**properties)
            import math

            self.cw = int(math.ceil(W / float(unit))) + pad * 2
            self.ch = int(math.ceil(H / float(unit))) + pad * 2

            cx = cx / float(unit) + pad
            cy = cy / float(unit) + pad
            radius = radius / float(unit)
            ring = 2

            ## 같은 값이 이어지는 가로 토막으로 적어 둔다: (불투명도, x, y, 길이)
            self.runs = []
            for y in range(self.ch):
                start = 0
                last = None
                for x in range(self.cw + 1):
                    alpha = None
                    if x < self.cw:
                        dx = x + 0.5 - cx
                        dy = y + 0.5 - cy
                        r = math.sqrt(dx * dx + dy * dy)
                        alpha = 205
                        if r <= radius:
                            alpha = 0
                        elif r <= radius + ring:
                            alpha = 110
                        elif dy < 0:
                            t = min(1.0, max(0.0, y / max(1.0, cy)))
                            if abs(dx) <= radius * (0.35 + 0.65 * t):
                                alpha = 140
                    if alpha != last:
                        if last:
                            self.runs.append((last, start, y, x - start))
                        start = x
                        last = alpha

        def render(self, width, height, st, at):
            rv = renpy.Render(self.cw, self.ch)
            surf = rv.canvas().get_surface()
            for alpha, x, y, w in self.runs:
                surf.fill((11, 16, 48, alpha), (x, y, w, 1))
            return rv


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
            self.close = sg_fx_pix("close", sg_fx_art["close"], {"p": sg_fx_paper, "k": sg_fx_ink}, 2)

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

## a0 초부터 a1 초까지, 그리고 b0 초부터 b1 초까지만 보인다.
transform sg_fx_t_twice(a0, a1, b0, b1):
    alpha 0.0
    pause a0
    alpha 1.0
    pause (a1 - a0)
    alpha 0.0
    pause (b0 - a1)
    alpha 1.0
    pause (b1 - b0)
    alpha 0.0

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

## 흔들림의 톱니: 0.08초마다 위아래로 튄다.
transform sg_fx_t_jolt(x, a, b):
    pos (x, -48)
    block:
        yoffset a
        pause 0.08
        yoffset b
        pause 0.08
        repeat

## 암전 속의 눈: 0.6초에 뜨고 한 번 깜빡인 뒤 1.8초에 사라진다.
transform sg_fx_t_eyes(x, y):
    pos (x, y)
    anchor (0.5, 0.5)
    alpha 0.0
    pause 0.6
    alpha 1.0
    pause 0.48
    yzoom 0.25
    pause 0.12
    yzoom 1.0
    pause 0.6
    alpha 0.0

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

## 흑백의 위아래 띠: 반쯤 나왔다가 다 나오고, 끝날 때 거꾸로 들어간다. 2.6초
transform sg_fx_t_bar(y_out, y_half, y_in):
    ypos y_half
    pause 0.13
    ypos y_in
    pause 2.34
    ypos y_half
    pause 0.13
    ypos y_out

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

transform sg_fx_t_bolt_line:
    alpha 1.0
    pause 0.9
    linear 0.3 alpha 0.0

## 스포트라이트: 불빛이 자리를 찾느라 두 번 헛짚는다. 3초
transform sg_fx_t_spot(x, y):
    pos (x - 72, y + 24)
    alpha 0.55
    pause 0.15
    pos (x + 40, y - 16)
    alpha 1.0
    pause 0.15
    pos (x, y)
    pause 2.52
    alpha 0.55
    pause 0.18
    alpha 0.0


## ---------- master 레이어에 거는 것 ----------

## 흔들림: 왼쪽으로 덜컹 튀었다가 제자리로 돌아오기를 다섯 번, 점점 약하게. 0.8초
transform sg_fx_t_shake:
    xoffset -24
    pause 0.08
    xoffset 0
    pause 0.08
    xoffset -20
    pause 0.08
    xoffset 0
    pause 0.08
    xoffset -16
    pause 0.08
    xoffset 0
    pause 0.08
    xoffset -10
    pause 0.08
    xoffset 0
    pause 0.08
    xoffset -6
    pause 0.08
    xoffset 0

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

## 흑백: 두 단계로 흑백이 되었다가 돌아온다. 2.6초
transform sg_fx_t_mono:
    matrixcolor SaturationMatrix(0.45)
    pause 0.13
    matrixcolor (ContrastMatrix(1.15) * SaturationMatrix(0.0))
    pause 2.34
    matrixcolor SaturationMatrix(0.45)
    pause 0.13
    matrixcolor SaturationMatrix(1.0)

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

## 꽃잎: 분홍 픽셀 꽃잎이 팔랑거리며 위에서 비스듬히 떨어진다. 2.9초
screen sg_fx_petals(d):
    layer "sg_fx"
    zorder 40
    add d
    timer 2.9 action Function(sg_fx_end, "꽃잎")

## 반짝이: 십자 모양 픽셀 반짝임이 여기저기 깜빡인다. 2.4초
screen sg_fx_sparks(d):
    layer "sg_fx"
    zorder 42
    add d
    timer 2.4 action Function(sg_fx_end, "반짝이")

## 집중선: 가장자리에서 얼굴 쪽으로 모이는 남색 선. 1.4초
screen sg_fx_lines(d):
    layer "sg_fx"
    zorder 30
    add d
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

## 하트: 빨간 픽셀 하트가 아래에서 떠오른다. 2.8초
screen sg_fx_hearts(d):
    layer "sg_fx"
    zorder 44
    add d
    timer 2.8 action Function(sg_fx_end, "하트")

## 흔들림: 무대가 덜컹거리는 동안 양옆에 남색 톱니가 튄다. 0.8초
screen sg_fx_shake():
    layer "sg_fx"
    zorder 26
    add sg_fx_saw("left") at sg_fx_t_jolt(0, 0, 24)
    add sg_fx_saw("right") at sg_fx_t_jolt(config.screen_width - 24, 24, 0)
    timer 0.8 action Function(sg_fx_end, "흔들림")

## 암전: 모눈 칸을 네 단계로 칠해 어두워졌다가 돌아온다. 어둠 속에서 눈만 깜빡인다. 2.2초
screen sg_fx_blackout(x, y):
    layer "sg_fx"
    zorder 10
    ## 0.12초마다 한 칸씩 더 칠해 어두워지고, 끝날 때 거꾸로 밝아진다
    add sg_fx_dither(1) at sg_fx_t_twice(0.0, 0.12, 2.08, 2.2)
    add sg_fx_dither(2) at sg_fx_t_twice(0.12, 0.24, 1.96, 2.08)
    add sg_fx_dither(3) at sg_fx_t_twice(0.24, 0.36, 1.84, 1.96)
    add Solid(sg_fx_dark) at sg_fx_t_between(0.36, 1.84)

    fixed:
        at sg_fx_t_eyes(x, y)
        xysize (110, 44)
        add Solid(sg_fx_paper, xysize=(22, 44))
        add Solid(sg_fx_paper, xysize=(22, 44)) xalign 1.0

    timer 2.2 action Function(sg_fx_end, "암전")

## 붉은 화면: 붉은 막이 덮이고 맥박처럼 두 번 뛴다. 2.2초
screen sg_fx_red():
    layer "sg_fx"
    zorder 12
    add Solid(sg_fx_red) at sg_fx_t_red_film
    add sg_fx_ring((1, 1, 1), (1.0, 0.55, 0.28)) at sg_fx_t_red_frame
    add sg_fx_ring((3, 2, 2), (1.0, 0.55, 0.28)) at sg_fx_t_red_beat
    timer 2.2 action Function(sg_fx_end, "붉은 화면")

## 흑백: 무대가 흑백이 되는 동안 망점과 위아래 띠가 덮인다. 2.6초
screen sg_fx_mono():
    layer "sg_fx"
    zorder 14
    add sg_fx_tone()
    add Solid(sg_fx_dark, xysize=(config.screen_width, 44)) at sg_fx_t_bar(-44, -22, 0)
    add Solid(sg_fx_dark, xysize=(config.screen_width, 44)) at sg_fx_t_bar(config.screen_height, config.screen_height - 22, config.screen_height - 44)
    timer 2.6 action Function(sg_fx_end, "흑백")

## 비: 비스듬한 픽셀 빗줄기가 쏟아지고 화면이 조금 어두워진다. 3.4초
screen sg_fx_rain(d):
    layer "sg_fx"
    zorder 20
    add Solid(sg_fx_rgba(sg_fx_ink, 0.2))
    add d
    timer 3.4 action Function(sg_fx_end, "비")

## 번개: 화면이 한 번 번쩍이고 픽셀 번개 한 줄기가 내리친다. 1.5초
screen sg_fx_bolt(d):
    layer "sg_fx"
    zorder 22
    add Solid(sg_fx_dark) at sg_fx_t_bolt_dark
    add Solid("#FFFFFF") at sg_fx_t_bolt_flash
    add d at sg_fx_t_bolt_line
    timer 1.5 action Function(sg_fx_end, "번개")

## 스포트라이트: 얼굴 둘레만 남기고 어두워진다. 3초
screen sg_fx_spot(d, x, y):
    layer "sg_fx"
    zorder 16
    add d at sg_fx_t_spot(x, y)
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
                    add sg_fx_pix("err-icon", sg_fx_art["err_icon"], {"o": sg_fx_ink, "r": sg_fx_red, "w": "#FFFFFF"}, 4)
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
        import math
        import random

        W, H = env["W"], env["H"]
        art = sg_fx_art
        pal = {"d": "#D94F7C", "p": "#FF8FB0", "l": "#FFD0DC", "q": "#F26B94"}
        shapes = {
            "a": lambda: art["petal_a"],
            "b": lambda: art["petal_b"],
            "c": lambda: art["petal_c"],
            "ma": lambda: sg_fx_mirrored(art["petal_a"]),
            "mb": lambda: sg_fx_mirrored(art["petal_b"]),
            "da": lambda: art["petal_da"],
            "db": lambda: art["petal_db"],
            "dc": lambda: art["petal_dc"],
            "ta": lambda: sg_fx_transposed(art["petal_da"]),
            "tb": lambda: sg_fx_transposed(art["petal_db"]),
        }
        ## 팔랑 한 바퀴: 곧게 선 것과 기운 것
        orders = [
            ["a", "a", "a", "b", "c", "mb", "ma", "ma", "ma", "mb", "c", "b"],
            ["da", "da", "da", "db", "dc", "tb", "ta", "ta", "ta", "tb", "dc", "db"],
        ]

        def frame(name, turn, unit):
            return sg_fx_pix("petal-%s-%d-%d" % (name, turn, unit),
                             lambda: sg_fx_turned(shapes[name](), turn), pal, unit)

        items = []
        for i in range(44):
            unit = random.choice([3, 4, 4, 5, 6])
            turn = random.randrange(4)
            size = 9 * unit
            dur = random.uniform(1.15, 1.4)
            n = int(round(dur * 12))
            sy = int(math.ceil((H + size * 2) / float(n) / unit)) * unit
            sx = int(round(sy * random.uniform(0.3, 0.55) / unit)) * unit
            items.append({
                "frames": [frame(name, turn, unit) for name in orders[0 if i % 3 == 0 else 1]],
                "x": random.uniform(-sx * n, W - size * 0.5),
                "y": -size,
                "sx": sx,
                "sy": sy,
                "n": n,
                "dur": dur,
                ## 처음부터 화면이 차 있고, 2.9초 전에 마지막 장이 빠진다
                "delay": random.uniform(-dur, 2.8 - 2 * dur),
                "spin": random.uniform(0.9, 1.3),
            })
        return {"d": SgFxSprites("petal", items, 2.9)}, None

    def sg_fx_build_sparks(env):
        import random

        W, H = env["W"], env["H"]
        art = sg_fx_art
        pal = {"y": sg_fx_marker, "w": "#FFFFFF", "o": sg_fx_ink}
        order = ["s", "m", "l", "m", "s"]

        items = []
        for i in range(24):
            unit = random.choice([3, 4, 4, 6])
            size = 13 * unit
            items.append({
                "frames": [
                    sg_fx_pix("spark-%s-%d" % (name, unit),
                              lambda: sg_fx_outlined(art["spark_" + name], "o"), pal, unit)
                    for name in order
                ],
                "x": random.uniform(0, W - size),
                "y": random.uniform(0, H - size),
                "delay": random.uniform(0, 1.3),
            })
        return {"d": SgFxSprites("spark", items, 2.4)}, None

    def sg_fx_build_lines(env):
        unit = 4
        d = SgFxLines(env["W"], env["H"], env["cx"], env["cy"], max(env["pw"], env["ph"]) * 0.62, unit, 1.4)
        return {"d": Transform(d, zoom=unit, nearest=True)}, None

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
        pal = {"o": sg_fx_ink, "r": sg_fx_red, "w": "#FFFFFF", "s": "#A81F36"}

        items = []
        for i in range(18):
            unit = random.choice([4, 6, 6, 8])
            w = 9 * unit
            h = 8 * unit
            dur = random.uniform(1.3, 1.9)
            n = int(round(dur * 11))
            rise = random.uniform(0.45, 0.95) * H + h
            items.append({
                "frames": [sg_fx_pix("heart-%d" % unit, sg_fx_art["heart"], pal, unit)],
                "x": random.uniform(w * 0.5, W - w * 1.5),
                "y": H + unit,
                "sx": random.randint(-1, 1) * unit,
                "sy": int(round(rise / n / unit)) * unit,
                "n": n,
                "dur": dur,
                "delay": random.uniform(0, 0.8),
                "unit": unit,
            })
        return {"d": SgFxSprites("heart", items, 2.8)}, None

    def sg_fx_build_shake(env):
        return {}, sg_fx_t_shake

    def sg_fx_build_blackout(env):
        return {"x": env["cx"], "y": env["cy"]}, None

    def sg_fx_build_red(env):
        return {}, None

    def sg_fx_build_mono(env):
        return {}, sg_fx_t_mono

    def sg_fx_build_rain(env):
        import math
        import random

        W, H = env["W"], env["H"]
        near = sg_fx_pix("drop-near", sg_fx_art["drop"], {"b": sg_fx_ink}, 4)
        far = sg_fx_pix("drop-far", sg_fx_art["drop"], {"b": "#5E78C4"}, 2)

        items = []
        for i in range(84):
            is_near = (i % 2 == 0)
            unit = 4 if is_near else 2
            h = 12 * unit
            dur = random.uniform(0.5, 0.7) if is_near else random.uniform(0.8, 1.1)
            n = int(round(dur * 14))
            sy = int(math.ceil((H + h * 2) / float(n) / (unit * 3))) * unit * 3
            items.append({
                "frames": [near if is_near else far],
                "x": random.uniform(0, W + sy * n / 3.0),
                "y": -h,
                "sx": -sy // 3,
                "sy": sy,
                "n": n,
                "dur": dur,
                "delay": -random.uniform(0, dur),
            })
        return {"d": SgFxSprites("drop", items, 3.4)}, None

    def sg_fx_build_bolt(env):
        unit = 6
        ## 번개 끝이 대사창 위에서 보이게 무대 높이에 맞춘다
        d = SgFxBolt(env["W"], env["H"], env["ui_top"], unit)
        return {"d": Transform(d, zoom=unit, nearest=True)}, None

    def sg_fx_build_spot(env):
        import math
        unit = 8
        pad = 12
        radius = math.sqrt(env["pw"] ** 2 + env["ph"] ** 2) / 2 * 0.98
        d = SgFxSpot(env["W"], env["H"], env["cx"], env["cy"], radius, unit, pad)
        return {"d": Transform(d, zoom=unit, nearest=True), "x": -pad * unit, "y": -pad * unit}, None

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

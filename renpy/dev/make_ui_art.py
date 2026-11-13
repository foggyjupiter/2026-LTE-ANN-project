"""미소녀 게임풍 화면 장식(renpy/game/images/ui/gal_*.png)을 만든다. 개발용이다.

    python3 renpy/dev/make_ui_art.py

Pillow가 필요하다. 만든 PNG는 깃에 올려 두므로 게임을 켤 때는 이 스크립트가 필요 없다.
크게(S배) 그린 뒤 줄여서 가장자리를 매끄럽게 한다. 대부분은 Ren'Py의 Frame(9칸 늘이기)으로
늘여 쓰는 그림이라, 늘어나도 되는 가운데와 늘어나면 안 되는 모서리 장식을 나눠 그렸다.
제목 그림은 fonts/Jua-Regular.ttf 로 찍는다.
"""
import math
import pathlib
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

GAME = pathlib.Path(__file__).resolve().parent.parent / "game"
OUT = GAME / "images" / "ui"
FONT = GAME / "fonts" / "Jua-Regular.ttf"
S = 3

PINK = "#ff7fae"
PINK_DEEP = "#f2558e"
PINK_SOFT = "#ffc3d9"
PINK_PALE = "#ffe6f0"
CREAM = "#fffafc"
SKY = "#bfe6ff"
SKY_DEEP = "#6db8f5"
GOLD = "#e6b44a"
GOLD_PALE = "#fff0bd"
PLUM = "#4a2a48"
WHITE = "#ffffff"


def rgba(color, alpha=255):
    h = color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def new(w, h):
    return Image.new("RGBA", (round(w * S), round(h * S)), (0, 0, 0, 0))


def save(im, w, h, name):
    OUT.mkdir(parents=True, exist_ok=True)
    im.resize((w, h), Image.LANCZOS).save(OUT / f"{name}.png", optimize=True)
    print(f"ui/{name}.png")


def box(*values):
    return [round(v * S) for v in values]


def layer(im, draw_fn):
    """투명한 판에 그린 뒤 겹친다. 반투명한 색이 섞이게 하려는 것이다."""
    top = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(top))
    im.alpha_composite(top)


def grad_rr(im, b, r, top, bottom):
    """위에서 아래로 번지는 색으로 채운 둥근 네모."""
    w, h = im.size
    strip = Image.new("RGBA", (1, h))
    y0, y1 = b[1] * S, b[3] * S
    for y in range(h):
        t = min(1.0, max(0.0, (y - y0) / max(1.0, y1 - y0)))
        strip.putpixel((0, y), tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(4)))
    fill = strip.resize((w, h))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box(*b), radius=round(r * S), fill=255)
    im.alpha_composite(Image.composite(fill, Image.new("RGBA", im.size, (0, 0, 0, 0)), mask))


def line_rr(im, b, r, color, width):
    layer(im, lambda d: d.rounded_rectangle(box(*b), radius=round(r * S), outline=color, width=round(width * S)))


def heart_points(cx, cy, w, h, steps=80):
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(((cx + x / 32.0 * w) * S, (cy - (y - 2.5) / 30.0 * h) * S))
    return pts


def heart(im, cx, cy, w, h, fill, outline=None, width=0, shine=True):
    if outline is not None:
        layer(im, lambda d: d.polygon(heart_points(cx, cy, w + width * 2, h + width * 2), fill=outline))
    layer(im, lambda d: d.polygon(heart_points(cx, cy, w, h), fill=fill))
    if shine:
        layer(im, lambda d: d.ellipse(box(cx - w * 0.30, cy - h * 0.30, cx - w * 0.12, cy - h * 0.12),
                                      fill=(255, 255, 255, 190)))


def flower(im, cx, cy, r, petal, center):
    def draw(d):
        for i in range(5):
            a = -math.pi / 2 + 2 * math.pi * i / 5
            px, py = cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55
            d.ellipse(box(px - r * 0.5, py - r * 0.5, px + r * 0.5, py + r * 0.5), fill=petal)
        d.ellipse(box(cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3), fill=center)
    layer(im, draw)


def sparkle(im, cx, cy, r, fill):
    pts = []
    for i in range(8):
        a = math.pi * i / 4 - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.3
        pts.append(((cx + math.cos(a) * rad) * S, (cy + math.sin(a) * rad) * S))
    layer(im, lambda d: d.polygon(pts, fill=fill))


def with_glow(im, color, radius):
    """그림 둘레에 번지는 빛을 깐다."""
    alpha = im.getchannel("A").filter(ImageFilter.GaussianBlur(radius * S))
    halo = Image.new("RGBA", im.size, color[:3] + (0,))
    halo.putalpha(alpha.point(lambda v: min(255, int(v * color[3] / 255 * 1.6))))
    halo.alpha_composite(im)
    return halo


# ------------------------------------------------------------------ 대사창

def textbox():
    """대사창. 9칸 늘이기, 테두리 56. 모서리에 작은 꽃, 가는 금색 속테두리.

    미연시의 대사창답게 반투명하다. 뒤의 배경과 스탠딩이 비쳐 보이고,
    글은 Ren'Py 쪽에서 흰 테두리를 둘러 읽히게 한다.
    """
    w = h = 176
    im = new(w, h)
    grad_rr(im, (4, 4, w - 4, h - 4), 22, rgba(CREAM, 138), rgba("#ffcfe0", 176))
    line_rr(im, (4, 4, w - 4, h - 4), 22, rgba(PINK, 235), 2)
    line_rr(im, (9.5, 9.5, w - 9.5, h - 9.5), 17, rgba(GOLD, 215), 1)
    line_rr(im, (6.4, 6.4, w - 6.4, h - 6.4), 20, rgba(WHITE, 200), 1.2)
    for cx, cy in ((14, 14), (w - 14, 14), (14, h - 14), (w - 14, h - 14)):
        flower(im, cx, cy, 8.4, rgba(PINK), rgba(GOLD_PALE))
        flower(im, cx, cy, 6.2, rgba("#ffb3cf"), rgba(GOLD))
    for cx, cy in ((30, 9.5), (w - 30, 9.5), (30, h - 9.5), (w - 30, h - 9.5)):
        sparkle(im, cx, cy, 3.2, rgba(GOLD))
    save(im, w, h, "gal_textbox")


def nametag():
    """이름표 리본. 흰 그림이라 Ren'Py에서 캐릭터 대표색을 입힌다. 좌우 테두리 36."""
    w, h = 132, 52
    im = new(w, h)
    # 뒤로 접힌 꼬리
    layer(im, lambda d: d.polygon([(p[0] * S, p[1] * S) for p in
                                   ((2, 14), (26, 14), (26, 50), (2, 50), (12, 32))], fill=(205, 205, 205, 255)))
    layer(im, lambda d: d.polygon([(p[0] * S, p[1] * S) for p in
                                   ((w - 2, 14), (w - 26, 14), (w - 26, 50), (w - 2, 50), (w - 12, 32))],
                                  fill=(205, 205, 205, 255)))
    layer(im, lambda d: d.polygon([(p[0] * S, p[1] * S) for p in ((16, 44), (26, 44), (26, 50))],
                                  fill=(150, 150, 150, 255)))
    layer(im, lambda d: d.polygon([(p[0] * S, p[1] * S) for p in ((w - 16, 44), (w - 26, 44), (w - 26, 50))],
                                  fill=(150, 150, 150, 255)))
    layer(im, lambda d: d.rounded_rectangle(box(16, 2, w - 16, 44), radius=6 * S, fill=(255, 255, 255, 255)))
    save(im, w, h, "gal_nametag")

    trim = new(w, h)   # 리본 위에 겹치는 흰 바느질 선과 광택
    def stitches(d):
        for x in range(22, w - 22, 8):
            d.line(box(x, 7, x + 4, 7), fill=(255, 255, 255, 210), width=round(1.4 * S))
            d.line(box(x, 39, x + 4, 39), fill=(255, 255, 255, 210), width=round(1.4 * S))
    layer(trim, stitches)
    layer(trim, lambda d: d.rounded_rectangle(box(18, 4, w - 18, 20), radius=5 * S, fill=(255, 255, 255, 46)))
    save(trim, w, h, "gal_nametag_trim")


def ctc():
    im = new(34, 32)
    heart(im, 17, 16, 24, 22, rgba(PINK), rgba(WHITE), 2.6)
    save(im, 34, 32, "gal_ctc")


# ------------------------------------------------------------------ 선택지, 단추

def bar(name, top, bottom, edge, glow=None, gem=GOLD):
    """가운데 가로 막대. 좌우 테두리 46, 위아래 14. 양끝에 마름모 장식. 둘레 10픽셀은 빛이 번질 자리다."""
    w, h, m = 200, 76, 10
    im = new(w, h)
    grad_rr(im, (m, m, w - m, h - m), (h - 2 * m) / 2, top, bottom)
    line_rr(im, (m, m, w - m, h - m), (h - 2 * m) / 2, edge, 2.6)
    line_rr(im, (m + 4, m + 4, w - m - 4, h - m - 4), (h - 2 * m) / 2 - 4, rgba(WHITE, 220), 1.4)
    for cx in (m + 24, w - m - 24):
        sparkle(im, cx, h / 2, 9, rgba(gem))
        sparkle(im, cx, h / 2, 4.5, rgba(WHITE))
    for cx in (m + 38, w - m - 38):
        layer(im, lambda d, cx=cx: d.ellipse(box(cx - 2, h / 2 - 2, cx + 2, h / 2 + 2), fill=rgba(gem)))
    if glow is not None:
        im = with_glow(im, glow, 5)
    save(im, w, h, name)


def button(name, top, bottom, edge, glow=None):
    """큰 단추. 테두리 30. 위쪽에 광택."""
    w, h, m = 120, 72, 8
    im = new(w, h)
    grad_rr(im, (m, m, w - m, h - m), 22, top, bottom)
    line_rr(im, (m, m, w - m, h - m), 22, edge, 2.6)
    layer(im, lambda d: d.rounded_rectangle(box(m + 8, m + 5, w - m - 8, m + 17), radius=7 * S,
                                            fill=(255, 255, 255, 80)))
    if glow is not None:
        im = with_glow(im, glow, 5)
    save(im, w, h, name)


def speech():
    """직접 말하기 칸: 꼬리가 왼쪽 아래로 난 말풍선. 테두리 왼쪽 64, 오른쪽 30, 위 24, 아래 38."""
    w, h = 160, 100
    im = new(w, h)
    tail = [(34, h - 26), (58, h - 26), (30, h - 3)]
    layer(im, lambda d: d.polygon([(x * S, y * S) for x, y in tail], fill=rgba(PINK)))
    layer(im, lambda d: d.rounded_rectangle(box(3, 3, w - 3, h - 20), radius=20 * S, fill=rgba(PINK)))
    inner = [(37.5, h - 28), (54, h - 28), (33.5, h - 9)]
    layer(im, lambda d: d.polygon([(x * S, y * S) for x, y in inner], fill=rgba(CREAM, 255)))
    grad_rr(im, (5.8, 5.8, w - 5.8, h - 22.8), 17.5, rgba(WHITE, 255), rgba("#fff0f6", 255))
    save(im, w, h, "gal_speech")


# ------------------------------------------------------------------ 위쪽 표시

def plate():
    """위쪽 표시의 바탕 판. 테두리 22."""
    w, h = 72, 48
    im = new(w, h)
    grad_rr(im, (2, 2, w - 2, h - 2), 16, rgba(CREAM, 200), rgba("#ffdcea", 206))
    line_rr(im, (2, 2, w - 2, h - 2), 16, rgba(PINK), 2.4)
    line_rr(im, (5, 5, w - 5, h - 5), 13, rgba(WHITE, 230), 1.3)
    save(im, w, h, "gal_plate")


def sign():
    """장소 팻말. 테두리 좌우 26, 위 20, 아래 14. 위에 줄을 건 못이 있다."""
    w, h = 96, 58
    im = new(w, h)
    for x in (22, w - 22):
        layer(im, lambda d, x=x: d.line(box(x, 12, w / 2, 2), fill=rgba("#b98a5a"), width=round(1.6 * S)))
    layer(im, lambda d: d.ellipse(box(w / 2 - 3, 0, w / 2 + 3, 6), fill=rgba(GOLD)))
    grad_rr(im, (2, 12, w - 2, h - 2), 9, rgba("#e9f6ff", 212), rgba(SKY, 216))
    line_rr(im, (2, 12, w - 2, h - 2), 9, rgba(SKY_DEEP), 2.4)
    line_rr(im, (5, 15, w - 5, h - 5), 6, rgba(WHITE, 230), 1.3)
    for x in (12, w - 12):
        layer(im, lambda d, x=x: d.ellipse(box(x - 2.4, 32.6, x + 2.4, 37.4), fill=rgba(GOLD)))
    save(im, w, h, "gal_sign")


def heart_row(name, fill, outline, shine):
    """하트 열 개가 한 줄로 선 호감도 게이지. 채운 줄과 빈 줄을 겹쳐서 쓴다."""
    cell, h = 24, 24
    im = new(cell * 10, h)
    for i in range(10):
        heart(im, cell * i + cell / 2, h / 2, 17, 15.5, fill, outline, 2.2, shine)
    save(im, cell * 10, h, name)


def small_flower(name, petal, center):
    im = new(20, 20)
    flower(im, 10, 10, 8.6, petal, center)
    save(im, 20, 20, name)


def burst(name, color, kind):
    """호감도 변화 뒤에 깔리는 하트. up: 터지는 하트, down: 금 간 하트, zero: 옅은 하트, nan: 어긋난 하트."""
    w, h = 190, 160
    im = new(w, h)
    cx, cy = w / 2, h / 2 + 4
    if kind == "up":
        rnd = random.Random(7)
        for i in range(12):
            a = 2 * math.pi * i / 12 + 0.2
            d0 = 62 + rnd.random() * 14
            x, y = cx + math.cos(a) * d0 * 1.15, cy + math.sin(a) * d0 * 0.95
            if i % 2:
                heart(im, x, y, 15, 14, rgba(PINK_SOFT), rgba(WHITE), 1.6, False)
            else:
                sparkle(im, x, y, 9, rgba(GOLD_PALE))
                sparkle(im, x, y, 6, rgba(GOLD))
    heart(im, cx, cy, 104, 94, rgba(color, 235), rgba(WHITE, 240), 5)
    if kind == "down":
        crack = [(cx - 4, cy - 34), (cx + 8, cy - 14), (cx - 8, cy + 2), (cx + 6, cy + 18), (cx - 2, cy + 40)]
        layer(im, lambda d: d.line([(x * S, y * S) for x, y in crack], fill=rgba(WHITE), width=round(5 * S), joint="curve"))
        layer(im, lambda d: d.line([(x * S, y * S) for x, y in crack], fill=rgba("#2f5f9f"), width=round(2 * S), joint="curve"))
        for x, y in ((cx - 62, cy + 44), (cx + 60, cy + 50), (cx - 40, cy + 64), (cx + 34, cy + 68)):
            layer(im, lambda d, x=x, y=y: d.ellipse(box(x - 4, y - 7, x + 4, y + 7), fill=rgba("#9fd0ff", 220)))
    if kind == "nan":
        src = im.copy()
        im = new(w, h)
        band = h * S // 6
        for i in range(6):                       # 가로로 썰어서 어긋나게 놓는다
            piece = src.crop((0, i * band, w * S, (i + 1) * band))
            im.alpha_composite(piece, (max(0, (9 if i % 2 else 0) * S), i * band))
        for x, y in ((30, 30), (160, 40), (36, 128), (150, 124)):
            sparkle(im, x, y, 8, rgba("#e6d6ff"))
    save(im, w, h, name)


# ------------------------------------------------------------------ 속마음 구름

def cloud():
    """만화의 생각 풍선. 너비 290에 맞췄다. 테두리 32, 옆 가장자리는 몽실한 무늬가 36마다 되풀이된다."""
    w, h, pad, step = 290, 32 * 2 + 72, 13, 36
    im = new(w, h)
    def bumps(d):
        d.rounded_rectangle(box(pad, pad, w - pad, h - pad), radius=18 * S, fill=rgba(WHITE, 232))
        n = round((w - 2 * pad - 24) / step)
        for i in range(n + 1):
            x = pad + 12 + (w - 2 * pad - 24) * i / n
            for y in (pad + 3, h - pad - 3):
                d.ellipse(box(x - 21, y - 13, x + 21, y + 13), fill=rgba(WHITE, 232))
        for y in (32 + 18, 32 + 54):
            for x in (pad + 2, w - pad - 2):
                d.ellipse(box(x - 12, y - 19, x + 12, y + 19), fill=rgba(WHITE, 232))
        for x, y in ((pad + 7, pad + 8), (w - pad - 7, pad + 8), (pad + 7, h - pad - 8), (w - pad - 7, h - pad - 8)):
            d.ellipse(box(x - 15, y - 14, x + 15, y + 14), fill=rgba(WHITE, 232))
    layer(im, bumps)
    edge = im.getchannel("A").filter(ImageFilter.MaxFilter(2 * S + 1))
    outline = Image.new("RGBA", im.size, rgba(PINK_SOFT))
    outline.putalpha(edge)
    outline.alpha_composite(im)
    save(outline, w, h, "gal_cloud")

    tail = new(64, 50)
    for cx, cy, r in ((20, 18, 13), (48, 38, 7.5)):
        layer(tail, lambda d, cx=cx, cy=cy, r=r: d.ellipse(box(cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), fill=rgba(PINK_SOFT)))
        layer(tail, lambda d, cx=cx, cy=cy, r=r: d.ellipse(box(cx - r, cy - r, cx + r, cy + r), fill=rgba(WHITE, 250)))
    save(tail, 64, 50, "gal_cloud_tail")


# ------------------------------------------------------------------ 카드, 창

def card(name, edge, inner, glow=None):
    """카드와 가운데 창의 액자. 테두리 40. 둘레 10픽셀은 빛이 번질 자리다."""
    w = h = 140
    m = 10
    im = new(w, h)
    grad_rr(im, (m, m, w - m, h - m), 20, rgba(WHITE, 250), rgba("#fff1f6", 250))
    line_rr(im, (m, m, w - m, h - m), 20, edge, 3)
    line_rr(im, (m + 6, m + 6, w - m - 6, h - m - 6), 14, inner, 1.4)
    for cx, cy in ((m + 12, m + 12), (w - m - 12, m + 12), (m + 12, h - m - 12), (w - m - 12, h - m - 12)):
        flower(im, cx, cy, 9.5, edge, rgba(GOLD_PALE))
        flower(im, cx, cy, 7, rgba("#ffc0d6"), rgba(GOLD))
    if glow is not None:
        im = with_glow(im, glow, 6)
    save(im, w, h, name)


def ribbon():
    """끝이 접힌 띠. 흰 그림이라 색을 입혀 쓴다. 좌우 테두리 22."""
    w, h = 100, 34
    im = new(w, h)
    for side in (0, 1):
        pts = ((0, 8), (20, 8), (20, 34), (0, 34), (8, 21))
        pts = [((w - x) if side else x, y) for x, y in pts]
        layer(im, lambda d, pts=pts: d.polygon([(x * S, y * S) for x, y in pts], fill=(200, 200, 200, 255)))
        fold = ((12, 28), (20, 28), (20, 34))
        fold = [((w - x) if side else x, y) for x, y in fold]
        layer(im, lambda d, fold=fold: d.polygon([(x * S, y * S) for x, y in fold], fill=(140, 140, 140, 255)))
    layer(im, lambda d: d.rectangle(box(12, 0, w - 12, 28), fill=(255, 255, 255, 255)))
    layer(im, lambda d: d.line(box(14, 3.5, w - 14, 3.5), fill=(255, 255, 255, 255), width=round(1 * S)))
    save(im, w, h, "gal_ribbon")


def petal():
    im = new(26, 22)
    pts = [(13, 2), (22, 8), (20, 18), (13, 21), (6, 18), (4, 8)]
    layer(im, lambda d: d.polygon([(x * S, y * S) for x, y in pts], fill=rgba("#ffb7d0", 235)))
    layer(im, lambda d: d.ellipse(box(6, 3, 20, 20), fill=rgba("#ffc8dc", 240)))
    layer(im, lambda d: d.polygon([(x * S, y * S) for x, y in ((13, 0), (16, 6), (10, 6))], fill=(0, 0, 0, 0)))
    im = im.filter(ImageFilter.GaussianBlur(0.4 * S))
    save(im, 26, 22, "gal_petal")


def title():
    """고르기 화면의 제목 그림. 귀여운 글꼴에 흰 테두리, 분홍 그러데이션, 옅은 그림자."""
    w, h = 760, 120
    text = "전학생 환영 소개팅"
    font = ImageFont.truetype(str(FONT), 70 * S)
    mask = Image.new("L", (w * S, h * S), 0)
    d = ImageDraw.Draw(mask)
    tw = d.textlength(text, font=font)
    x, y = (w * S - tw) / 2, 16 * S
    d.text((x, y), text, font=font, fill=255)
    wide = Image.new("L", mask.size, 0)
    ImageDraw.Draw(wide).text((x, y), text, font=font, fill=255, stroke_width=4 * S)
    wider = Image.new("L", mask.size, 0)
    ImageDraw.Draw(wider).text((x, y), text, font=font, fill=255, stroke_width=8 * S)

    im = new(w, h)
    shadow = Image.new("RGBA", im.size, rgba(PINK_DEEP, 0))
    shadow.putalpha(wider.filter(ImageFilter.GaussianBlur(3 * S)).point(lambda v: int(v * 0.55)))
    im.alpha_composite(shadow, (0, 4 * S))
    rim = Image.new("RGBA", im.size, rgba(PINK_DEEP))
    rim.putalpha(wider)
    im.alpha_composite(rim)
    white = Image.new("RGBA", im.size, rgba(WHITE))
    white.putalpha(wide)
    im.alpha_composite(white)
    strip = Image.new("RGBA", (1, h * S))
    for yy in range(h * S):
        t = min(1.0, max(0.0, (yy - 22 * S) / (70.0 * S)))
        a, b = rgba("#ff9cc2"), rgba("#f0468a")
        strip.putpixel((0, yy), tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4)))
    fill = strip.resize(im.size)
    fill.putalpha(mask)
    im.alpha_composite(fill)
    for cx in (x / S - 34, (x + tw) / S + 34):
        heart(im, cx, 58, 34, 31, rgba(PINK), rgba(WHITE), 3.4)
    for cx, cy in ((x / S - 66, 34), ((x + tw) / S + 66, 86)):
        sparkle(im, cx, cy, 10, rgba(GOLD))
    save(im, w, h, "gal_title")


# ------------------------------------------------------------------ 엔딩

def stamp():
    """등급 도장의 테. 빨간 인주가 군데군데 덜 묻은 것처럼 보이게 한다. 글자는 Ren'Py가 찍는다."""
    w = h = 150
    im = new(w, h)
    red = (214, 38, 60, 225)
    layer(im, lambda d: d.ellipse(box(6, 6, w - 6, h - 6), outline=red, width=round(7 * S)))
    layer(im, lambda d: d.ellipse(box(19, 19, w - 19, h - 19), outline=red, width=round(2.2 * S)))
    for a in range(0, 360, 30):
        x = w / 2 + math.cos(math.radians(a)) * 62.5
        y = h / 2 + math.sin(math.radians(a)) * 62.5
        sparkle(im, x, y, 3.4, red)
    rnd = random.Random(11)
    alpha = im.getchannel("A")
    d = ImageDraw.Draw(alpha)
    for _ in range(260):
        x, y, r = rnd.random() * w * S, rnd.random() * h * S, rnd.random() * 2.2 * S
        d.ellipse((x - r, y - r, x + r, y + r), fill=0)
    im.putalpha(alpha)
    save(im, w, h, "gal_stamp")


def laurel():
    """칭호 배지 옆의 월계수 가지 (왼쪽 것. 오른쪽은 뒤집어 쓴다)."""
    w, h = 40, 64
    im = new(w, h)
    def draw(d):
        stem = []
        for i in range(13):
            t = i / 12
            ang = math.radians(250 - 150 * t)
            stem.append(((34 + math.cos(ang) * 26) * S, (34 - math.sin(ang) * 28 + 0) * S))
        d.line(stem, fill=rgba(GOLD), width=round(2 * S), joint="curve")
        for i in range(1, 12, 2):
            x, y = stem[i][0] / S, stem[i][1] / S
            ang = math.radians(250 - 150 * i / 12)
            for side in (-1, 1):
                la = ang + side * 0.9 + math.pi / 2
                pts = []
                for k in range(16):
                    u = 2 * math.pi * k / 16
                    ex, ey = math.cos(u) * 7.5, math.sin(u) * 3.2
                    px = x + math.cos(la) * 6 + ex * math.cos(la) - ey * math.sin(la)
                    py = y - math.sin(la) * 6 - (ex * math.sin(la) + ey * math.cos(la))
                    pts.append((px * S, py * S))
                d.polygon(pts, fill=rgba(GOLD if side < 0 else "#f2cd6b"))
    layer(im, draw)
    save(im, w, h, "gal_laurel")


def main():
    textbox()
    nametag()
    ctc()
    bar("gal_choice", rgba(WHITE, 196), rgba("#ffd6e6", 204), rgba(PINK))   # 스탠딩이 비치게 반투명
    bar("gal_choice_hover", rgba("#fffbe6", 255), rgba("#ffc2da", 255), rgba(PINK_DEEP), rgba("#ff8fbd", 210))
    button("gal_btn", rgba("#ff9cc2"), rgba("#f25a93"), rgba(WHITE))
    button("gal_btn_hover", rgba("#ffb6d2"), rgba("#ff6fa5"), rgba(WHITE), rgba("#ff8fbd", 220))
    button("gal_btn_off", rgba("#d9d3da"), rgba("#bdb5c0"), rgba(WHITE))
    button("gal_btn2", rgba(WHITE), rgba("#ffe9f1"), rgba(PINK))
    button("gal_btn2_hover", rgba("#fffbe6"), rgba("#ffd6e6"), rgba(PINK_DEEP), rgba("#ff8fbd", 200))
    speech()
    plate()
    sign()
    heart_row("gal_hearts_full", rgba(PINK), rgba(WHITE), True)
    heart_row("gal_hearts_empty", rgba("#f3dfe8", 235), rgba("#e8a9c2", 255), False)
    small_flower("gal_flower_on", rgba(PINK), rgba(GOLD_PALE))
    small_flower("gal_flower_off", rgba(WHITE, 235), rgba("#f1c6d8"))
    burst("gal_burst_up", PINK, "up")
    burst("gal_burst_down", "#7fb4ee", "down")
    burst("gal_burst_zero", "#cfc3d4", "zero")
    burst("gal_burst_nan", "#b48cff", "nan")
    cloud()
    card("gal_card", rgba(PINK), rgba(GOLD, 220))
    card("gal_card_hover", rgba(PINK_DEEP), rgba(GOLD), rgba("#ff8fbd", 230))
    ribbon()
    petal()
    title()
    stamp()
    laurel()


if __name__ == "__main__":
    main()

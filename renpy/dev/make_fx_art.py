"""sg_fx 가 쓰는 매끄러운 그림(renpy/game/images/fx/*.png)을 만든다.

    python3 renpy/dev/make_fx_art.py renpy/game/images/fx

크게 그려서 줄이는 방식으로 가장자리를 매끄럽게 한다. 번개와 집중선은 씨앗값을 고정해 매번 같은 그림이 나온다.
"""
import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
INK = (27, 37, 89)
DARK = (11, 16, 48)


def save(im, name):
    im.save(os.path.join(OUT, name), optimize=True)
    print(name, im.size)


def tint(mask, color, alpha=1.0):
    """흰 모양(L)을 색과 불투명도가 있는 그림으로 바꾼다."""
    out = Image.new("RGBA", mask.size, color + (0,))
    out.putalpha(mask.point(lambda v: int(v * alpha)))
    return out


def shrink(im, size):
    return im.resize(size, Image.LANCZOS)


# ---------- 꽃잎: 벚꽃잎 한 장이 돌며 뒤집히는 16장 ----------
def petal_base(light, deep):
    s = 256
    m = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(m)
    pts = []
    for i in range(200):
        t = i / 199.0 * 2 * math.pi
        # 위가 둥글고 아래가 뾰족한 물방울 모양
        r = 0.5 + 0.5 * math.cos(t)          # 1: 아래 끝, 0: 위
        x = math.sin(t) * (0.36 - 0.20 * r ** 1.6)
        y = -math.cos(t) * 0.46 + 0.02
        pts.append((s / 2 + x * s, s / 2 - y * s * -1))
    d.polygon(pts, fill=255)
    # 위쪽 가운데의 작은 홈
    d.polygon([(s / 2 - 16, 4), (s / 2 + 16, 4), (s / 2, 46)], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(2.2))
    base = tint(m, deep, 0.94)
    # 가운데를 밝게
    hl = Image.new("L", (s, s), 0)
    ImageDraw.Draw(hl).ellipse((s / 2 - 46, 50, s / 2 + 46, 190), fill=255)
    hl = ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(22)), m)
    base.alpha_composite(tint(hl, light, 0.9))
    # 밝은 배경에서도 보이게 가장자리를 조금 짙게 두른다
    edge = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(9))).filter(ImageFilter.GaussianBlur(1.5))
    base.alpha_composite(tint(edge, (232, 104, 146), 0.75))
    return base


def petal_sheet(light, deep, turn):
    base = petal_base(light, deep)
    n, cell = 16, 64
    sheet = Image.new("RGBA", (cell * n, cell), (0, 0, 0, 0))
    for k in range(n):
        flip = max(0.22, abs(math.cos(math.pi * k / n * 2)))
        im = base.resize((max(1, int(256 * flip)), 256), Image.LANCZOS)
        box = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        box.alpha_composite(im, ((256 - im.width) // 2, 0))
        box = box.rotate(turn * 360.0 * k / n + 25, resample=Image.BICUBIC)
        sheet.alpha_composite(shrink(box, (cell, cell)), (k * cell, 0))
    return sheet


save(petal_sheet((255, 236, 242), (255, 183, 203), 1), "sg_fx_petal_a.png")
save(petal_sheet((255, 224, 234), (252, 150, 180), -1), "sg_fx_petal_b.png")


# ---------- 하트: 통통한 하트. 가로는 불투명도 네 단계, 세로는 기울기 세 가지 ----------
def heart_shape(s, grow=1.0):
    m = Image.new("L", (s, s), 0)
    pts = []
    for i in range(240):
        t = i / 239.0 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((s / 2 + x * s / 40.0 * grow, s / 2 - (y + 2) * s / 40.0 * grow))
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def heart_base():
    # 둘레에 분홍 빛 번짐이 들어갈 자리를 남기고 가운데에 그린다
    s = 400
    rim = heart_shape(s, 0.8).filter(ImageFilter.GaussianBlur(2.5))
    body = heart_shape(s, 0.745).filter(ImageFilter.GaussianBlur(2.5))
    halo = heart_shape(s, 0.84).filter(ImageFilter.GaussianBlur(20))
    im = tint(halo, (255, 132, 170), 0.6)
    im.alpha_composite(tint(rim, (214, 52, 92)))
    im.alpha_composite(tint(body, (246, 88, 122)))
    glow = Image.new("L", (s, s), 0)
    ImageDraw.Draw(glow).ellipse((100, 100, 280, 230), fill=255)
    glow = ImageChops.multiply(glow.filter(ImageFilter.GaussianBlur(30)), body)
    im.alpha_composite(tint(glow, (255, 150, 172), 0.85))
    shine = Image.new("L", (s, s), 0)
    ImageDraw.Draw(shine).ellipse((132, 124, 176, 156), fill=255)
    shine = shine.rotate(28, center=(154, 140)).filter(ImageFilter.GaussianBlur(5))
    im.alpha_composite(tint(shine, (255, 255, 255), 0.85))
    return im


def heart_sheet():
    base = heart_base()
    cell = 96
    sheet = Image.new("RGBA", (cell * 4, cell * 3), (0, 0, 0, 0))
    for row, angle in enumerate((14, 0, -14)):
        im = shrink(base.rotate(angle, resample=Image.BICUBIC), (cell, cell))
        for col, a in enumerate((0.95, 0.7, 0.45, 0.2)):
            part = im.copy()
            part.putalpha(part.getchannel("A").point(lambda v, a=a: int(v * a)))
            sheet.alpha_composite(part, (col * cell, row * cell))
    return sheet


save(heart_sheet(), "sg_fx_heart.png")


# ---------- 반짝이: 네 갈래 별이 커졌다 작아지는 10장 ----------
def spark_base():
    s = 288
    c = s / 2
    m = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(m)
    for long_r, wide in ((132, 13), (60, 9)):
        for q in range(4):
            a = q * math.pi / 2 + (math.pi / 4 if long_r == 60 else 0)
            tip = (c + math.cos(a) * long_r, c + math.sin(a) * long_r)
            left = (c + math.cos(a + math.pi / 2) * wide, c + math.sin(a + math.pi / 2) * wide)
            right = (c + math.cos(a - math.pi / 2) * wide, c + math.sin(a - math.pi / 2) * wide)
            d.polygon([tip, left, right], fill=255)
    d.ellipse((c - 16, c - 16, c + 16, c + 16), fill=255)
    star = m.filter(ImageFilter.GaussianBlur(1.6))
    # 밝은 하늘 앞에서도 보이게 금빛 번짐을 짙게 깔고 그 위에 흰 별을 올린다
    glow = m.filter(ImageFilter.GaussianBlur(18)).point(lambda v: min(255, int(v * 2.6)))
    warm = m.filter(ImageFilter.GaussianBlur(5)).point(lambda v: min(255, int(v * 1.6)))
    im = tint(glow, (255, 196, 84), 0.9)
    im.alpha_composite(tint(warm, (255, 226, 140), 0.95))
    im.alpha_composite(tint(star, (255, 253, 240)))
    return im


def bokeh_base():
    """초점이 나간 둥근 빛망울."""
    s = 288
    c = s / 2
    disc = Image.new("L", (s, s), 0)
    ImageDraw.Draw(disc).ellipse((c - 84, c - 84, c + 84, c + 84), fill=255)
    ring = ImageChops.subtract(disc, disc.filter(ImageFilter.MinFilter(13)))
    im = tint(disc.filter(ImageFilter.GaussianBlur(10)), (255, 206, 226), 0.5)
    im.alpha_composite(tint(ring.filter(ImageFilter.GaussianBlur(3)), (255, 240, 246), 0.8))
    return im


def spark_sheet():
    # 윗줄은 네 갈래 별, 아랫줄은 둥근 빛망울. 가로로 커졌다 작아지는 10장
    n, cell = 10, 72
    sheet = Image.new("RGBA", (cell * n, cell * 2), (0, 0, 0, 0))
    for row, base in enumerate((spark_base(), bokeh_base())):
        for k in range(n):
            f = math.sin(math.pi * (k + 0.5) / n)
            size = max(4, int(cell * (0.25 + 0.75 * f)))
            im = shrink(base, (size, size))
            im.putalpha(im.getchannel("A").point(lambda v, f=f: int(v * (0.35 + 0.65 * f))))
            sheet.alpha_composite(im, (k * cell + (cell - size) // 2, row * cell + (cell - size) // 2))
    return sheet


save(spark_sheet(), "sg_fx_spark.png")


# ---------- 비: 아래로 갈수록 또렷한 빗줄기. 가까운 것과 먼 것 ----------
def drop(w, h, width, alpha):
    k = 4
    fade = Image.linear_gradient("L").resize((w * k, h * k))    # 위는 0, 아래는 255

    def streak(shift, thick):
        m = Image.new("L", (w * k, h * k), 0)
        ImageDraw.Draw(m).line(((w - 3) * k + shift, 2 * k, 3 * k + shift, (h - 2) * k), fill=255, width=thick)
        return ImageChops.multiply(m.filter(ImageFilter.GaussianBlur(k * 0.6)), fade)

    # 밝은 배경에서도 보이게 푸른 그늘 줄을 깔고 그 위에 흰 줄을 올린다
    im = tint(streak(int(1.4 * k), int((width + 1) * k)), (92, 116, 170), alpha * 0.8)
    im.alpha_composite(tint(streak(0, width * k), (236, 243, 255), alpha))
    return shrink(im, (w, h))


save(drop(24, 72, 3, 0.85), "sg_fx_drop_near.png")
save(drop(15, 44, 2, 0.5), "sg_fx_drop_far.png")


# ---------- 암전 속의 눈 ----------
def eyes():
    k = 4
    m = Image.new("L", (120 * k, 52 * k), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((6 * k, 4 * k, 34 * k, 48 * k), fill=255)
    d.ellipse((86 * k, 4 * k, 114 * k, 48 * k), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(k * 0.9))
    return shrink(tint(m, (244, 247, 251)), (120, 52))


save(eyes(), "sg_fx_eyes.png")


# ---------- 스포트라이트: 가장자리가 부드러운 빛의 원과 위에서 내려오는 빛기둥 ----------
# 화면 3배 넓이를 1/8 크기로 그린다. 구멍은 그림 한가운데, 반지름은 화면 기준 208픽셀
def smooth(a, b, v):
    t = min(1.0, max(0.0, (v - a) / float(b - a)))
    return t * t * (3 - 2 * t)


def spot():
    w, h = 480, 270
    cx, cy, r0 = w / 2.0, h / 2.0, 26.0
    px = []
    for y in range(h):
        for x in range(w):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            a = 0.82 * smooth(r0 - 3.5, r0 + 5.0, d)
            if dy < 0:
                t = min(1.0, max(0.0, (y - (cy - 90.0)) / 90.0))
                half = r0 * (0.4 + 0.6 * t)
                a *= 1.0 - 0.22 * (1.0 - smooth(half - 3.0, half + 6.0, abs(dx)))
            px.append(int(a * 255))
    m = Image.new("L", (w, h))
    m.putdata(px)
    return tint(m.filter(ImageFilter.GaussianBlur(0.8)), DARK)


save(spot(), "sg_fx_spot.png")


# ---------- 가장자리가 물드는 비네트 (화면의 1/4 크기). 흑백용 어두운 것과 붉은 화면용 붉은 것 ----------
def vignette(color, strength, inner):
    w, h = 320, 180
    px = []
    for y in range(h):
        for x in range(w):
            dx = (x + 0.5 - w / 2.0) / (w / 2.0)
            dy = (y + 0.5 - h / 2.0) / (h / 2.0)
            px.append(int(255 * strength * smooth(inner, 1.4, math.hypot(dx, dy))))
    m = Image.new("L", (w, h))
    m.putdata(px)
    return tint(m, color)


save(vignette(DARK, 0.5, 0.62), "sg_fx_vignette.png")
save(vignette((226, 59, 78), 0.9, 0.45), "sg_fx_vignette_red.png")


# ---------- 번개: 매끄러운 줄기와 은은한 빛 번짐. 세 가지 ----------
def bolt(seed):
    rnd = random.Random(seed)
    w, h, k = 320, 480, 2
    way = rnd.choice([-1, 1])
    x, y = w / 2.0 + way * -20, -10.0
    pts = [(x, y)]
    while y < h * 0.66:
        y += rnd.uniform(70, 100)
        x += way * rnd.uniform(28, 46)
        pts.append((x, y))
        y += rnd.uniform(2, 10)
        x -= way * rnd.uniform(40, 60)
        pts.append((x, y))
    y += rnd.uniform(60, 80)
    x += way * rnd.uniform(26, 40)
    pts.append((x, min(y, h - 26.0)))
    at = 2 * rnd.randint(1, max(1, (len(pts) - 3) // 2))
    bx, by = pts[at]
    mid = (bx - way * rnd.uniform(36, 50), by + rnd.uniform(40, 56))
    branch = [(bx, by), mid, (mid[0] - way * rnd.uniform(16, 26), mid[1] + rnd.uniform(28, 40))]

    def stroke(path, width):
        m = Image.new("L", (w * k, h * k), 0)
        d = ImageDraw.Draw(m)
        last = len(path) - 1
        for i in range(last):
            thick = max(1.0, width * (1 - 0.55 * i / float(last)))
            (x0, y0), (x1, y1) = path[i], path[i + 1]
            d.line((x0 * k, y0 * k, x1 * k, y1 * k), fill=255, width=int(round(thick * k)))
            rad = thick * k / 2.0
            for (px_, py_) in (path[i], path[i + 1]):
                d.ellipse((px_ * k - rad, py_ * k - rad, px_ * k + rad, py_ * k + rad), fill=255)
        return m

    def layer(width, blur, color, alpha, gain=1.0):
        m = ImageChops.lighter(stroke(pts, width), stroke(branch, width * 0.55))
        m = m.filter(ImageFilter.GaussianBlur(blur * k))
        if gain != 1.0:
            m = m.point(lambda v: min(255, int(v * gain)))
        return tint(m, color, alpha)

    im = layer(28, 14, (255, 232, 150), 0.6, 1.6)
    im.alpha_composite(layer(14, 2.2, (255, 238, 150), 0.95))
    im.alpha_composite(layer(6.5, 0.8, (255, 255, 255), 1.0))
    return shrink(im, (w, h))


for i in range(3):
    save(bolt(20 + i), "sg_fx_bolt_%d.png" % (i + 1))


# ---------- 집중선: 가운데로 모이는 가는 쐐기. 서로 다른 세 장 ----------
# 화면 2배 넓이를 1/2 크기로 그린다. 가운데가 모이는 자리이고, 비워 두는 반지름은 화면 기준 186픽셀
def lines(seed):
    rnd = random.Random(seed)
    w, h, k = 1280, 720, 2
    cx, cy = w * k / 2.0, h * k / 2.0
    clear = 93.0 * k
    far = 1700.0 * k
    squash = 1.0 / math.sqrt(1.35)
    m = Image.new("L", (w * k, h * k), 0)
    d = ImageDraw.Draw(m)

    def pt(r, a):
        return (cx + r * math.cos(a), cy + r * math.sin(a) * squash)

    a = rnd.uniform(0, 2.0)
    while a < 360.0:
        width = rnd.uniform(0.5, 2.6)
        tip = clear * rnd.uniform(1.0, 2.1)
        a0, a1 = math.radians(a), math.radians(a + width)
        d.polygon([pt(tip, (a0 + a1) / 2), pt(far, a0), pt(far, a1)], fill=255)
        a += width + rnd.uniform(1.4, 5.0)
    return shrink(tint(m, INK, 0.94), (w, h))


for i in range(3):
    save(lines(40 + i), "sg_fx_lines_%d.png" % (i + 1))


# ---------- 가짜 오류창의 아이콘과 닫기 단추 ----------
def err_icon():
    k = 6
    s = 44 * k
    rim = Image.new("L", (s, s), 0)
    ImageDraw.Draw(rim).ellipse((2 * k, 2 * k, s - 2 * k, s - 2 * k), fill=255)
    body = Image.new("L", (s, s), 0)
    ImageDraw.Draw(body).ellipse((5 * k, 5 * k, s - 5 * k, s - 5 * k), fill=255)
    cross = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(cross)
    d.line((15 * k, 15 * k, 29 * k, 29 * k), fill=255, width=int(4.4 * k))
    d.line((29 * k, 15 * k, 15 * k, 29 * k), fill=255, width=int(4.4 * k))
    im = tint(rim, (196, 44, 70))
    im.alpha_composite(tint(body, (238, 84, 104)))
    im.alpha_composite(tint(cross, (255, 255, 255)))
    return shrink(im, (44, 44))


def close_box():
    """제목 줄 오른쪽의 둥근 닫기 단추."""
    k = 6
    s = 22 * k
    disc = Image.new("L", (s, s), 0)
    ImageDraw.Draw(disc).ellipse((1 * k, 1 * k, s - 1 * k, s - 1 * k), fill=255)
    cross = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(cross)
    d.line((7 * k, 7 * k, 15 * k, 15 * k), fill=255, width=int(2.0 * k))
    d.line((15 * k, 7 * k, 7 * k, 15 * k), fill=255, width=int(2.0 * k))
    im = tint(disc, (244, 140, 170))
    im.alpha_composite(tint(cross, (255, 255, 255)))
    return shrink(im, (22, 22))


save(err_icon(), "sg_fx_err_icon.png")
save(close_box(), "sg_fx_close.png")


def rounded(size, box, radius, k=4):
    """둥근 네모 모양(L). 크게 그려 줄여서 모서리가 매끄럽다."""
    w, h = size
    m = Image.new("L", (w * k, h * k), 0)
    ImageDraw.Draw(m).rounded_rectangle([v * k for v in box], radius=radius * k, fill=255)
    return shrink(m, (w, h))


def window():
    """
    가짜 오류창의 틀. 둥근 모서리와 부드러운 그림자가 있고 위 44픽셀은 제목 줄이다.
    사방 24픽셀은 그림자 자리다. Ren'Py 에서 Frame 으로 늘려 쓴다.
    """
    w, h, m = 148, 168, 24
    box = (m, m, w - m, h - m)
    shape = rounded((w, h), box, 14)
    shadow = Image.new("L", (w, h), 0)
    shadow.paste(shape, (0, 7))
    im = tint(shadow.filter(ImageFilter.GaussianBlur(9)), (46, 28, 72), 0.38)
    im.alpha_composite(tint(shape, (214, 196, 224)))                                  # 가는 테두리
    inner = rounded((w, h), (m + 1, m + 1, w - m - 1, h - m - 1), 13)
    im.alpha_composite(tint(inner, (255, 252, 253)))
    # 제목 줄: 위쪽만 둥글고 은은한 분홍빛
    bar = Image.new("L", (w, h), 0)
    ImageDraw.Draw(bar).rectangle((0, 0, w, m + 44), fill=255)
    bar = ImageChops.multiply(bar, inner)
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(m, m + 45):
        t = (y - m) / 44.0
        c = tuple(int(a + (b - a) * t) for a, b in zip((255, 214, 228), (247, 226, 240)))
        ImageDraw.Draw(grad).line((0, y, w, y), fill=c + (255,))
    grad.putalpha(bar)
    im.alpha_composite(grad)
    return im


def button(top, bottom):
    """둥근 단추. 사방 6픽셀은 그림자 자리다."""
    w, h, m = 72, 52, 6
    shape = rounded((w, h), (m, m, w - m, h - m), 14)
    shadow = Image.new("L", (w, h), 0)
    shadow.paste(shape, (0, 3))
    im = tint(shadow.filter(ImageFilter.GaussianBlur(3)), (120, 40, 80), 0.35)
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        t = min(1.0, max(0.0, (y - m) / float(h - 2 * m)))
        c = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
        ImageDraw.Draw(grad).line((0, y, w, y), fill=c + (255,))
    grad.putalpha(shape)
    im.alpha_composite(grad)
    return im


save(window(), "sg_fx_win.png")
save(button((255, 150, 182), (242, 110, 150)), "sg_fx_btn.png")
save(button((255, 176, 200), (250, 136, 172)), "sg_fx_btn_hover.png")


# ---------- 자막: 위아래가 부드럽게 사라지는 어두운 띠와 가는 장식선 ----------
def caption_band():
    w, h = 16, 200
    px = []
    for y in range(h):
        # 일반적인 미연시의 대사창처럼 뒤의 그림이 비치게 반투명으로 둔다
        a = 0.42 * smooth(0, 58, y) * smooth(0, 58, h - 1 - y)
        px.extend([int(a * 255)] * w)
    m = Image.new("L", (w, h))
    m.putdata(px)
    return tint(m, (14, 16, 44))


def caption_ornament():
    """양끝이 사라지는 가는 선과 가운데의 작은 벚꽃."""
    w, h, k = 560, 30, 4
    im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    cx, cy = w * k / 2.0, h * k / 2.0
    line = Image.new("L", (w * k, h * k), 0)
    d = ImageDraw.Draw(line)
    for x in range(w * k):
        dist = abs(x - cx) / cx
        if abs(x - cx) < 26 * k:
            continue
        a = int(235 * (1 - dist) ** 1.4)
        d.line((x, cy - k * 0.6, x, cy + k * 0.6), fill=a)
    im.alpha_composite(tint(line, (255, 236, 214)))
    for side in (-1, 1):
        px_ = cx + side * 38 * k
        dia = Image.new("L", (w * k, h * k), 0)
        ImageDraw.Draw(dia).polygon([(px_, cy - 4 * k), (px_ + 4 * k, cy), (px_, cy + 4 * k), (px_ - 4 * k, cy)], fill=255)
        im.alpha_composite(tint(dia, (255, 236, 214), 0.9))
    flower = Image.new("L", (w * k, h * k), 0)
    d = ImageDraw.Draw(flower)
    for i in range(5):
        a = math.radians(i * 72 - 90)
        px_, py_ = cx + math.cos(a) * 7.5 * k, cy + math.sin(a) * 7.5 * k
        d.ellipse((px_ - 5.6 * k, py_ - 5.6 * k, px_ + 5.6 * k, py_ + 5.6 * k), fill=255)
    im.alpha_composite(tint(flower.filter(ImageFilter.GaussianBlur(k * 0.5)), (255, 186, 208)))
    heart = Image.new("L", (w * k, h * k), 0)
    ImageDraw.Draw(heart).ellipse((cx - 3 * k, cy - 3 * k, cx + 3 * k, cy + 3 * k), fill=255)
    im.alpha_composite(tint(heart, (255, 244, 214)))
    return shrink(im, (w, h))


save(caption_band(), "sg_fx_caption_band.png")
save(caption_ornament(), "sg_fx_caption_orn.png")


# ---------- 집중선 뒤에 까는 흰 빛. 가운데(얼굴 자리)는 비우고 그 둘레부터 하얗게 번진다 ----------
# 화면 3배 넓이를 1/8 크기로 그린다. 비워 두는 반지름은 화면 기준 186픽셀
def lines_glow():
    w, h = 480, 270
    cx, cy, c = w / 2.0, h / 2.0, 23.25
    squash = math.sqrt(1.35)
    px = []
    for y in range(h):
        for x in range(w):
            r = math.hypot(x + 0.5 - cx, (y + 0.5 - cy) * squash)
            a = 0.7 * smooth(0.6 * c, 1.25 * c, r) * (1.0 - 0.5 * smooth(1.3 * c, 7.0 * c, r))
            px.append(int(a * 255))
    m = Image.new("L", (w, h))
    m.putdata(px)
    return tint(m.filter(ImageFilter.GaussianBlur(1.0)), (255, 255, 255))


save(lines_glow(), "sg_fx_lines_glow.png")

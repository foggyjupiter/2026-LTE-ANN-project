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
    s = 320
    rim = heart_shape(s, 1.0).filter(ImageFilter.GaussianBlur(2.5))
    body = heart_shape(s, 0.93).filter(ImageFilter.GaussianBlur(2.5))
    im = tint(rim, (214, 52, 92))
    im.alpha_composite(tint(body, (246, 88, 122)))
    glow = Image.new("L", (s, s), 0)
    ImageDraw.Draw(glow).ellipse((60, 60, 240, 190), fill=255)
    glow = ImageChops.multiply(glow.filter(ImageFilter.GaussianBlur(30)), body)
    im.alpha_composite(tint(glow, (255, 150, 172), 0.85))
    shine = Image.new("L", (s, s), 0)
    ImageDraw.Draw(shine).ellipse((92, 84, 136, 116), fill=255)
    shine = shine.rotate(28, center=(114, 100)).filter(ImageFilter.GaussianBlur(5))
    im.alpha_composite(tint(shine, (255, 255, 255), 0.85))
    return im


def heart_sheet():
    base = heart_base()
    cell = 80
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
    glow = m.filter(ImageFilter.GaussianBlur(18)).point(lambda v: min(255, int(v * 2.2)))
    im = tint(glow, (255, 226, 130), 0.75)
    im.alpha_composite(tint(star, (255, 252, 236)))
    return im


def spark_sheet():
    base = spark_base()
    n, cell = 10, 72
    sheet = Image.new("RGBA", (cell * n, cell), (0, 0, 0, 0))
    for k in range(n):
        f = math.sin(math.pi * (k + 0.5) / n)
        size = max(4, int(cell * (0.25 + 0.75 * f)))
        im = shrink(base, (size, size))
        im.putalpha(im.getchannel("A").point(lambda v, f=f: int(v * (0.35 + 0.65 * f))))
        sheet.alpha_composite(im, (k * cell + (cell - size) // 2, (cell - size) // 2))
    return sheet


save(spark_sheet(), "sg_fx_spark.png")


# ---------- 비: 아래로 갈수록 또렷한 빗줄기. 가까운 것과 먼 것 ----------
def drop(w, h, width, alpha):
    k = 4
    m = Image.new("L", (w * k, h * k), 0)
    ImageDraw.Draw(m).line(((w - 3) * k, 2 * k, 3 * k, (h - 2) * k), fill=255, width=width * k)
    m = m.filter(ImageFilter.GaussianBlur(k * 0.6))
    fade = Image.linear_gradient("L").resize((w * k, h * k))    # 위는 0, 아래는 255
    m = ImageChops.multiply(m, fade)
    return shrink(tint(m, (226, 236, 255), alpha), (w, h))


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
    im = tint(rim, INK)
    im.alpha_composite(tint(body, (226, 59, 78)))
    im.alpha_composite(tint(cross, (255, 255, 255)))
    return shrink(im, (44, 44))


def close_box():
    k = 6
    s = 22 * k
    im = Image.new("RGBA", (s, s), (244, 247, 251, 255))
    d = ImageDraw.Draw(im)
    d.line((6 * k, 6 * k, 16 * k, 16 * k), fill=INK + (255,), width=int(2.2 * k))
    d.line((16 * k, 6 * k, 6 * k, 16 * k), fill=INK + (255,), width=int(2.2 * k))
    return shrink(im, (22, 22))


save(err_icon(), "sg_fx_err_icon.png")
save(close_box(), "sg_fx_close.png")

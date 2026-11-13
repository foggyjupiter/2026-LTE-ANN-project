"""sg_stage 가 쓰는 만화 기호 그림(renpy/game/images/emote/*.png)을 만든다.

    python3 renpy/dev/make_emote_art.py [renpy/game/images/emote]

네 배로 크게 그려서 줄이는 방식으로 가장자리를 매끄럽게 한다. 기호마다 짙은 테두리,
흰 가장자리, 위에서 아래로 가는 그러데이션, 광택을 넣어 스티커처럼 보이게 한다.
난수를 쓰지 않으므로 몇 번을 돌려도 같은 그림이 나온다.

기호 그림은 192x192(세로줄만 256x192)이고 화면에서는 sg_stage.rpy 가 절반쯤으로 줄여 쓴다.
장소 제목 카드의 띠(title_band.png, 720x96)도 여기서 만든다.
"""
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "game", "images", "emote")
FONT = os.path.join(HERE, "..", "game", "fonts", "Pretendard-Bold.otf")
os.makedirs(OUT, exist_ok=True)

SS = 4            # 몇 배로 그려서 줄이는가
SIZE = 192        # 그림 한 변
B = SIZE * SS     # 그릴 때의 한 변
WHITE = (255, 255, 255)


def save(im, name):
    im.save(os.path.join(OUT, name), optimize=True)
    print(name, im.size)


def canvas(w=B, h=B):
    return Image.new("L", (w, h), 0)


def tint(mask, color, alpha=1.0):
    """흰 모양(L)을 색과 불투명도가 있는 그림으로 바꾼다."""
    out = Image.new("RGBA", mask.size, color + (0,))
    out.putalpha(mask.point(lambda v: int(v * alpha)))
    return out


def grow(mask, r):
    """모양을 r픽셀쯤 둥글게 부풀린다."""
    soft = mask.filter(ImageFilter.GaussianBlur(r * 0.75))
    return soft.point(lambda v: 255 if v > 22 else 0).filter(ImageFilter.GaussianBlur(SS * 0.6))


def shrink_in(mask, r):
    """모양을 r픽셀쯤 안으로 줄인다."""
    soft = mask.filter(ImageFilter.GaussianBlur(r * 0.75))
    return soft.point(lambda v: 255 if v > 232 else 0).filter(ImageFilter.GaussianBlur(SS * 0.6))


def gradient(mask, top, bottom):
    """모양 안을 위(top)에서 아래(bottom)로 가는 색으로 칠한다."""
    box = mask.getbbox() or (0, 0) + mask.size
    ramp = Image.linear_gradient("L").resize((mask.size[0], box[3] - box[1]))
    full = Image.new("L", mask.size, 0)
    full.paste(ramp, (0, box[1]))
    full.paste(255, (0, box[3], mask.size[0], mask.size[1]))
    a = Image.new("RGBA", mask.size, top + (255,))
    b = Image.new("RGBA", mask.size, bottom + (255,))
    out = Image.composite(b, a, full)
    out.putalpha(mask)
    return out


def sticker(mask, top, bottom, edge, gloss=None, edge_w=5, rim_w=5, shade=0.22, shadow=True):
    """모양(L) 하나를 기호 그림으로 만든다.

    mask     흰 모양
    top, bottom  그러데이션의 위아래 색
    edge     테두리 색(몸 색보다 짙게)
    gloss    광택을 그리는 함수(ImageDraw 를 받는다). 모양 안쪽에만 남는다
    """
    w, h = mask.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    line = grow(mask, edge_w * SS)
    rim = grow(line, rim_w * SS) if rim_w else None
    if shadow:
        base = rim if rim is not None else line
        sh = ImageChops.offset(base, 0, 4 * SS).filter(ImageFilter.GaussianBlur(4 * SS))
        out.alpha_composite(tint(sh, (20, 24, 60), 0.30))
    if rim is not None:
        out.alpha_composite(tint(rim, WHITE))
    out.alpha_composite(tint(line, edge))
    out.alpha_composite(gradient(mask, top, bottom))
    if shade:
        # 오른쪽 아래에 초승달 모양의 그늘
        moved = ImageChops.offset(mask, -5 * SS, -6 * SS)
        dark = ImageChops.subtract(mask, moved).filter(ImageFilter.GaussianBlur(3 * SS))
        out.alpha_composite(tint(ImageChops.multiply(dark, mask), edge, shade))
    if gloss is not None:
        g = canvas(w, h)
        gloss(ImageDraw.Draw(g))
        g = g.filter(ImageFilter.GaussianBlur(1.2 * SS))
        g = ImageChops.multiply(g, shrink_in(mask, 3 * SS))
        out.alpha_composite(tint(g, WHITE, 0.82))
    return out


def finish(im, size=None):
    w, h = im.size
    return im.resize(size or (w // SS, h // SS), Image.LANCZOS)


def rot_ellipse(draw_target, box, angle, fill=255):
    """기울어진 타원을 L 그림에 그린다."""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    pad = max(w, h)
    tile = Image.new("L", (pad * 2, pad * 2), 0)
    ImageDraw.Draw(tile).ellipse((pad - w / 2, pad - h / 2, pad + w / 2, pad + h / 2), fill=fill)
    tile = tile.rotate(angle, resample=Image.BICUBIC)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    draw_target.paste(255, (cx - pad, cy - pad), tile)


def stroke(d, pts, width):
    """끝이 둥근 굵은 선."""
    d.line(pts, fill=255, width=int(width), joint="curve")
    r = width / 2.0
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)


# ---------- 하트 ----------
def heart():
    m = canvas()
    pts = []
    for i in range(360):
        t = i / 360.0 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((B / 2 + x * B * 0.0215, B * 0.47 - y * B * 0.0215))
    ImageDraw.Draw(m).polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(SS))

    def gloss(d):
        pass

    im = sticker(m, (255, 150, 186), (255, 64, 120), (190, 24, 78), gloss)
    # 광택: 왼쪽 위의 기울어진 타원과 작은 점
    g = canvas()
    rot_ellipse(g, (B * 0.27, B * 0.26, B * 0.44, B * 0.36), 38)
    ImageDraw.Draw(g).ellipse((B * 0.245, B * 0.40, B * 0.285, B * 0.44), fill=255)
    g = ImageChops.multiply(g.filter(ImageFilter.GaussianBlur(SS)), shrink_in(m, 3 * SS))
    im.alpha_composite(tint(g, WHITE, 0.85))
    save(finish(im), "heart.png")


# ---------- 빠직(화남 표시) ----------
def vein():
    m = canvas()
    d = ImageDraw.Draw(m)
    c = B / 2.0
    gap = B * 0.335          # 가운데에서 호의 중심까지
    rad = B * 0.245
    wid = B * 0.085
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        ox, oy = c + sx * gap, c + sy * gap
        mid = math.atan2(-sy, -sx)          # 가운데를 보는 방향
        pts = []
        for i in range(25):
            a = mid - 0.92 + 1.84 * i / 24.0
            pts.append((ox + math.cos(a) * rad, oy + math.sin(a) * rad))
        stroke(d, pts, wid)
    m = m.filter(ImageFilter.GaussianBlur(SS * 0.8))

    def gloss(g):
        for sx, sy in ((-1, -1), (1, -1)):
            ox, oy = c + sx * gap, c + sy * gap
            mid = math.atan2(-sy, -sx)
            pts = []
            for i in range(9):
                a = mid - 0.5 + 0.55 * i / 8.0
                pts.append((ox + math.cos(a) * (rad + wid * 0.12), oy + math.sin(a) * (rad + wid * 0.12)))
            stroke(g, pts, wid * 0.22)

    im = sticker(m, (255, 112, 96), (232, 40, 62), (140, 16, 40), gloss, shade=0.18)
    save(finish(im), "vein.png")


# ---------- 땀방울 ----------
def sweat():
    m = canvas()
    d = ImageDraw.Draw(m)
    cx, cy, r = B * 0.5, B * 0.60, B * 0.215
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    pts = [(cx, B * 0.13)]
    for i in range(21):
        a = math.radians(205 + 130 * i / 20.0)      # 원의 위쪽 둘레
        pts.append((cx + math.cos(a) * r * 0.985, cy + math.sin(a) * r * 0.985))
    d.polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(SS * 1.5)).rotate(-14, resample=Image.BICUBIC, center=(cx, cy))

    def gloss(g):
        g.ellipse((B * 0.375, B * 0.50, B * 0.455, B * 0.62), fill=255)
        g.ellipse((B * 0.40, B * 0.655, B * 0.435, B * 0.69), fill=255)

    im = sticker(m, (214, 244, 255), (72, 172, 246), (38, 98, 176), gloss, shade=0.26)
    save(finish(im), "sweat.png")


# ---------- 느낌표 ----------
def exclaim():
    m = canvas()
    d = ImageDraw.Draw(m)
    cx = B * 0.5
    # 위가 넓고 아래가 좁은 쐐기
    d.polygon([(cx - B * 0.105, B * 0.15), (cx + B * 0.105, B * 0.15),
               (cx + B * 0.042, B * 0.60), (cx - B * 0.042, B * 0.60)], fill=255)
    d.ellipse((cx - B * 0.105, B * 0.10, cx + B * 0.105, B * 0.22), fill=255)
    d.ellipse((cx - B * 0.045, B * 0.565, cx + B * 0.045, B * 0.635), fill=255)
    r = B * 0.075
    d.ellipse((cx - r, B * 0.775 - r, cx + r, B * 0.775 + r), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(SS)).rotate(-9, resample=Image.BICUBIC, center=(cx, B * 0.5))

    def gloss(g):
        g.rounded_rectangle((B * 0.425, B * 0.16, B * 0.462, B * 0.40), radius=B * 0.02, fill=255)
        g.ellipse((B * 0.535, B * 0.735, B * 0.57, B * 0.77), fill=255)

    im = sticker(m, (255, 222, 84), (255, 102, 56), (142, 34, 24), gloss)
    save(finish(im), "exclaim.png")


# ---------- 물음표 ----------
def question():
    m = canvas()
    font = ImageFont.truetype(FONT, int(B * 0.86))
    d = ImageDraw.Draw(m)
    box = d.textbbox((0, 0), "?", font=font)
    d.text(((B - (box[2] - box[0])) / 2 - box[0], (B - (box[3] - box[1])) / 2 - box[1]), "?", font=font, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(SS * 1.6)).point(lambda v: 255 if v > 118 else 0)
    m = m.filter(ImageFilter.GaussianBlur(SS * 0.8)).rotate(-10, resample=Image.BICUBIC)

    def gloss(g):
        pts = []
        for i in range(13):
            a = math.radians(200 + 95 * i / 12.0)
            pts.append((B * 0.50 + math.cos(a) * B * 0.155, B * 0.345 + math.sin(a) * B * 0.155))
        stroke(g, pts, B * 0.024)

    im = sticker(m, (170, 226, 255), (92, 120, 255), (40, 44, 142), gloss)
    save(finish(im), "question.png")


# ---------- 반짝임 ----------
def star_mask(cx, cy, R, inner=0.0):
    m = canvas()
    pts = []
    n = 240
    for i in range(n):
        t = i / float(n) * 2 * math.pi
        # 끝이 뾰족하고 사이가 오목한 네 갈래 별. inner 가 클수록 가운데가 통통하다
        c, s = math.cos(t), math.sin(t)
        p = 3.0 - inner * 2.0
        x = math.copysign(abs(s) ** p, s)
        y = math.copysign(abs(c) ** p, c)
        pts.append((cx + x * R * 0.82, cy - y * R))
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def sparkle():
    m = ImageChops.lighter(star_mask(B * 0.44, B * 0.48, B * 0.36), star_mask(B * 0.78, B * 0.23, B * 0.17))
    m = ImageChops.lighter(m, star_mask(B * 0.77, B * 0.77, B * 0.12))
    m = m.filter(ImageFilter.GaussianBlur(SS * 0.9))

    def gloss(g):
        g.ellipse((B * 0.385, B * 0.415, B * 0.495, B * 0.525), fill=255)
        g.ellipse((B * 0.745, B * 0.215, B * 0.795, B * 0.265), fill=255)

    glow = grow(m, 12 * SS).filter(ImageFilter.GaussianBlur(7 * SS))
    im = Image.new("RGBA", (B, B), (0, 0, 0, 0))
    im.alpha_composite(tint(glow, (255, 240, 170), 0.55))
    im.alpha_composite(sticker(m, (255, 252, 214), (255, 204, 64), (226, 128, 20), gloss,
                               edge_w=4, rim_w=4, shade=0.12, shadow=False))
    save(finish(im), "sparkle.png")


# ---------- 김(뿌우) ----------
def steam():
    m = canvas()
    d = ImageDraw.Draw(m)
    for x, y, r in ((0.36, 0.44, 0.15), (0.52, 0.34, 0.18), (0.67, 0.45, 0.14), (0.50, 0.50, 0.16),
                    (0.40, 0.56, 0.10), (0.62, 0.56, 0.10)):
        d.ellipse((B * (x - r), B * (y - r), B * (x + r), B * (y + r)), fill=255)
    # 아래로 이어지는 작은 꼬리 구름
    d.ellipse((B * 0.33, B * 0.70, B * 0.45, B * 0.82), fill=255)
    d.ellipse((B * 0.27, B * 0.86, B * 0.33, B * 0.92), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(SS * 1.2))

    def gloss(g):
        g.ellipse((B * 0.40, B * 0.215, B * 0.52, B * 0.285), fill=255)

    im = sticker(m, (255, 255, 255), (255, 226, 232), (118, 106, 150), gloss, shade=0.30)
    # 안쪽의 꼬불꼬불한 선 두 줄
    ln = canvas()
    ld = ImageDraw.Draw(ln)
    for x0, y0 in ((0.40, 0.47), (0.56, 0.42)):
        pts = []
        for i in range(21):
            a = math.radians(160 + 250 * i / 20.0)
            pts.append((B * x0 + math.cos(a) * B * 0.045, B * y0 + math.sin(a) * B * 0.04))
        stroke(ld, pts, B * 0.018)
    im.alpha_composite(tint(ln.filter(ImageFilter.GaussianBlur(SS * 0.5)), (232, 150, 170), 0.9))
    save(finish(im), "steam.png")


# ---------- 말줄임표: 작은 말풍선 안의 점 세 개 ----------
def dots():
    m = canvas()
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((B * 0.15, B * 0.27, B * 0.85, B * 0.65), radius=B * 0.19, fill=255)
    d.polygon([(B * 0.27, B * 0.60), (B * 0.42, B * 0.60), (B * 0.24, B * 0.80)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(SS * 1.2))

    def gloss(g):
        g.rounded_rectangle((B * 0.24, B * 0.305, B * 0.52, B * 0.335), radius=B * 0.015, fill=255)

    im = sticker(m, (255, 255, 255), (232, 236, 252), (52, 58, 110), gloss, rim_w=0, shade=0.16)
    for i, x in enumerate((0.335, 0.5, 0.665)):
        dot = canvas()
        r = B * 0.052
        ImageDraw.Draw(dot).ellipse((B * x - r, B * 0.46 - r, B * x + r, B * 0.46 + r), fill=255)
        dot = dot.filter(ImageFilter.GaussianBlur(SS * 0.6))
        im.alpha_composite(gradient(dot, (96, 104, 168), (52, 58, 110)))
        hl = canvas()
        ImageDraw.Draw(hl).ellipse((B * x - r * 0.55, B * 0.46 - r * 0.6, B * x - r * 0.05, B * 0.46 - r * 0.1), fill=255)
        im.alpha_composite(tint(hl.filter(ImageFilter.GaussianBlur(SS * 0.5)), WHITE, 0.7))
    save(finish(im), "dots.png")


# ---------- 음표 ----------
def note():
    m = canvas()
    d = ImageDraw.Draw(m)
    rot_ellipse(m, (B * 0.24, B * 0.60, B * 0.50, B * 0.80), 22)
    d.rounded_rectangle((B * 0.435, B * 0.20, B * 0.495, B * 0.70), radius=B * 0.02, fill=255)
    # 깃발
    pts = [(B * 0.465, B * 0.17)]
    for i in range(17):
        t = i / 16.0
        pts.append((B * (0.48 + 0.25 * t), B * (0.19 + 0.30 * t ** 1.5)))
    for i in range(17):
        t = 1 - i / 16.0
        pts.append((B * (0.48 + 0.19 * t), B * (0.32 + 0.20 * t ** 1.4)))
    pts.append((B * 0.465, B * 0.33))
    d.polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(SS * 1.1))

    def gloss(g):
        rot_ellipse(g._image, (B * 0.285, B * 0.635, B * 0.375, B * 0.685), 22)
        g.rounded_rectangle((B * 0.447, B * 0.24, B * 0.462, B * 0.50), radius=B * 0.006, fill=255)

    im = sticker(m, (150, 240, 214), (38, 184, 168), (14, 96, 104), gloss)
    save(finish(im), "note.png")


# ---------- 우울한 세로줄 ----------
def gloom():
    w, h = 256 * SS, 192 * SS
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # 뒤에 깔리는 어스름
    haze = canvas(w, h)
    ImageDraw.Draw(haze).ellipse((w * 0.08, -h * 0.35, w * 0.92, h * 0.70), fill=255)
    haze = haze.filter(ImageFilter.GaussianBlur(22 * SS))
    im.alpha_composite(tint(haze, (58, 46, 118), 0.62))
    # 아래로 갈수록 옅어지는 세로줄. 길이가 들쭉날쭉하다
    fade = Image.linear_gradient("L").resize((w, h)).point(lambda v: 255 - int(v * 0.62))
    for layer_color, extra, alpha in (((240, 236, 255), 3.0, 0.85), ((44, 32, 108), 0.0, 1.0)):
        ln = canvas(w, h)
        d = ImageDraw.Draw(ln)
        for i, (x, length) in enumerate(((0.16, 0.50), (0.27, 0.74), (0.38, 0.60), (0.50, 0.86),
                                         (0.62, 0.66), (0.73, 0.78), (0.84, 0.52))):
            pts = []
            for k in range(25):
                t = k / 24.0
                pts.append((w * x + math.sin(t * 5.0 + i) * w * 0.006, h * (0.06 + length * t)))
            stroke(d, pts, (7.0 + extra) * SS)
        ln = ImageChops.multiply(ln.filter(ImageFilter.GaussianBlur(SS * 0.7)), fade)
        im.alpha_composite(tint(ln, layer_color, alpha))
    save(finish(im), "gloom.png")


# ---------- 장소 제목 카드의 띠: 양 끝이 옅어지는 어두운 띠와 위아래의 가는 장식선 ----------
def title_band():
    w, h = 720 * SS, 96 * SS
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # 가운데가 진하고 양 끝으로 사라지는 가로 띠
    half = Image.linear_gradient("L").rotate(90, expand=True).resize((w // 2, h))     # 왼쪽 0 → 오른쪽 255
    side = Image.new("L", (w, h), 0)
    side.paste(half, (0, 0))
    side.paste(half.transpose(Image.FLIP_LEFT_RIGHT), (w // 2, 0))
    side = side.point(lambda v: min(255, int(v * 1.5)))
    band = canvas(w, h)
    ImageDraw.Draw(band).rectangle((0, h * 0.17, w, h * 0.83), fill=255)
    band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(3 * SS)), side)
    im.alpha_composite(tint(band, (22, 28, 70), 0.62))
    # 가는 선 두 줄과 가운데의 작은 마름모
    ln = canvas(w, h)
    d = ImageDraw.Draw(ln)
    for y in (h * 0.17, h * 0.83):
        d.rectangle((w * 0.06, y - 0.75 * SS, w * 0.94, y + 0.75 * SS), fill=255)
        r = 5 * SS
        d.rectangle((w / 2 - r * 2.4, y - 2 * SS, w / 2 + r * 2.4, y + 2 * SS), fill=0)
        d.polygon([(w / 2 - r, y), (w / 2, y - r), (w / 2 + r, y), (w / 2, y + r)], fill=255)
        for sx in (-1, 1):
            cx = w / 2 + sx * r * 2.1
            d.ellipse((cx - 1.6 * SS, y - 1.6 * SS, cx + 1.6 * SS, y + 1.6 * SS), fill=255)
    ln = ImageChops.multiply(ln.filter(ImageFilter.GaussianBlur(SS * 0.4)), side)
    im.alpha_composite(tint(ln, (255, 236, 244), 0.95))
    save(finish(im), "title_band.png")


if __name__ == "__main__":
    heart()
    vein()
    sweat()
    exclaim()
    question()
    sparkle()
    steam()
    dots()
    note()
    gloom()
    title_band()

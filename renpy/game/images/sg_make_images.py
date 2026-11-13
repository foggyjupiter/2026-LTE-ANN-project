"""화면 부품(ui/)과 자리표시 그림(placeholder/)을 만든다. 개발용이다.

    python3 renpy/game/images/sg_make_images.py

Pillow가 필요하다. 만든 PNG와 JPG는 깃에 올려 두므로 게임을 켤 때는 이 스크립트가 필요 없다.

- ui/                       대사창, 단추, 말풍선에 쓰는 흰색 부품. 색은 Ren'Py에서 입힌다
- placeholder/sprites/<캐릭터>/<표정>.png   진짜 스탠딩이 없을 때 쓰는 그림 (768x1152, 투명 배경)
- placeholder/bg/<키>.jpg   진짜 배경이 없을 때 쓰는 그림 (1280x720)

진짜 그림은 sprites/<캐릭터>/<표정>.png 와 bg/<키>.jpg 에 넣는다. 있으면 그쪽을 쓴다.
"""
import math
import pathlib

from PIL import Image, ImageDraw, ImageFilter

HERE = pathlib.Path(__file__).resolve().parent
S = 2  # 이 배율로 크게 그린 뒤 줄여서 가장자리를 매끄럽게 한다

WHITE = (255, 255, 255, 255)
SKIN = (255, 226, 205, 255)
SKIN_SHADE = (243, 200, 178, 255)
INK = (42, 38, 60, 255)
BLUSH = (255, 120, 130, 150)
SHIRT = (250, 250, 252, 255)
RIBBON = (220, 60, 80, 255)
NAVY = (43, 58, 122, 255)

FACES = ("neutral", "smile", "blush", "pout", "shock", "dark")


def rgba(hex_color, alpha=255):
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))


class Canvas:
    """S배로 그리고 마지막에 줄이는 그림판. 좌표는 줄인 뒤의 값으로 적는다."""

    def __init__(self, width, height, fill=(0, 0, 0, 0)):
        self.size = (width, height)
        self.image = Image.new("RGBA", (width * S, height * S), fill)

    def _layer(self):
        layer = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
        return layer, ImageDraw.Draw(layer)

    def _put(self, layer):
        self.image = Image.alpha_composite(self.image, layer)

    @staticmethod
    def _box(box):
        return [round(v * S) for v in box]

    def ellipse(self, cx, cy, rx, ry, fill, outline=None, width=0):
        layer, d = self._layer()
        d.ellipse(self._box((cx - rx, cy - ry, cx + rx, cy + ry)), fill=fill,
                  outline=outline, width=round(width * S))
        self._put(layer)

    def rect(self, x0, y0, x1, y1, fill, radius=0, outline=None, width=0):
        layer, d = self._layer()
        d.rounded_rectangle(self._box((x0, y0, x1, y1)), radius=round(radius * S), fill=fill,
                            outline=outline, width=round(width * S))
        self._put(layer)

    def polygon(self, points, fill):
        layer, d = self._layer()
        d.polygon([(round(x * S), round(y * S)) for x, y in points], fill=fill)
        self._put(layer)

    def line(self, points, fill, width):
        layer, d = self._layer()
        d.line([(round(x * S), round(y * S)) for x, y in points], fill=fill,
               width=round(width * S), joint="curve")
        r = width / 2
        for x, y in (points[0], points[-1]):  # 끝을 둥글게
            d.ellipse(self._box((x - r, y - r, x + r, y + r)), fill=fill)
        self._put(layer)

    def arc(self, cx, cy, rx, ry, start, end, fill, width):
        layer, d = self._layer()
        d.arc(self._box((cx - rx, cy - ry, cx + rx, cy + ry)), start, end, fill=fill,
              width=round(width * S))
        self._put(layer)

    def chord(self, cx, cy, rx, ry, start, end, fill):
        layer, d = self._layer()
        d.chord(self._box((cx - rx, cy - ry, cx + rx, cy + ry)), start, end, fill=fill)
        self._put(layer)

    def gradient(self, x0, y0, x1, y1, top, bottom):
        """위에서 아래로 번지는 색."""
        height = max(1, round((y1 - y0) * S))
        strip = Image.new("RGBA", (1, height))
        for y in range(height):
            strip.putpixel((0, y), mix(top, bottom, y / max(1, height - 1)))
        strip = strip.resize((round((x1 - x0) * S), height))
        layer = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
        layer.paste(strip, (round(x0 * S), round(y0 * S)))
        self._put(layer)

    def star(self, cx, cy, r, fill, points=4, inner=0.4):
        pts = []
        for i in range(points * 2):
            radius = r if i % 2 == 0 else r * inner
            angle = math.pi * i / points - math.pi / 2
            pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        self.polygon(pts, fill)

    def blur(self, radius):
        self.image = self.image.filter(ImageFilter.GaussianBlur(radius * S))

    def result(self):
        return self.image.resize(self.size, Image.LANCZOS)


def save(image, path, **options):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, **options)
    print(path.relative_to(HERE))


# ---------------------------------------------------------------- 화면 부품

def ui_round(name, radius, *, line=0, size=None):
    """모서리가 둥근 흰 네모. Ren'Py의 Frame으로 늘여 쓴다. line을 주면 테두리만 그린다."""
    side = size or radius * 2 + 8
    c = Canvas(side, side)
    if line:
        c.rect(0, 0, side, side, None, radius=radius, outline=WHITE, width=line)
    else:
        c.rect(0, 0, side, side, WHITE, radius=radius)
    save(c.result(), HERE / "ui" / f"{name}.png")


def ui_shadow(name, radius, spread):
    """둥근 네모 밑에 까는 그림자. 가장자리 spread 픽셀이 번진 부분이다."""
    side = radius * 2 + spread * 2 + 8
    c = Canvas(side, side)
    c.rect(spread, spread, side - spread, side - spread, (10, 14, 40, 150), radius=radius)
    c.blur(spread / 2.4)
    save(c.result(), HERE / "ui" / f"{name}.png")


def ui_heart():
    c = Canvas(64, 64)
    c.ellipse(21, 23, 15, 15, WHITE)
    c.ellipse(43, 23, 15, 15, WHITE)
    c.polygon([(7.5, 30), (56.5, 30), (32, 59)], WHITE)
    save(c.result(), HERE / "ui" / "heart.png")


def ui_dot():
    c = Canvas(64, 64)
    c.ellipse(32, 32, 30, 30, WHITE)
    save(c.result(), HERE / "ui" / "dot.png")


def ui_ctc():
    c = Canvas(28, 22)
    c.polygon([(2, 3), (26, 3), (14, 20)], WHITE)
    save(c.result(), HERE / "ui" / "ctc.png")


def ui_shade(name, top_alpha, bottom_alpha):
    """위아래로 번지는 어두운 띠. 글자 뒤에 깔아서 읽기 쉽게 한다."""
    c = Canvas(8, 256)
    c.gradient(0, 0, 8, 256, (12, 14, 34, top_alpha), (12, 14, 34, bottom_alpha))
    save(c.result(), HERE / "ui" / f"{name}.png")


def ui_bubble_tail():
    """생각 풍선에서 머리 쪽으로 이어지는 동그라미 두 개."""
    c = Canvas(64, 48)
    c.ellipse(20, 18, 14, 14, WHITE)
    c.ellipse(50, 38, 8, 8, WHITE)
    save(c.result(), HERE / "ui" / "bubble_tail.png")


def make_ui():
    for radius in (8, 14, 20, 28):
        ui_round(f"r{radius}", radius)
    ui_round("r14_line", 14, line=2)
    ui_round("r20_line", 20, line=2)
    ui_round("r20_line3", 20, line=3.5)
    ui_shadow("shadow20", 20, 18)
    ui_heart()
    ui_dot()
    ui_ctc()
    ui_shade("shade_bottom", 0, 185)
    ui_shade("shade_top", 150, 0)
    ui_bubble_tail()


# ---------------------------------------------------------------- 자리표시 스탠딩

CX, CY = 384, 360          # 얼굴 한가운데
EYE_Y, EYE_DX = 378, 62
MOUTH_Y = 458

CHARACTERS = {
    "giulhee": {"hair": "#F58A2B", "hair2": "#E0382B", "eye": "#B8660F", "top": "#D93A3A"},
    "oeun": {"hair": "#232F66", "hair2": "#1A2350", "eye": "#39508F", "top": "#2B3A7A"},
    "anna": {"hair": "#B7DB63", "hair2": "#9CC64A", "eye": "#6E8F2F", "top": "#F2E3BD"},
    "relu": {"hair": "#F8D030", "hair2": "#EDB81C", "eye": "#C98A0A", "top": "#F4B400"},
    "haru": {"hair": "#8A4FD3", "hair2": "#6D38B5", "eye": "#6D38B5", "top": "#2B3A7A"},
    "boxhyun": {"hair": "#1E1E22", "hair2": "#111114", "eye": "#7B8590", "top": "#26262B"},
}


def back_hair(c, who, hair, hair2):
    """얼굴 뒤에 깔리는 머리. 캐릭터마다 실루엣이 다르다."""
    if who == "giulhee":      # 끝으로 갈수록 부푸는 높은 포니테일
        for i, (x, y, r) in enumerate([(520, 150, 62), (596, 190, 78), (652, 270, 92),
                                       (676, 380, 98), (660, 500, 86), (628, 600, 60)]):
            c.ellipse(x, y, r, r, mix(hair, hair2, i / 5))
        c.ellipse(CX, 330, 186, 200, hair)
    elif who == "oeun":       # 단정한 양 갈래 땋은 머리
        c.ellipse(CX, 330, 182, 196, hair)
        for side in (-1, 1):
            for i in range(9):
                x = CX + side * (176 + (10 if i % 2 else -6))
                c.ellipse(x, 470 + i * 52, 40, 34, hair if i % 2 else hair2)
            c.rect(CX + side * 176 - 30, 915, CX + side * 176 + 30, 937, rgba("#F5C518"), radius=8)
            c.ellipse(CX + side * 176, 962, 24, 30, hair)
    elif who == "anna":       # 잔머리가 삐친 짧은 단발
        c.ellipse(CX, 345, 200, 205, hair)
        c.rect(190, 340, 578, 560, hair, radius=70)
        for x0, y0, x1, y1 in [(205, 210, 150, 150), (560, 200, 625, 150), (190, 500, 130, 540),
                               (580, 500, 640, 545), (384, 150, 400, 95)]:
            c.line([(x0, y0), (x1, y1)], hair2, 16)
    elif who == "relu":       # 옆으로 묶은 포니테일
        for i, (x, y, r) in enumerate([(196, 250, 60), (140, 300, 74), (104, 392, 78),
                                       (104, 500, 66), (128, 590, 46)]):
            c.ellipse(x, y, r, r, mix(hair, hair2, i / 4))
        c.ellipse(CX, 330, 184, 198, hair)
        c.ellipse(214, 262, 20, 20, WHITE)
    elif who == "haru":       # 길고 굽이치는 머리
        c.ellipse(CX, 330, 190, 200, hair)
        c.rect(200, 330, 568, 900, hair, radius=40)
        for side in (-1, 1):
            for i in range(10):
                x = CX + side * (196 + (26 if i % 2 else 0))
                c.ellipse(x, 380 + i * 66, 62, 56, hair if i % 2 else hair2)
    else:                     # boxhyun: 검은 단발
        c.ellipse(CX, 340, 192, 200, hair)
        c.rect(196, 340, 572, 590, hair, radius=60)


def clothes(c, who, top):
    """목과 윗옷."""
    c.rect(338, 490, 430, 640, SKIN_SHADE, radius=30)
    if who == "relu":         # 후드
        c.ellipse(CX, 640, 230, 110, mix(top, INK, 0.12))
    if who == "boxhyun":
        c.ellipse(CX, 640, 226, 104, mix(top, WHITE, 0.08))
    width = 300 if who == "haru" else 280   # 하루는 재킷을 어깨에 걸쳤다
    c.rect(CX - width, 610, CX + width, 1300, top, radius=150)
    if who in ("giulhee", "oeun", "haru", "anna"):   # 셔츠 깃과 리본
        c.polygon([(CX - 86, 612), (CX + 86, 612), (CX, 800)], SHIRT)
        c.polygon([(CX - 30, 690), (CX + 30, 690), (CX + 18, 722), (CX - 18, 722)], RIBBON)
        c.polygon([(CX - 64, 676), (CX - 12, 700), (CX - 64, 736)], RIBBON)
        c.polygon([(CX + 64, 676), (CX + 12, 700), (CX + 64, 736)], RIBBON)
    c.rect(CX - 46, 560, CX + 46, 640, SKIN_SHADE, radius=30)
    # 교표: 선으로 이어진 동그라미 세 개
    if who in ("oeun", "haru"):
        ex, ey = 520, 800
        c.line([(ex - 18, ey + 12), (ex, ey - 16), (ex + 18, ey + 12), (ex - 18, ey + 12)],
               rgba("#F5C518"), 3)
        for dx, dy in ((-18, 12), (0, -16), (18, 12)):
            c.ellipse(ex + dx, ey + dy, 8, 8, rgba("#F5C518"))
    if who == "giulhee":      # 트레이닝 재킷의 흰 줄
        for side in (-1, 1):
            c.line([(CX + side * 236, 700), (CX + side * 262, 1152)], WHITE, 14)
        c.line([(CX, 800), (CX, 1152)], mix(top, INK, 0.25), 6)
    elif who == "oeun":       # 끝까지 채운 단추, 수첩과 붙임쪽지
        for y in (850, 940, 1030):
            c.ellipse(CX, y, 11, 11, rgba("#C9CEDF"))
        c.rect(520, 930, 690, 1152, rgba("#F4F1E8"), radius=10)
        for i, color in enumerate(("#F5C518", "#F29A2E", "#F5C518")):
            c.rect(676, 950 + i * 50, 716, 980 + i * 50, rgba(color), radius=4)
    elif who == "anna":       # 단추 하나가 빠진 카디건
        c.line([(CX, 800), (CX, 1152)], mix(top, INK, 0.18), 5)
        for y in (860, 1040):
            c.ellipse(CX + 26, y, 12, 12, rgba("#B58A5A"))
        c.ellipse(CX + 26, 950, 12, 12, None, outline=rgba("#B58A5A"), width=3)
    elif who == "relu":       # 집업 후드
        c.line([(CX, 650), (CX, 1152)], WHITE, 8)
        for side in (-1, 1):
            c.line([(CX + side * 40, 660), (CX + side * 48, 800)], WHITE, 7)
            c.ellipse(CX + side * 48, 806, 9, 9, WHITE)
    elif who == "haru":       # 별 하나가 그려진 완장, 두꺼운 책
        c.rect(596, 800, 690, 880, WHITE, radius=8)
        c.star(643, 840, 26, rgba("#F5C518"), points=5, inner=0.45)
        c.rect(96, 930, 290, 1152, rgba("#5B2F9A"), radius=10)
        c.rect(112, 950, 274, 962, rgba("#F5C518"), radius=4)
    else:                     # boxhyun: 청록 끈, 목에 건 헤드폰
        teal = rgba("#22B8B0")
        for side in (-1, 1):
            c.line([(CX + side * 44, 650), (CX + side * 52, 830)], teal, 8)
            c.ellipse(CX + side * 52, 838, 10, 10, teal)
        c.arc(CX, 600, 150, 96, 20, 160, rgba("#3A3A42"), 22)
        for side in (-1, 1):
            c.ellipse(CX + side * 142, 624, 34, 46, rgba("#3A3A42"))
            c.ellipse(CX + side * 142, 624, 16, 26, teal)


def front_hair(c, who, hair, hair2):
    """얼굴 위로 내려오는 앞머리와 장식."""
    c.chord(CX, 318, 170, 150, 180, 360, hair)                    # 이마를 덮는 윗머리
    if who == "boxhyun":      # 한쪽 눈을 덮는 긴 앞머리
        c.polygon([(214, 300), (400, 250), (372, 330), (348, 432), (300, 452), (226, 420)], hair)
        c.polygon([(400, 262), (556, 300), (548, 352), (470, 330)], hair)
        return
    fringe = {
        "giulhee": [(226, 300), (300, 372), (330, 300), (384, 352), (430, 300), (486, 364), (544, 300)],
        "oeun": [(222, 300), (222, 356), (300, 340), (384, 348), (468, 340), (546, 356), (546, 300)],
        "anna": [(220, 300), (262, 384), (318, 318), (372, 366), (428, 320), (500, 380), (548, 300)],
        "relu": [(224, 300), (286, 360), (350, 316), (420, 362), (474, 318), (520, 356), (546, 300)],
        "haru": [(222, 300), (250, 390), (330, 320), (384, 300), (440, 320), (518, 390), (546, 300)],
    }[who]
    c.polygon(fringe, hair)
    if who == "giulhee":      # 치솟는 꺾은선 그래프 머리핀
        c.line([(232, 300), (254, 286), (270, 292), (296, 250)], rgba("#FFE14D"), 8)
    elif who == "anna":       # 한쪽에만 꽂은 머리핀
        c.rect(476, 300, 540, 318, rgba("#FF9EB5"), radius=8)
    elif who == "relu":       # 볼에 붙인 반창고
        c.rect(452, 420, 508, 446, rgba("#F3D2A8"), radius=8)
        c.line([(472, 426), (472, 440)], rgba("#D9B080"), 3)
        c.line([(488, 426), (488, 440)], rgba("#D9B080"), 3)


def draw_face(c, who, face, eye_color):
    """표정. 눈, 눈썹, 입, 홍조, 그늘."""
    sides = (1,) if who == "boxhyun" else (-1, 1)   # 하이쿠는 한쪽 눈이 머리에 가려 있다
    dull = face == "dark"
    look = 10 if face in ("blush", "pout") else 0   # 눈길을 옆으로 돌린다

    if face == "dark":        # 얼굴 위쪽에 드리운 그늘
        c.chord(CX, CY, 148, 170, 180, 360, (40, 36, 70, 120))

    for side in sides:
        x = CX + side * EYE_DX
        if face == "smile" and who != "boxhyun":
            c.arc(x, EYE_Y + 8, 24, 22, 200, 340, INK, 7)          # 감은 눈
            continue
        if who == "anna" and face in ("neutral", "blush", "pout"):
            c.chord(x + look, EYE_Y, 20, 20, 0, 180, INK)          # 졸린 반쯤 감긴 눈
            c.line([(x - 22 + look, EYE_Y), (x + 22 + look, EYE_Y)], INK, 6)
            continue
        if face == "shock":
            big = 1.15 if who == "boxhyun" else 1.5
            c.ellipse(x, EYE_Y, 20 * big, 24 * big, WHITE, outline=INK, width=5)
            c.ellipse(x, EYE_Y, 8, 9, INK)
            continue
        ry = 16 if (who == "boxhyun" or face == "pout") else 24
        c.ellipse(x + look, EYE_Y, 18, ry, eye_color)
        c.ellipse(x + look, EYE_Y + 2, 10, ry * 0.6, INK)
        if dull:
            c.ellipse(x + look, EYE_Y, 18, ry, (60, 60, 80, 170))  # 빛이 없는 눈
        elif who == "haru":
            c.star(x + look + 2, EYE_Y - 2, 12, rgba("#FFE14D"))   # 별 모양 반짝임
        else:
            c.ellipse(x + look + 6, EYE_Y - ry * 0.4, 5, 5, WHITE)

    # 눈썹
    brow_y = EYE_Y - 48
    for side in sides:
        x = CX + side * EYE_DX
        if face == "pout":
            c.line([(x - side * 26, brow_y - 8), (x + side * 22, brow_y + 12)], INK, 6)
        elif face == "shock":
            c.line([(x - 22, brow_y - 22), (x + 22, brow_y - 22)], INK, 6)
        elif who == "giulhee" or (who == "haru" and face in ("neutral", "smile")):
            c.line([(x - side * 24, brow_y + 10), (x + side * 24, brow_y - 8)], INK, 6)  # 치켜든 눈썹
        elif face == "blush":
            c.line([(x - side * 24, brow_y - 6), (x + side * 22, brow_y + 6)], INK, 5)
        else:
            c.line([(x - 22, brow_y), (x + 22, brow_y)], INK, 5)

    if who == "oeun":         # 동그란 안경
        for side in (-1, 1):
            c.ellipse(CX + side * EYE_DX, EYE_Y, 46, 46, (255, 255, 255, 40), outline=INK, width=5)
        c.line([(CX - 16, EYE_Y), (CX + 16, EYE_Y)], INK, 5)

    # 홍조
    if face in ("blush", "pout") or (who == "giulhee" and face == "smile"):
        alpha = 90 if (who == "boxhyun" or face == "pout") else 150
        size = 30 if face == "blush" else 26
        for side in (-1, 1):
            c.ellipse(CX + side * 98, 432, size, size * 0.55, BLUSH[:3] + (alpha,))

    # 입
    if who == "boxhyun":
        if face == "smile":
            c.arc(CX, MOUTH_Y - 12, 22, 14, 30, 150, INK, 5)
        elif face == "shock":
            c.ellipse(CX, MOUTH_Y, 8, 8, INK)
        else:
            c.line([(CX - 16, MOUTH_Y), (CX + 16, MOUTH_Y)], INK, 5)
    elif face == "smile" or (who == "relu" and face in ("neutral", "dark")):
        c.chord(CX, MOUTH_Y - 16, 36, 34, 0, 180, rgba("#B8324A"))   # 활짝 웃는 입
    elif face == "neutral":
        if who == "haru":
            c.line([(CX - 20, MOUTH_Y + 2), (CX + 6, MOUTH_Y + 2), (CX + 26, MOUTH_Y - 10)], INK, 5)
        else:
            c.arc(CX, MOUTH_Y - 14, 22, 16, 30, 150, INK, 5)
    elif face == "blush":
        c.line([(CX - 18, MOUTH_Y), (CX - 6, MOUTH_Y - 6), (CX + 6, MOUTH_Y), (CX + 18, MOUTH_Y - 6)],
               INK, 5)
    elif face == "pout":
        c.arc(CX, MOUTH_Y + 14, 18, 14, 210, 330, INK, 6)
    elif face == "shock":
        c.ellipse(CX, MOUTH_Y + 4, 16, 22, rgba("#B8324A"))
    else:                     # dark: 가늘게 굳은 웃음
        c.arc(CX, MOUTH_Y - 20, 34, 22, 30, 150, INK, 5)

    if who == "relu" and face == "dark":   # 관자놀이의 땀방울
        c.ellipse(520, 318, 9, 13, rgba("#9AD4F5"))


def make_sprite(who, face):
    spec = CHARACTERS[who]
    hair, hair2, top = rgba(spec["hair"]), rgba(spec["hair2"]), rgba(spec["top"])
    c = Canvas(768, 1152)
    back_hair(c, who, hair, hair2)
    clothes(c, who, top)
    c.ellipse(CX, CY, 148, 170, SKIN)
    draw_face(c, who, face, rgba(spec["eye"]))
    front_hair(c, who, hair, hair2)
    save(c.result(), HERE / "placeholder" / "sprites" / who / f"{face}.png", optimize=True)


# ---------------------------------------------------------------- 자리표시 배경

def sky(c, top="#8CC8F5", bottom="#DDF0FF"):
    c.gradient(0, 0, 1280, 720, rgba(top), rgba(bottom))
    for x, y, r in [(180, 120, 60), (250, 110, 80), (330, 130, 55), (900, 90, 70), (980, 100, 50),
                    (640, 190, 45), (700, 185, 60)]:
        c.ellipse(x, y, r * 1.5, r * 0.55, (255, 255, 255, 215))


def trees(c, y, xs, scale=1.0):
    for x in xs:
        c.rect(x - 9 * scale, y - 70 * scale, x + 9 * scale, y, rgba("#8B6B4A"), radius=4)
        c.ellipse(x, y - 110 * scale, 62 * scale, 70 * scale, rgba("#6FB36A"))
        c.ellipse(x - 30 * scale, y - 80 * scale, 44 * scale, 44 * scale, rgba("#5FA65B"))


def bg_store_line(c):
    c.gradient(0, 0, 1280, 720, rgba("#FFF1D6"), rgba("#F9DDB0"))
    c.rect(0, 470, 1280, 720, rgba("#D9B98A"))
    for i in range(4):                                   # 진열장
        x = 90 + i * 290
        c.rect(x, 110, x + 240, 420, rgba("#B98555"), radius=10)
        for row in range(3):
            c.rect(x + 14, 128 + row * 96, x + 226, 206 + row * 96, rgba("#FFF8EA"), radius=6)
            for k in range(5):
                color = ("#F29A2E", "#E8552D", "#8CC8F5", "#A4D65E", "#F5C518")[(k + row + i) % 5]
                c.rect(x + 24 + k * 40, 150 + row * 96, x + 54 + k * 40, 204 + row * 96,
                       rgba(color), radius=5)
    c.rect(0, 420, 1280, 520, rgba("#8E5E3B"))           # 계산대
    c.rect(0, 420, 1280, 440, rgba("#A9764D"))
    c.line([(200, 620), (1080, 620)], rgba("#F5C518"), 10)   # 줄 서는 선


def bg_library(c):
    c.gradient(0, 0, 1280, 720, rgba("#F6EEDC"), rgba("#EAD9B8"))
    c.rect(0, 520, 1280, 720, rgba("#B58E63"))
    for i in range(3):                                   # 큰 창
        x = 470 + i * 150
        c.rect(x, 90, x + 120, 420, rgba("#CFEBFF"), radius=8)
        c.polygon([(x, 420), (x + 120, 420), (x + 40, 720), (x - 160, 720)], (255, 255, 255, 60))
    for x0 in (30, 880):                                 # 책장
        c.rect(x0, 60, x0 + 370, 540, rgba("#8B5E3C"), radius=10)
        for row in range(4):
            y = 84 + row * 112
            c.rect(x0 + 16, y, x0 + 354, y + 94, rgba("#6E4729"), radius=4)
            for k in range(14):
                color = ("#C4553D", "#3F6FA8", "#E3B23C", "#5E9E6B", "#8A4FD3", "#F4F1E8")[(k * 5 + row) % 6]
                tall = 60 + (k * 7 + row * 5) % 28
                c.rect(x0 + 22 + k * 23.5, y + 92 - tall, x0 + 42 + k * 23.5, y + 92, rgba(color), radius=3)
    c.rect(380, 560, 900, 600, rgba("#8B5E3C"), radius=8)    # 책상
    c.rect(410, 600, 440, 720, rgba("#6E4729"))
    c.rect(840, 600, 870, 720, rgba("#6E4729"))


def bg_rooftop(c):
    sky(c)
    for i, (x, w, h) in enumerate([(40, 90, 110), (150, 70, 150), (240, 120, 90), (400, 80, 130),
                                   (520, 110, 100), (690, 90, 160), (800, 130, 110), (980, 80, 140),
                                   (1080, 140, 100)]):
        c.rect(x, 470 - h, x + w, 470, rgba(("#B9C7DC", "#A9BAD3", "#C6D2E3")[i % 3]))
    c.rect(0, 470, 1280, 720, rgba("#C9CDD3"))            # 바닥
    c.rect(0, 470, 1280, 486, rgba("#AEB3BB"))
    for x in range(40, 1281, 150):                        # 난간 기둥과 가로대
        c.rect(x - 6, 250, x + 6, 480, rgba("#7F8A99"), radius=3)
    for y in (258, 330, 402):
        c.line([(0, y), (1280, y)], rgba("#7F8A99"), 6)


def bg_corridor(c):
    c.gradient(0, 0, 1280, 720, rgba("#F3F1EA"), rgba("#E6E2D6"))
    c.polygon([(0, 720), (1280, 720), (860, 470), (420, 470)], rgba("#D8C7A6"))   # 바닥
    c.polygon([(520, 720), (760, 720), (680, 470), (600, 470)], (255, 255, 255, 70))
    c.rect(420, 150, 860, 470, rgba("#EDE9DE"))
    c.rect(560, 230, 720, 470, rgba("#C9B58C"), radius=4)
    for i in range(3):                                    # 왼쪽 창
        x0, x1 = 30 + i * 135, 130 + i * 125
        top0, top1 = 120 + i * 40, 150 + i * 38
        c.polygon([(x0, top0), (x1, top1), (x1, 440 - i * 16), (x0, 470 - i * 14)], rgba("#CFEBFF"))
    for i in range(2):                                    # 오른쪽 교실 문
        x0, x1 = 1250 - i * 190, 1100 - i * 150
        c.polygon([(x0, 150 + i * 46), (x1, 190 + i * 40), (x1, 560 - i * 50), (x0, 640 - i * 66)],
                  rgba("#B9A27A"))
        c.polygon([(x0 - 36, 230 + i * 40), (x1 + 30, 250 + i * 36), (x1 + 30, 340 + i * 24),
                   (x0 - 36, 330 + i * 30)], rgba("#DDEFFB"))


def bg_cafeteria(c):
    c.gradient(0, 0, 1280, 720, rgba("#F4F7F2"), rgba("#E3ECDF"))
    c.rect(0, 430, 1280, 720, rgba("#D6DCC9"))
    c.rect(60, 190, 1220, 330, rgba("#C9D2D6"), radius=8)     # 배식대
    c.rect(60, 190, 1220, 214, rgba("#AEB9BF"), radius=8)
    for k in range(7):
        c.rect(110 + k * 155, 230, 230 + k * 155, 300, rgba("#EEF2F4"), radius=8)
    c.rect(1000, 130, 1180, 190, rgba("#E8552D"), radius=6)   # 쌓인 식판
    for row, (y, s) in enumerate([(470, 0.8), (590, 1.0)]):   # 긴 식탁과 동그란 의자
        c.rect(120 - row * 60, y, 1160 + row * 60, y + 34 * s, rgba("#F2E6CF"), radius=10)
        for k in range(8):
            x = 190 - row * 50 + k * (128 + row * 16)
            c.ellipse(x, y + 78 * s, 34 * s, 14 * s, rgba("#F29A2E"))


def bg_science_lab(c):
    c.gradient(0, 0, 1280, 720, rgba("#EAF0F2"), rgba("#D5E0E4"))
    c.rect(0, 500, 1280, 720, rgba("#B9C4C9"))
    c.rect(300, 80, 980, 330, rgba("#2F5D50"), radius=8)       # 칠판
    c.rect(300, 322, 980, 340, rgba("#9A7B57"), radius=4)
    for x in (70, 1090):                                       # 창
        c.rect(x, 110, x + 130, 360, rgba("#CFEBFF"), radius=8)
    for row, (y, s) in enumerate([(430, 0.85), (560, 1.0)]):   # 검은 실험대
        c.rect(90 - row * 50, y, 1190 + row * 50, y + 60 * s, rgba("#2B2F36"), radius=8)
        for k in range(5):                                     # 플라스크와 비커
            x = 200 + k * 220 - row * 30
            color = ("#7FD1E8", "#F29A2E", "#A4D65E", "#F5C518", "#C89BF0")[k]
            c.polygon([(x - 10, y - 70 * s), (x + 10, y - 70 * s), (x + 34 * s, y), (x - 34 * s, y)],
                      (255, 255, 255, 200))
            c.polygon([(x - 18 * s, y - 30 * s), (x + 18 * s, y - 30 * s), (x + 34 * s, y),
                       (x - 34 * s, y)], rgba(color))
            c.rect(x + 60, y - 50 * s, x + 100, y, rgba(color, 190), radius=4)


def bg_field_bench(c):
    sky(c, "#FFC98A", "#FFF1D6")                               # 늦은 오후
    c.rect(0, 430, 1280, 720, rgba("#D9B77E"))
    c.rect(0, 430, 1280, 452, rgba("#8FBF72"))
    trees(c, 440, (80, 220, 1060, 1210), 1.1)
    for x in (520, 760):                                       # 골대
        c.rect(x - 5, 330, x + 5, 470, WHITE)
    c.rect(515, 325, 765, 337, WHITE)
    c.rect(330, 560, 950, 590, rgba("#A9764D"), radius=8)      # 벤치
    c.rect(330, 500, 950, 524, rgba("#A9764D"), radius=8)
    for x in (380, 900):
        c.rect(x - 10, 500, x + 10, 660, rgba("#6E4729"), radius=4)


def bg_front_gate(c):
    sky(c)
    c.rect(360, 250, 920, 470, rgba("#F4EBDD"))                # 학교 건물
    c.rect(360, 236, 920, 262, rgba("#C97B63"))
    for row in range(2):
        for k in range(8):
            c.rect(390 + k * 64, 290 + row * 80, 430 + k * 64, 340 + row * 80, rgba("#BFE1F7"), radius=4)
    c.rect(0, 470, 1280, 720, rgba("#BFD9A6"))
    c.polygon([(520, 470), (760, 470), (1000, 720), (280, 720)], rgba("#E7DCC8"))   # 길
    trees(c, 520, (170, 300, 980, 1110), 1.2)
    for x in (120, 1080):                                      # 벽돌 기둥
        c.rect(x, 300, x + 90, 640, rgba("#B5654E"), radius=6)
        c.rect(x - 12, 280, x + 102, 312, rgba("#8E4A38"), radius=6)
        for k in range(1, 6):
            c.line([(x, 312 + k * 54), (x + 90, 312 + k * 54)], rgba("#9A5340"), 3)


BACKGROUNDS = {
    "store_line": bg_store_line,
    "library": bg_library,
    "rooftop": bg_rooftop,
    "corridor": bg_corridor,
    "cafeteria": bg_cafeteria,
    "science_lab": bg_science_lab,
    "field_bench": bg_field_bench,
    "front_gate": bg_front_gate,
}


def make_background(key):
    c = Canvas(1280, 720, WHITE)
    BACKGROUNDS[key](c)
    c.blur(1.6)   # 살짝 흐려서 인물이 앞에 서 보이게 한다
    save(c.result().convert("RGB"), HERE / "placeholder" / "bg" / f"{key}.jpg", quality=88)


def main():
    make_ui()
    for who in CHARACTERS:
        for face in FACES:
            make_sprite(who, face)
    for key in BACKGROUNDS:
        make_background(key)


if __name__ == "__main__":
    main()

## 엔딩 카드의 호감도 곡선.
##
## 턴마다 받은 호감도(sg_score_log)를 점으로 찍고 잇는다. 오른 구간은 분홍, 내린 구간은 파랑,
## 그대로인 구간은 연보라다. 엔딩이 뜨면 앞에서부터 한 구간씩 차례로 그려진다.
## 선은 얇은 막대(Solid)를 돌려서 긋는다. 그림 파일을 새로 만들지 않아도 되고 GPU가 그린다.

## 곡선 상자의 기본 크기. 엔딩 카드 안쪽 폭(660)에 맞춘다. 높이는 엔딩마다 글 길이에 맞춰 정한다(sg_curve_height)
define sg_curve_size = (660, 120)
## 곡선 상자 안의 여백: 왼쪽, 위, 오른쪽, 아래. 위는 마지막 점의 점수 글자가 들어갈 자리다
define sg_curve_pad = (56, 22, 30, 10)
## 이 점수부터 대성공이다(sogaeting/data/endings.json). 곡선 뒤에 연한 띠로 칠한다
define sg_curve_great = 85

transform sg_curve_in(delay=0.0):
    alpha 0.0
    pause delay
    linear 0.18 alpha 1.0

transform sg_curve_dot_in(delay=0.0, zoom_to=1.0):
    alpha 0.0 zoom 0.2
    pause delay
    easein 0.22 alpha 1.0 zoom zoom_to

init python:

    import math

    def sg_curve_points(scores, total, size=None, pad=None):
        """점수들을 상자 안의 (x, y) 좌표로. 가로는 등장부터 마지막 답까지 total+1칸으로 나눈다."""
        w, h = size or sg_curve_size
        left, top, right, bottom = pad or sg_curve_pad
        slots = max(1, int(total))
        inner_w = w - left - right
        inner_h = h - top - bottom
        points = [ ]
        for i, s in enumerate(scores[:slots + 1]):
            x = left + inner_w * i / float(slots)
            y = top + inner_h * (100 - max(0, min(100, s))) / 100.0
            points.append((int(round(x)), int(round(y))))
        return points

    def sg_curve_segment(p, q, color, thickness=4):
        """두 점을 잇는 막대 하나. 가운데를 기준으로 돌려서 두 점 사이에 놓는다."""
        dx, dy = q[0] - p[0], q[1] - p[1]
        length = max(1, int(round(math.hypot(dx, dy))) + 2)
        angle = math.degrees(math.atan2(dy, dx))
        bar = Transform(Solid(color, xysize=(length, thickness)), rotate=angle, rotate_pad=False,
                        anchor=(0.5, 0.5), transform_anchor=True)
        return bar, ((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0)

    def sg_curve(scores, total, step=0.09, height=None):
        """호감도 곡선 그림 하나(Fixed). 점이 둘보다 적으면 None."""
        if not isinstance(scores, (list, tuple)) or len(scores) < 2:
            return None
        w, h = sg_curve_size
        if height:
            h = int(height)
        size = (w, h)
        left, top, right, bottom = sg_curve_pad
        box = Fixed(xysize=(w, h))

        # 대성공 구간: 연한 분홍 띠
        top_y = sg_curve_points([100], 1, size)[0][1]
        great_y = sg_curve_points([sg_curve_great], 1, size)[0][1]
        box.add(Transform(Solid("#ffd6e4"), alpha=0.55, xpos=left, ypos=top_y,
                          xysize=(w - left - right, max(1, great_y - top_y))))
        box.add(Text("대성공", font=gui.interface_text_font, size=12, color="#e98aac",
                     xanchor=1.0, xpos=left - 10, yanchor=0.5, ypos=(top_y + great_y) // 2))

        # 시작 점수(50) 기준선: 점선
        base_y = sg_curve_points([50], 1, size)[0][1]
        x = left
        while x < w - right:
            box.add(Transform(Solid("#e7b9cc"), xysize=(6, 2), xpos=x, ypos=base_y - 1))
            x += 12
        box.add(Text("50", font=gui.interface_text_font, size=13, color="#c48aa3",
                     xanchor=1.0, xpos=left - 10, yanchor=0.5, ypos=base_y))

        points = sg_curve_points(scores, total, size)
        for i in range(1, len(points)):
            before, after = scores[i - 1], scores[i]
            if after > before:
                color = gui.sg_pink
            elif after < before:
                color = gui.sg_blue
            else:
                color = "#cdb8dd"
            bar, (mx, my) = sg_curve_segment(points[i - 1], points[i], color)
            box.add(At(Transform(bar, xpos=int(mx), ypos=int(my)), sg_curve_in(step * i)))

        # 점: 흰 테두리가 있는 하트. 그림(heart.png)은 흰색이라 색을 입혀 쓴다. 마지막 점은 크게
        last = len(points) - 1
        for i, (px, py) in enumerate(points):
            size = 0.40 if i == last else 0.24
            color = gui.sg_pink if i == 0 or scores[i] >= scores[i - 1] else gui.sg_blue
            dot = Fixed(
                Transform("images/ui/heart.png", zoom=size * 1.45, anchor=(0.5, 0.5), xpos=0, ypos=0),
                Transform("images/ui/heart.png", zoom=size, anchor=(0.5, 0.5), xpos=0, ypos=0,
                          matrixcolor=TintMatrix(color)),
                xysize=(0, 0))
            box.add(At(Transform(dot, xpos=px, ypos=py), sg_curve_dot_in(step * i, 1.0)))
        px, py = points[last]
        label = Text(str(scores[last]), font=gui.interface_text_font, size=16, bold=True,
                     color=gui.sg_pink_deep, outlines=[ (2, "#ffffff", 0, 0) ])
        box.add(At(Transform(label, xanchor=0.5, yanchor=1.0, xpos=px, ypos=max(16, py - 12)),
                   sg_curve_in(step * last + 0.1)))
        return box

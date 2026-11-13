## 그림 찾기: 배경과 스탠딩.
##
## 진짜 그림이 있으면 그것을 쓰고, 없으면 images/placeholder/ 의 자리표시 그림을 쓴다.
##
##   스탠딩   images/sprites/<캐릭터 id>/<표정>.png   768x1152, 투명 배경, 허리 위
##   배경     images/bg/<키>.jpg                      1280x720
##
## 자리표시 그림은 images/sg_make_images.py 가 만든다.

## 서버가 알려 주는 등장 장소(한글)와 배경 그림의 키.
## tools/art_prompts.json 의 backgrounds.<키>.seed 를 옮겨 적은 것이다.
## 둘이 어긋나면 tests/test_renpy_assets.py 가 실패한다.
define sg_place_bg = {
    "매점 줄": "store_line",
    "도서관": "library",
    "옥상": "rooftop",
    "복도 모퉁이": "corridor",
    "급식실": "cafeteria",
    "과학실": "science_lab",
    "운동장 벤치": "field_bench",
    "정문 앞": "front_gate",
}

## 표정 여섯 가지. 서버가 턴마다 이 가운데 하나를 준다.
define sg_faces = ("neutral", "smile", "blush", "pout", "shock", "dark")

## 장소를 모를 때와 고르기 화면에 쓰는 배경.
define sg_default_bg = "front_gate"

## 엔딩 등급(band_id)마다 엔딩 화면에 세울 표정.
define sg_band_face = {
    "great": "blush",
    "good": "smile",
    "soso": "neutral",
    "bad": "pout",
    "worst": "dark",
}

init -5 python:

    def sg_first_loadable(paths):
        """paths 가운데 처음으로 읽을 수 있는 파일. 없으면 None."""
        for path in paths:
            if renpy.loadable(path):
                return path
        return None

    def sg_bg_key(place):
        """등장 장소(한글)에 맞는 배경 키. 모르는 장소면 기본 배경."""
        return sg_place_bg.get(place, sg_default_bg)

    def sg_bg_image(key):
        """배경 그림. 진짜 그림, 자리표시 그림, 단색 순서로 찾는다."""
        if not isinstance(key, str) or not key.replace("_", "").isalnum():
            key = sg_default_bg
        path = sg_first_loadable([
            "images/bg/%s.jpg" % key,
            "images/bg/%s.png" % key,
            "images/bg/%s.webp" % key,
            "images/placeholder/bg/%s.jpg" % key,
            "images/placeholder/bg/%s.jpg" % sg_default_bg,
        ])
        if path is None:
            return Solid("#cfd8ea")
        return Transform(path, xysize=(1280, 720), fit="cover")

    def sg_sprite_path(char_id, face):
        """스탠딩 그림 파일. 그 표정이 없으면 평소 표정, 그것도 없으면 자리표시 그림."""
        if not isinstance(char_id, str) or not char_id.replace("_", "").isalnum():
            return None
        if face not in sg_faces:
            face = "neutral"
        return sg_first_loadable([
            "images/sprites/%s/%s.png" % (char_id, face),
            "images/sprites/%s/%s.webp" % (char_id, face),
            "images/sprites/%s/neutral.png" % char_id,
            "images/sprites/%s/neutral.webp" % char_id,
            "images/placeholder/sprites/%s/%s.png" % (char_id, face),
            "images/placeholder/sprites/%s/neutral.png" % char_id,
        ])

    def sg_sprite_image(char_id, face):
        """스탠딩 그림. 파일이 하나도 없는 캐릭터면 빈 그림."""
        path = sg_sprite_path(char_id, face)
        if path is None:
            return Null(768, 1152)
        return Image(path)

    def sg_portrait(char_id, width, height, face="smile"):
        """카드에 넣는 얼굴 그림. 스탠딩의 머리 부분을 잘라 쓴다. 없으면 None."""
        path = sg_sprite_path(char_id, face)
        if path is None:
            return None
        # 스탠딩 768x1152 에서 머리와 어깨가 들어오는 네모
        crop_w = 560
        crop_h = int(crop_w * height / float(width))
        return Transform(path, crop=(104, 40, crop_w, crop_h), xysize=(width, height))

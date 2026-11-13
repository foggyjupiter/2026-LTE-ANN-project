"""Ren'Py 화면(renpy/game/sg_assets.rpy)에 옮겨 적은 값이 원본과 어긋나지 않는지 본다.

- 등장 장소와 배경 키의 짝: tools/art_prompts.json 의 backgrounds.<키>.seed
- 표정 이름: tools/art_prompts.json 의 faces
- 등장 장소 목록: sogaeting/data/seeds.json 의 entrance
- 엔딩 등급: sogaeting/data/endings.json 의 id
- 자리표시 그림: 캐릭터마다 표정 여섯 장, 배경 키마다 한 장

Ren'Py를 띄우지 않고 .rpy 파일의 글만 읽는다.
"""
import ast
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAME = ROOT / "renpy" / "game"
ASSETS_RPY = GAME / "sg_assets.rpy"


def _defined(name):
    """sg_assets.rpy 의 `define <name> = <값>` 에서 값을 읽는다."""
    text = ASSETS_RPY.read_text(encoding="utf-8")
    match = re.search(rf"^define {re.escape(name)} = ", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"sg_assets.rpy 에 define {name} 이 없다")
    rest = text[match.end():]
    opener = rest[0]
    if opener not in "({[":
        return ast.literal_eval(rest.splitlines()[0])
    closer = {"(": ")", "{": "}", "[": "]"}[opener]
    depth = 0
    for index, char in enumerate(rest):
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return ast.literal_eval(rest[:index + 1])
    raise AssertionError(f"define {name} 의 값이 닫히지 않았다")


def _json(*parts):
    return json.loads(ROOT.joinpath(*parts).read_text(encoding="utf-8"))


class PlaceBackgroundTest(unittest.TestCase):
    def setUp(self):
        self.prompts = _json("tools", "art_prompts.json")
        self.place_bg = _defined("sg_place_bg")

    def test_matches_art_prompts(self):
        expected = {spec["seed"]: key for key, spec in self.prompts["backgrounds"].items()}
        self.assertEqual(self.place_bg, expected)

    def test_covers_every_entrance_seed(self):
        entrances = _json("sogaeting", "data", "seeds.json")["entrance"]
        self.assertEqual(sorted(self.place_bg), sorted(entrances))

    def test_default_background_is_a_known_key(self):
        self.assertIn(_defined("sg_default_bg"), self.prompts["backgrounds"])


class FaceTest(unittest.TestCase):
    def test_faces_match_art_prompts(self):
        self.assertEqual(list(_defined("sg_faces")), list(_json("tools", "art_prompts.json")["faces"]))

    def test_band_faces(self):
        band_face = _defined("sg_band_face")
        bands = [grade["id"] for grade in _json("sogaeting", "data", "endings.json")]
        self.assertEqual(sorted(band_face), sorted(bands))
        for face in band_face.values():
            self.assertIn(face, _defined("sg_faces"))


class PlaceholderTest(unittest.TestCase):
    """진짜 그림이 없을 때 쓰는 자리표시 그림이 빠짐없이 있는지 본다."""

    def test_every_character_has_six_faces(self):
        characters = sorted(_json("tools", "art_prompts.json")["characters"])
        data_ids = sorted(path.stem for path in (ROOT / "sogaeting" / "data" / "characters").glob("*.json"))
        self.assertEqual(characters, data_ids)
        for char_id in characters:
            for face in _defined("sg_faces"):
                path = GAME / "images" / "placeholder" / "sprites" / char_id / f"{face}.png"
                self.assertTrue(path.is_file(), f"자리표시 스탠딩이 없다: {path.relative_to(ROOT)}")

    def test_every_background_key_has_a_placeholder(self):
        for key in _json("tools", "art_prompts.json")["backgrounds"]:
            path = GAME / "images" / "placeholder" / "bg" / f"{key}.jpg"
            self.assertTrue(path.is_file(), f"자리표시 배경이 없다: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    unittest.main()

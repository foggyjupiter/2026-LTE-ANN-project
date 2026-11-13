"""Ren'Py 화면의 소리(renpy/game/sg_audio.rpy)가 가리키는 것이 실제로 있는지 본다.

- sg_sounds 의 소리 파일이 전부 있고, 비어 있지 않고, Ogg 파일이다
- audio/ 폴더에 sg_sounds 가 모르는 효과음 파일이 없다 (배경음 bgm.* 은 뺀다)
- 연출, 단추, 엔딩에 적은 소리 이름이 sg_sounds 에 있다
- 소리를 건 연출 이름이 sg_fx.rpy 에, 단추 스타일이 sg_screens.rpy 나 sg_fx.rpy 에 있다
- 엔딩 등급이 sogaeting/data/endings.json 에 있다

Ren'Py를 띄우지 않고 .rpy 파일의 글만 읽는다.
"""
import ast
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAME = ROOT / "renpy" / "game"
AUDIO_RPY = GAME / "sg_audio.rpy"


def _defined(name):
    """sg_audio.rpy 의 `define <name> = <값>` 에서 값을 읽는다."""
    text = AUDIO_RPY.read_text(encoding="utf-8")
    match = re.search(rf"^define {re.escape(name)} = ", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"sg_audio.rpy 에 define {name} 이 없다")
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


def _read(name):
    path = GAME / name
    return path.read_text(encoding="utf-8") if path.exists() else None


class SoundFileTest(unittest.TestCase):
    def setUp(self):
        self.sounds = _defined("sg_sounds")

    def test_every_sound_file_exists_and_is_not_empty(self):
        self.assertTrue(self.sounds)
        for name, path in self.sounds.items():
            with self.subTest(sound=name):
                file = GAME / path
                self.assertTrue(file.is_file(), f"{path} 가 없다. renpy/dev/make_sfx.py 를 돌린다")
                data = file.read_bytes()
                self.assertGreater(len(data), 1000, f"{path} 가 비었거나 너무 작다")
                self.assertEqual(data[:4], b"OggS", f"{path} 는 Ogg 파일이 아니다")

    def test_sound_files_live_in_audio_folder(self):
        for name, path in self.sounds.items():
            with self.subTest(sound=name):
                self.assertRegex(path, r"^audio/[a-z0-9_]+\.ogg$")

    def test_no_stray_sound_files(self):
        known = {pathlib.PurePosixPath(path).name for path in self.sounds.values()}
        found = {file.name for file in (GAME / "audio").iterdir()
                 if file.is_file() and file.stem != "bgm" and not file.name.startswith(".")}
        self.assertEqual(found - known, set(), "sg_sounds 에 없는 파일이 audio/ 에 있다")

    def test_bgm_is_not_shipped(self):
        # 배경음은 사용자가 나중에 넣는다. 레포에는 자리만 있다
        for path in _defined("sg_bgm_files"):
            with self.subTest(path=path):
                self.assertRegex(path, r"^audio/bgm\.[a-z0-9]+$")
                self.assertNotIn(path, self.sounds.values())


class SoundNameTest(unittest.TestCase):
    def setUp(self):
        self.sounds = _defined("sg_sounds")

    def test_fx_sounds_are_known(self):
        fx = _defined("sg_fx_sounds")
        for effect, sound in fx.items():
            with self.subTest(effect=effect):
                self.assertIn(sound, self.sounds)
        text = _read("sg_fx.rpy")
        if text is None:
            self.skipTest("sg_fx.rpy 가 없다")
        for effect in fx:
            with self.subTest(effect=effect):
                self.assertIn(f'"{effect}":', text, f"sg_fx.rpy 의 sg_fx_table 에 {effect} 가 없다")

    def test_button_sounds_are_known(self):
        buttons = _defined("sg_button_sounds")
        text = "\n".join(t for t in (_read("sg_screens.rpy"), _read("sg_fx.rpy")) if t)
        for style, pair in buttons.items():
            with self.subTest(style=style):
                self.assertEqual(len(pair), 2)
                for sound in pair:
                    if sound is not None:
                        self.assertIn(sound, self.sounds)
                self.assertRegex(text, rf"(?m)^style {re.escape(style)}\b", f"스타일 {style} 을 찾지 못했다")

    def test_ending_sounds_are_known(self):
        endings = _defined("sg_ending_sounds")
        bands = {band["id"] for band in json.loads(
            (ROOT / "sogaeting" / "data" / "endings.json").read_text(encoding="utf-8"))}
        for band, sound in endings.items():
            with self.subTest(band=band):
                self.assertIn(sound, self.sounds)
                self.assertIn(band, bands)
        self.assertIn("end_calm", self.sounds)     # 표에 없는 등급이 쓰는 소리

    def test_score_sounds_exist(self):
        for name in ("up", "down", "big_up", "big_down", "odd"):
            with self.subTest(sound=name):
                self.assertIn(name, self.sounds)


if __name__ == "__main__":
    unittest.main()

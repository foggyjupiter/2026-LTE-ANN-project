"""배경음 MIDI의 악기를 학교 연애 게임에 맞는 악기로 바꾼다. 개발용이다.

작곡 도구(fl-studio-plugin arranger)는 편성을 여러 단계로 고르고, 그 과정에서 합창, 신스 패드, 칩 사각파,
PC-98 신스 같은 소리가 끼어들었다(사용자: "아카펠라도 있고 게임 분위기와 너무 안 어울려").
그래서 곡을 만든 뒤 트랙마다 역할(트랙 이름의 " - " 앞)을 보고 아래 표의 GM 악기로 바꾼다.
음과 리듬은 그대로 두고 악기 번호(program change)와 뱅크(CC0, CC32), 트랙 이름만 바꾼다.

    python3 set_instruments.py <곡 폴더(song.mid, meta.json)> <menu|talk|high|low> <내보낼 폴더>

내보낸 폴더의 song.mid를 arranger의 렌더러로 렌더링한다:
    python -m tools.render_audio <내보낸 폴더>/song.mid --soundfont sgm -o bgm_<상황>.ogg
렌더러는 곡 폴더의 meta.json에서 트랙 효과를 트랙 이름으로 찾으므로, 효과 체인도 새 이름으로 옮겨 적는다.
mido가 있어야 한다.
"""
import json
import pathlib
import sys

import mido

DRUM_CHANNEL = 9
# 드럼 세트 (뱅크 128 자리, SGM-V2.01 이름)
STANDARD_KIT = (0, "Standard Kit")
BRUSH_KIT = (40, "Brush Kit")
DRUM_KITS = {"menu": STANDARD_KIT, "talk": BRUSH_KIT, "high": STANDARD_KIT, "low": BRUSH_KIT}
BANK_MSB = 0      # CC0
BANK_LSB = 32     # CC32

# GM 악기 번호 (0부터)
PIANO = (0, "Piano")
ELECTRIC_PIANO = (4, "Electric Piano")
ELECTRIC_PIANO_2 = (5, "Electric Piano 2")
GLOCKENSPIEL = (9, "Glockenspiel")
VIBRAPHONE = (11, "Vibraphone")
NYLON_GUITAR = (24, "Nylon Guitar")
CLEAN_GUITAR = (27, "Clean Guitar")
ACOUSTIC_BASS = (32, "Acoustic Bass")
FINGER_BASS = (33, "Finger Bass")
VIOLIN = (40, "Violin")
HARP = (46, "Harp")
STRINGS = (48, "Strings")
SLOW_STRINGS = (49, "Slow Strings")
CLARINET = (71, "Clarinet")
FLUTE = (73, "Flute")

# 역할(트랙 이름의 " - " 앞)마다 악기. 표에 없는 역할은 FAMILY_DEFAULT를 따른다
INSTRUMENTS = {
	"menu": {     # 신나는 뱀프를 피아노로 친다 (사용자 "메인화면은 뱀프로 하되 피아노로"). 뱀프는 Ostinato 1이다.
		# 주선율까지 피아노면 뱀프와 뭉치므로 주선율은 플루트, 둘째 선율은 비브라폰
		"Lead 1": FLUTE, "Lead 2": VIBRAPHONE, "Lead 3": CLARINET, "Lead Layer 1": STRINGS,
		"Counter": CLARINET, "Piano": PIANO, "Ostinato 1": PIANO, "Ostinato 2": ELECTRIC_PIANO,
		"Sustain": STRINGS, "Sustain 2": SLOW_STRINGS, "Wall of Chords": SLOW_STRINGS, "Bass": FINGER_BASS,
	},
	"talk": {     # 대화 중, 호감도 보통: 잔잔하게
		"Lead 1": PIANO, "Lead 2": FLUTE, "Lead 3": GLOCKENSPIEL, "Lead Layer 1": STRINGS,
		"Counter": CLARINET, "Piano": PIANO, "Ostinato 1": NYLON_GUITAR, "Ostinato 2": HARP,
		"Sustain": STRINGS, "Sustain 2": SLOW_STRINGS, "Wall of Chords": SLOW_STRINGS, "Bass": ACOUSTIC_BASS,
	},
	"high": {     # 대화 중, 호감도 높음: 들뜬 뱀프
		"Lead 1": ELECTRIC_PIANO, "Lead 2": FLUTE, "Lead 3": VIBRAPHONE, "Lead Layer 1": STRINGS,
		"Counter": PIANO, "Piano": PIANO, "Ostinato 1": CLEAN_GUITAR, "Ostinato 2": ELECTRIC_PIANO_2,
		"Sustain": STRINGS, "Sustain 2": SLOW_STRINGS, "Wall of Chords": SLOW_STRINGS, "Bass": FINGER_BASS,
	},
	"low": {      # 대화 중, 호감도 낮음: 단조, 가라앉게
		"Lead 1": PIANO, "Lead 2": VIOLIN, "Lead 3": FLUTE, "Lead Layer 1": SLOW_STRINGS,
		"Counter": CLARINET, "Piano": PIANO, "Ostinato 1": NYLON_GUITAR, "Ostinato 2": HARP,
		"Sustain": SLOW_STRINGS, "Sustain 2": STRINGS, "Wall of Chords": SLOW_STRINGS, "Bass": ACOUSTIC_BASS,
	},
}
# 표에 없는 역할: 이름의 첫 낱말로 고른다
FAMILY_DEFAULT = {
	"Lead": PIANO, "Counter": CLARINET, "Piano": PIANO, "Ostinato": HARP, "Sustain": STRINGS,
	"Wall": SLOW_STRINGS, "Hits": STRINGS, "Arp": HARP, "Bass": ACOUSTIC_BASS,
}


# 반복 음형에는 메아리(딜레이)를 걸지 않는다. 원래 신스 음색에 맞춘 메아리라 피아노·기타 반복 음형에서는 리듬이 번진다
DRY_ROLES = ("Ostinato",)
ECHO = "Fruity Delay 2"


def role_of(name):
	return name.split(" - ")[0].strip()


def instrument_for(role, table):
	if role in table: return table[role]
	family = role.split(" ")[0]
	return FAMILY_DEFAULT.get(family, PIANO)


def convert(folder, mood, out):
	table = INSTRUMENTS[mood]
	source = mido.MidiFile(pathlib.Path(folder) / "song.mid")
	renamed = {}
	for track in source.tracks:
		name = next((m.name for m in track if m.type == "track_name"), "")
		channels = {m.channel for m in track if hasattr(m, "channel")}
		if not channels: continue                     # 템포만 든 지휘 트랙
		drums = channels == {DRUM_CHANNEL}
		role = role_of(name)
		program, sound = DRUM_KITS[mood] if drums else instrument_for(role, table)
		new_name = role + " - " + sound
		renamed[name] = new_name
		for index, message in enumerate(track):
			if message.type == "track_name":
				track[index] = message.copy(name=new_name)
			elif message.type == "program_change":
				track[index] = message.copy(program=program)
			elif message.type == "control_change" and message.control in (BANK_MSB, BANK_LSB):
				track[index] = message.copy(value=0)
		# 처음에 악기를 한 번 정해 둔다 (악기 번호가 없던 트랙도 있다)
		channel = min(channels)
		track.insert(0, mido.Message("program_change", channel=channel, program=program, time=0))
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=True)
	source.save(out / "song.mid")
	# meta.json은 그대로 옮기되 (섹션 정보는 렌더러의 섹션 균형에 쓰인다), 게임 사운드폰트 자리는 빼고
	# 트랙 효과는 새 트랙 이름으로 옮긴다
	meta_path = pathlib.Path(folder) / "meta.json"
	meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
	ensemble = (meta.setdefault("personality", {}) or {}).setdefault("ensemble", {})
	ensemble.pop("soundfont_banks", None)
	meta.pop("vital", None)
	old = ensemble.get("effects") or {}
	effects = {}
	for name, chain in old.items():
		if name not in renamed: continue
		if role_of(name).startswith(DRY_ROLES): chain = [effect for effect in chain if effect.get("name") != ECHO]
		if chain: effects[renamed[name]] = chain
	ensemble["effects"] = effects
	meta["instruments"] = {"mood": mood, "renamed": renamed}
	(out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
	return renamed


if __name__ == "__main__":
	if len(sys.argv) != 4 or sys.argv[2] not in INSTRUMENTS:
		print(__doc__)
		sys.exit(2)
	for old_name, new_name in convert(sys.argv[1], sys.argv[2], sys.argv[3]).items():
		print(f"{old_name}  ->  {new_name}")

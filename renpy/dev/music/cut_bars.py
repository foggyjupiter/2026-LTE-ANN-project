"""배경음 MIDI에서 마디 구간을 잘라 낸다. 개발용이다.

대화 중 곡(talk, high, low)은 멜로디가 나오기 전 빌드업이 16-18초라 길었다(사용자: "빌드업을 좀 줄이고
멜로디가 빨리 나와도 될 듯"). 그래서 오스티나토만 나오는 첫 마디들과 멜로디 조각(티저)이 나오는
빌드업 끝 두 마디는 남기고, 그 사이를 잘라 낸다.

    python3 cut_bars.py <곡 폴더(song.mid, meta.json)> <처음 마디> <끝 마디> <내보낼 폴더>

마디 번호는 1부터 센다. <처음 마디>부터 <끝 마디>까지(끝 마디 포함)를 잘라 내고 뒤를 당긴다. 4/4박자만 다룬다.
- 잘린 구간에서 시작한 음은 버린다. 잘린 구간 앞에서 시작해 구간 안에서 끝나는 음은 구간 앞에서 끊고,
  구간을 넘어 이어지는 음은 그만큼 짧게 한다.
- 악기, 음량, 템포 같은 설정 메시지는 버리지 않고 잘린 자리로 옮긴다(뒤에서도 같은 설정이 이어지게).
- meta.json의 섹션 위치(start_bar, bars)도 고친다. 렌더러가 섹션 균형을 맞출 때 쓴다.
mido가 있어야 한다.
"""
import json
import pathlib
import sys

import mido

BEATS_PER_BAR = 4
NOTE_EVENTS = ("note_on", "note_off")
DROP_IN_CUT = ("marker", "text", "cue_marker", "lyrics")   # 잘린 자리에서 의미가 없는 표시


def is_note_off(message):
	return message.type == "note_off" or (message.type == "note_on" and message.velocity == 0)


def cut_track(track, start, stop):
	"""tick 구간 [start, stop)을 잘라 낸 새 트랙."""
	gap = stop - start
	events = []          # (tick, 순서, 메시지). 같은 tick이면 설정, 음 끄기, 음 켜기 순서
	sounding = {}        # (채널, 음) -> [(시작 tick, note_on 메시지)]
	now = 0
	end_tick = 0
	for index, message in enumerate(track):
		now += message.time
		if message.type == "end_of_track":
			end_tick = now
			continue
		if message.type == "note_on" and message.velocity > 0:
			sounding.setdefault((message.channel, message.note), []).append((now, message))
			continue
		if is_note_off(message):
			waiting = sounding.get((message.channel, message.note))
			if not waiting: continue
			begin, on = waiting.pop(0)
			if start <= begin < stop: continue                    # 잘린 구간에서 시작한 음
			if begin >= stop:
				begin, end = begin - gap, now - gap
			elif now <= start:
				end = now
			elif now >= stop:
				end = now - gap
			else:
				end = start
			events.append((begin, 2, index, on.copy(time=0)))
			events.append((end, 1, index, mido.Message("note_off", channel=on.channel, note=on.note, velocity=0)))
			continue
		if now < start:
			tick = now
		elif now < stop:
			if message.type in DROP_IN_CUT: continue
			tick = start
		else:
			tick = now - gap
		events.append((tick, 0, index, message.copy(time=0)))
	events.sort(key=lambda event: (event[0], event[1], event[2]))
	result = mido.MidiTrack()
	last = 0
	for tick, _, _, message in events:
		result.append(message.copy(time=tick - last))
		last = tick
	end_tick = max(last, end_tick - gap if end_tick >= stop else end_tick)
	result.append(mido.MetaMessage("end_of_track", time=end_tick - last))
	return result


def cut_sections(sections, first, last):
	"""섹션 목록에서 마디 [first, last](1부터, 끝 포함)를 뺀다. 다 잘린 섹션은 없앤다."""
	removed = last - first + 1
	result = []
	for section in sections:
		begin = section["start_bar"]
		end = begin + section["bars"]                    # 끝 마디 다음
		overlap = max(0, min(end, last + 1) - max(begin, first))
		bars = section["bars"] - overlap
		if bars <= 0: continue
		if begin > last: begin -= removed
		elif begin >= first: begin = first
		result.append(dict(section, start_bar=begin, bars=bars))
	return result


def cut(folder, first, last, out):
	source = mido.MidiFile(pathlib.Path(folder) / "song.mid")
	bar = source.ticks_per_beat * BEATS_PER_BAR
	start, stop = (first - 1) * bar, last * bar
	result = mido.MidiFile(type=source.type, ticks_per_beat=source.ticks_per_beat)
	result.tracks.extend(cut_track(track, start, stop) for track in source.tracks)
	out = pathlib.Path(out)
	out.mkdir(parents=True, exist_ok=True)
	result.save(out / "song.mid")
	meta_path = pathlib.Path(folder) / "meta.json"
	if meta_path.exists():
		meta = json.loads(meta_path.read_text(encoding="utf-8"))
		if meta.get("meter", "4/4") != "4/4": raise SystemExit("4/4박자만 다룬다")
		meta["sections"] = cut_sections(meta.get("sections") or [], first, last)
		meta["cut_bars"] = meta.get("cut_bars", []) + [[first, last]]
		(out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
	return source.length, result.length


if __name__ == "__main__":
	if len(sys.argv) != 5:
		print(__doc__)
		sys.exit(2)
	first, last = int(sys.argv[2]), int(sys.argv[3])
	if not 1 <= first <= last:
		print("마디 번호가 이상하다: %d-%d" % (first, last))
		sys.exit(2)
	before, after = cut(sys.argv[1], first, last, sys.argv[4])
	print("%.1f초 -> %.1f초" % (before, after))

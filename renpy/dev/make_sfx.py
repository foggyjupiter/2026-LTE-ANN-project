#!/usr/bin/env python3
"""소개팅 게임의 효과음을 합성해서 renpy/game/audio/*.ogg 로 만든다. 개발용이다.

    python3 renpy/dev/make_sfx.py            만들고, 만든 파일을 다시 읽어 숫자를 찍는다
    python3 renpy/dev/make_sfx.py --check    만들지 않고 있는 파일의 숫자만 찍는다
    python3 renpy/dev/make_sfx.py <폴더>     다른 폴더에 만든다

numpy 와 ffmpeg 가 있어야 한다. 바깥에서 받아 온 소리는 하나도 없다. 전부 여기서 계산한 파형이다.

만드는 원칙
- 사인파와 부드러운 삼각파(홀수 배음 셋)만 쓴다. 잡음은 주파수 띠를 좁혀서 쓴다.
- 음높이는 다장조 5음계(도 레 미 솔 라)에서만 고른다. 여러 소리가 겹쳐도 어울린다.
- 모든 소리의 처음과 끝을 0으로 페이드한다. 딸깍 소리가 나지 않게 하려는 것이다.
- 길이는 0.05초에서 1.2초, 최대 진폭은 -12dB 아래로 맞춘다.

소리 이름과 파일의 짝은 renpy/game/sg_audio.rpy 의 sg_sounds 에 적혀 있다.
파일을 더하거나 빼면 그쪽도 고친다. 어긋나면 tests/test_renpy_audio.py 가 실패한다.
"""
import argparse
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

RATE = 48000          # Ren'Py 가 섞을 때 쓰는 표본율과 같다
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "game" / "audio"

# 다장조 5음계의 음이름. 반음 자리(도=0)
STEPS = {"C": 0, "D": 2, "E": 4, "G": 7, "A": 9}


def hz(note):
    """음이름("C5", "A4")을 주파수로 바꾼다. A4 가 440Hz 다."""
    midi = 12 * (int(note[1:]) + 1) + STEPS[note[0]]
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def clock(dur):
    return np.arange(int(RATE * dur)) / RATE


def rise(n):
    """0에서 1로 부드럽게 오르는 곡선 n칸. 첫 칸이 0이다."""
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / max(1, n))


def pluck(dur, tau, attack=0.004):
    """퉁기는 소리의 크기 곡선: 짧게 올라갔다가 tau초마다 1/e 로 줄어든다."""
    env = np.exp(-clock(dur) / tau)
    n = min(len(env), int(RATE * attack))
    env[:n] *= rise(n)
    return env


def swell(dur, attack, release):
    """천천히 올라와 머물다가 천천히 내려가는 크기 곡선."""
    env = np.ones(int(RATE * dur))
    a, r = int(RATE * attack), int(RATE * release)
    env[:a] *= rise(a)
    env[len(env) - r:] *= rise(r)[::-1]
    return env


def sine(freq, dur):
    return np.sin(2 * np.pi * freq * clock(dur))


def bell(note, dur, tau):
    """맑은 차임 한 음: 사인파에 금방 사라지는 2, 3배음을 조금 얹는다."""
    f, tt = hz(note), clock(dur)
    wave_ = (np.sin(2 * np.pi * f * tt)
             + 0.22 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt / (tau * 0.5))
             + 0.08 * np.sin(2 * np.pi * 3 * f * tt) * np.exp(-tt / (tau * 0.3)))
    return wave_ * pluck(dur, tau)


def soft(note, dur, tau, attack=0.008):
    """부드러운 삼각파 한 음: 홀수 배음 셋(1, 3, 5)만 쓴다."""
    f, tt = hz(note), clock(dur)
    wave_ = (np.sin(2 * np.pi * f * tt)
             - np.sin(2 * np.pi * 3 * f * tt) / 9.0
             + np.sin(2 * np.pi * 5 * f * tt) / 25.0)
    return wave_ * pluck(dur, tau, attack)


def glide(f0, f1, dur, curve=1.0):
    """f0 에서 f1 로 미끄러지는 사인파. curve 가 1보다 크면 처음에 빨리 움직인다."""
    x = np.linspace(0.0, 1.0, int(RATE * dur)) ** (1.0 / curve)
    freq = f0 * (f1 / f0) ** x
    return np.sin(2 * np.pi * np.cumsum(freq) / RATE)


def noise(dur, lo, hi, seed, order=4):
    """lo 에서 hi Hz 사이만 남긴 잡음. 씨앗이 같으면 늘 같은 소리다."""
    n = int(RATE * dur)
    spec = np.fft.rfft(np.random.default_rng(seed).standard_normal(n))
    f = np.maximum(np.fft.rfftfreq(n, 1.0 / RATE), 1e-6)
    gain = 1.0 / np.sqrt(1.0 + (f / hi) ** (2 * order))
    if lo > 0:
        gain = gain / np.sqrt(1.0 + (lo / f) ** (2 * order))
    out = np.fft.irfft(spec * gain, n)
    return out / np.max(np.abs(out))


def mix(dur, *parts):
    """(시작 시각, 파형, 크기)들을 dur초짜리 한 줄에 겹친다."""
    out = np.zeros(int(RATE * dur))
    for at, part, gain in parts:
        i = int(RATE * at)
        part = part[:len(out) - i]
        out[i:i + len(part)] += gain * part
    return out


def finish(wave_, peak_db, fade_in=0.004, fade_out=0.03):
    """처음과 끝을 0으로 페이드하고 최대 진폭을 peak_db 로 맞춘다."""
    out = np.array(wave_, dtype=float)
    a = min(len(out) // 2, int(RATE * fade_in))
    b = min(len(out) // 2, int(RATE * fade_out))
    out[:a] *= rise(a)
    out[len(out) - b:] *= rise(b)[::-1]
    out[-1] = 0.0
    return out * (10.0 ** (peak_db / 20.0) / np.max(np.abs(out)))


################################################################################
# 단추와 대화
################################################################################

def ui_hover():
    """단추에 올림: 아주 작고 짧은 한 음."""
    return finish(sine(hz("G5"), 0.06) * pluck(0.06, 0.012), -24, fade_out=0.015)


def ui_click():
    """단추 누름: 짧은 톡."""
    return finish(bell("E5", 0.08, 0.018), -16, fade_out=0.02)


def ui_choice():
    """선택지 고름: 미, 솔 두 음이 빠르게 오른다."""
    return finish(mix(0.24, (0.0, bell("E5", 0.2, 0.05), 1.0), (0.06, bell("G5", 0.18, 0.06), 0.9)), -15)


def ui_next():
    """대사 넘김: 자주 나므로 가장 작고 낮게."""
    return finish(sine(hz("C5"), 0.07) * pluck(0.07, 0.013), -20, fade_out=0.015)


def ui_send():
    """글 보내기: 솔에서 미로 미끄러져 오르는 휙."""
    return finish(glide(hz("G4"), hz("E5"), 0.2) * swell(0.2, 0.012, 0.09), -15, fade_in=0.01, fade_out=0.06)


################################################################################
# 호감도
################################################################################

def score_up():
    """호감도 오름: 미 솔 도, 맑은 세 음."""
    return finish(mix(0.7, (0.0, bell("E5", 0.6, 0.16), 0.8), (0.09, bell("G5", 0.6, 0.17), 0.85),
                      (0.18, bell("C6", 0.52, 0.2), 1.0)), -13, fade_out=0.08)


def score_down():
    """호감도 내림: 미에서 도로 내려앉는 낮은 두 음."""
    return finish(mix(0.45, (0.0, soft("E4", 0.2, 0.07), 0.9), (0.14, soft("C4", 0.31, 0.1), 1.0)),
                  -13, fade_out=0.06)


def score_big_up():
    """큰 오름: 도 미 솔 도 미로 뛰어오르고 화음이 남는다."""
    parts = [(0.07 * i, bell(n, 0.5, 0.14), 0.75) for i, n in enumerate(("C5", "E5", "G5", "C6", "E6"))]
    parts += [(0.38, bell("G5", 0.72, 0.3), 0.5), (0.38, bell("C6", 0.72, 0.3), 0.6), (0.38, bell("E6", 0.72, 0.28), 0.4)]
    return finish(mix(1.1, *parts), -12, fade_out=0.12)


def score_big_down():
    """큰 내림: 라 미 도 라로 층층이 내려간다."""
    return finish(mix(0.95, (0.0, soft("A4", 0.3, 0.08), 0.8), (0.12, soft("E4", 0.3, 0.09), 0.85),
                      (0.24, soft("C4", 0.35, 0.1), 0.9), (0.36, soft("A3", 0.59, 0.2), 1.0)), -12, fade_out=0.1)


def score_odd():
    """숫자가 아닌 변화(NaN): 레 라 레, 갸웃하는 세 음."""
    return finish(mix(0.36, (0.0, soft("D5", 0.12, 0.04), 1.0), (0.1, soft("A4", 0.12, 0.04), 0.9),
                      (0.2, soft("D5", 0.16, 0.05), 1.0)), -15)


################################################################################
# 연출
################################################################################

def fx_thunder():
    """번개: 낮은 우르릉. 높은 쪽을 깎은 잡음이 굴러가며 잦아든다."""
    dur = 1.1
    roll = 0.6 + 0.4 * noise(dur, 0, 7, 11, order=2)          # 느리게 출렁이는 크기
    low = noise(dur, 45, 180, 12) * roll
    mid = noise(dur, 150, 420, 13) * roll                      # 작은 스피커에서도 들리는 띠
    thump = glide(75, 48, 0.6, 2.0) * pluck(0.6, 0.2, 0.01)
    body = (low + 0.3 * mid) * pluck(dur, 0.38, 0.04)
    return finish(mix(dur, (0.0, body, 1.0), (0.0, thump, 0.7)), -12, fade_in=0.02, fade_out=0.3)


def fx_thud():
    """흔들림: 둔한 쿵."""
    drum = glide(150, 68, 0.3, 3.0) * pluck(0.3, 0.07, 0.003)
    hit = noise(0.08, 60, 380, 21) * pluck(0.08, 0.018, 0.002)
    return finish(mix(0.3, (0.0, drum, 1.0), (0.0, hit, 0.3)), -12, fade_out=0.06)


def fx_sparkle():
    """반짝이: 높은 음 여섯이 잘게 흩어진다. 가장 높은 음이 2.1kHz 다."""
    notes = (("G6", 0.0, 1.0), ("C7", 0.06, 0.8), ("E6", 0.12, 0.9), ("A6", 0.19, 0.7),
             ("G6", 0.27, 0.55), ("C7", 0.36, 0.4))
    return finish(mix(0.62, *[(at, bell(n, 0.25, 0.06), g) for n, at, g in notes]), -16, fade_out=0.06)


def fx_heart():
    """하트: 통. 살짝 높은 데서 솔로 내려앉는 둥근 한 음."""
    tt = clock(0.28)
    freq = hz("G4") * (1.0 + 0.35 * np.exp(-tt / 0.018))
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    wave_ = (np.sin(phase) + 0.2 * np.sin(2 * phase) * np.exp(-tt / 0.03)) * pluck(0.28, 0.07, 0.003)
    return finish(wave_, -13, fade_out=0.06)


def fx_dark():
    """암전: 낮게 깔리는 음. 도와 솔이 천천히 올라왔다가 사라진다."""
    dur = 1.2
    tt = clock(dur)
    tone = sine(hz("C3"), dur) + 0.5 * sine(hz("G3"), dur) + 0.25 * sine(hz("C4"), dur)
    tone = tone * (1.0 - 0.12 * np.sin(2 * np.pi * 4.0 * tt))   # 느린 떨림
    return finish(tone * swell(dur, 0.3, 0.55), -14, fade_in=0.05, fade_out=0.2)


def fx_alert():
    """가짜 오류창: 미에서 도로 떨어지는 짧은 알림음."""
    return finish(mix(0.34, (0.0, soft("E5", 0.14, 0.06, 0.005), 1.0), (0.13, soft("C5", 0.21, 0.08, 0.005), 1.0)),
                  -14, fade_out=0.05)


def fx_glitch():
    """화면 깨짐: 띠를 좁힌 잡음이 다섯 번 끊겨 나오고 그 사이에 작은 삑 소리가 낀다."""
    dur = 0.3
    hiss = noise(dur, 500, 2400, 31)
    gate = np.zeros(int(RATE * dur))
    for at, length, gain in ((0.0, 0.04, 1.0), (0.06, 0.025, 0.6), (0.1, 0.05, 0.9),
                             (0.17, 0.02, 0.5), (0.21, 0.06, 0.8)):
        i, n = int(RATE * at), int(RATE * length)
        gate[i:i + n] = gain * swell(length, 0.003, 0.003)[:n]
    blips = mix(dur, (0.045, sine(hz("A5"), 0.012) * swell(0.012, 0.003, 0.003), 0.5),
                (0.152, sine(hz("E5"), 0.015) * swell(0.015, 0.003, 0.003), 0.5),
                (0.192, sine(hz("D6"), 0.012) * swell(0.012, 0.003, 0.003), 0.4))
    return finish(hiss * gate + blips, -16, fade_in=0.003, fade_out=0.02)


def fx_whoosh():
    """집중선: 슉. 잡음의 띠가 낮은 데서 높은 데로 훑고 지나간다."""
    dur = 0.36
    tt = clock(dur)
    out = np.zeros(len(tt))
    bands = 6
    for k in range(bands):
        center = 300.0 * (2600.0 / 300.0) ** (k / (bands - 1.0))
        when = 0.07 + 0.2 * k / (bands - 1.0)
        window = np.exp(-0.5 * ((tt - when) / 0.045) ** 2)
        out += noise(dur, center * 0.7, center * 1.35, 41 + k) * window * (1.0 - 0.08 * k)
    return finish(out, -15, fade_in=0.03, fade_out=0.06)


################################################################################
# 엔딩
################################################################################

def end_good():
    """좋은 엔딩: 도 미 솔로 올라가 화음으로 맺는 짧은 팡파르."""
    parts = [(0.1 * i, soft(n, 0.22, 0.09), 0.8) for i, n in enumerate(("C5", "E5", "G5"))]
    parts += [(0.32, bell("C6", 0.88, 0.34), 0.9), (0.32, soft("G5", 0.88, 0.32), 0.45),
              (0.32, soft("E5", 0.88, 0.32), 0.45), (0.32, soft("C5", 0.88, 0.3), 0.4)]
    return finish(mix(1.2, *parts), -12, fade_out=0.15)


def end_calm():
    """그 밖의 엔딩: 라, 미로 내려와 낮은 라와 미가 조용히 남는다."""
    return finish(mix(1.2, (0.0, bell("A4", 0.6, 0.2), 0.9), (0.26, bell("E4", 0.6, 0.22), 0.9),
                      (0.52, soft("A3", 0.68, 0.3, 0.02), 0.8), (0.52, bell("E4", 0.68, 0.3), 0.5)),
                  -14, fade_out=0.15)


# 파일 이름(확장자 빼고)과 만드는 함수
SOUNDS = {
    "ui_hover": ui_hover, "ui_click": ui_click, "ui_choice": ui_choice, "ui_next": ui_next, "ui_send": ui_send,
    "score_up": score_up, "score_down": score_down, "score_big_up": score_big_up,
    "score_big_down": score_big_down, "score_odd": score_odd,
    "fx_thunder": fx_thunder, "fx_thud": fx_thud, "fx_sparkle": fx_sparkle, "fx_heart": fx_heart,
    "fx_dark": fx_dark, "fx_alert": fx_alert, "fx_glitch": fx_glitch, "fx_whoosh": fx_whoosh,
    "end_good": end_good, "end_calm": end_calm,
}


################################################################################
# 쓰기와 확인
################################################################################

def write_ogg(samples, path):
    """파형을 16비트 WAV 로 적고 ffmpeg 로 Ogg Vorbis 로 바꾼다. 다시 만들어도 같은 파일이 나온다."""
    pcm = np.round(np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "in.wav"
        with wave.open(str(wav), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(RATE)
            out.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-map_metadata", "-1",
                        "-fflags", "+bitexact", "-flags:a", "+bitexact",
                        "-c:a", "libvorbis", "-q:a", "5", "-ar", str(RATE), "-ac", "1", str(path)], check=True)


def read_audio(path):
    """소리 파일을 ffmpeg 로 풀어 -1에서 1 사이의 값으로 읽는다."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1",
                          "-ar", str(RATE), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(float) / 32768.0


def db(value):
    return 20.0 * math.log10(value) if value > 0 else -120.0


def measure(path):
    """파일 하나의 길이(초), 최대 진폭, 맨 처음과 맨 끝 0.25ms 의 최대 진폭(dBFS).

    양 끝이 0에 가까워야 재생이 시작하고 끝날 때 딸깍 소리가 나지 않는다.
    """
    wave_ = read_audio(path)
    edge = int(RATE * 0.00025)
    return {
        "seconds": len(wave_) / RATE,
        "peak": db(float(np.max(np.abs(wave_)))),
        "head": db(float(np.max(np.abs(wave_[:edge])))),
        "tail": db(float(np.max(np.abs(wave_[-edge:])))),
        "bytes": path.stat().st_size,
    }


def report(folder):
    """만든 파일을 다시 읽어 표로 찍는다. 원칙에서 벗어난 파일이 있으면 False."""
    ok = True
    print("%-20s %7s %9s %11s %9s %7s" % ("파일", "길이(초)", "최대(dB)", "처음(dB)", "끝(dB)", "바이트"))
    for name in SOUNDS:
        path = folder / (name + ".ogg")
        m = measure(path)
        # 길이 0.05-1.2초, 최대 -12dB 아래(손실 압축의 오차 0.5dB 까지 봐준다), 양 끝은 최대보다 30dB 넘게 작다
        good = (0.045 <= m["seconds"] <= 1.21 and m["peak"] <= -11.5
                and m["head"] <= m["peak"] - 30 and m["tail"] <= m["peak"] - 30)
        ok = ok and good
        print("%-20s %8.3f %9.1f %11.1f %9.1f %7d%s" % (path.name, m["seconds"], m["peak"], m["head"],
                                                        m["tail"], m["bytes"], "" if good else "  <- 확인"))
    return ok


def main():
    parser = argparse.ArgumentParser(description="소개팅 게임의 효과음을 합성한다.")
    parser.add_argument("folder", nargs="?", default=str(OUT), help="소리 파일을 둘 폴더")
    parser.add_argument("--check", action="store_true", help="만들지 않고 있는 파일의 숫자만 찍는다")
    args = parser.parse_args()
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg 를 찾지 못했습니다. ffmpeg 를 설치한 뒤 다시 실행해 주세요.")
    folder = pathlib.Path(args.folder)
    if not args.check:
        folder.mkdir(parents=True, exist_ok=True)
        for name, build in SOUNDS.items():
            write_ogg(build(), folder / (name + ".ogg"))
    sys.exit(0 if report(folder) else 1)


if __name__ == "__main__":
    main()

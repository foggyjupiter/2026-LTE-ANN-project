## sg_audio.rpy: 효과음과 배경음 자리.
##
## 소리 파일은 audio/ 에 있고 dev/make_sfx.py 가 합성해서 만든다. 받아 온 소리는 없다.
## 이 파일은 다른 .rpy 를 고치지 않고 소리를 붙인다.
##   단추 소리    sg_screens.rpy 의 단추 스타일에 activate_sound, hover_sound 를 얹는다
##   연출 소리    sg_fx.rpy 의 sg_fx_play 를 감싼다. sg_fx.rpy 가 없으면 아무 일도 없다
##   배경음       audio/bgm.ogg (또는 bgm.mp3)가 있으면 고르기 화면부터 되풀이 재생한다
##
## 다른 파일에서 부르는 것. 전부 아무것도 돌려주지 않고, 파일이나 소리 장치가 없어도 조용히 지나간다.
##   sg_sfx(name)              효과음 하나. name 은 아래 sg_sounds 의 이름
##   sg_sfx_score(change)      호감도 변화. 숫자나 팝업 글("+7", "-14", "±0", "NaN")을 준다
##   sg_sfx_ending(band_id)    엔딩 등장. "great", "good" 은 팡파르, 나머지는 차분한 음
##   SgSfx(name), SgSfxScore(change)    화면의 action 목록에 넣는 꼴
##
## 환경변수 SOGAETING_MUTE=1 이면 효과음과 배경음을 모두 끈다.

## 음량. 0.0(안 들림)에서 1.0(파일에 담긴 크기 그대로) 사이. 0.5 는 절반(-6dB)이다.
## 효과음 파일은 이미 -12dB 아래로 작게 만들어져 있다.
define sg_sfx_volume = 0.8
define sg_bgm_volume = 0.2

## 호감도가 한 번에 이만큼 움직이면 큰 변화의 소리를 낸다. 서버는 바라던 말에 캐릭터마다 5-8점,
## 다정한 말에 2점을 올리고, -1에 5점, -2에 10점을 내린다(sogaeting/director.py의 POINTS, hit_points).
## sg_stage.rpy 의 큰 변화 연출(sg_stage_big_up, sg_stage_big_down)과 같은 기준이다.
define sg_score_big_up = 5
define sg_score_big_down = 10

## 소리 이름과 파일. 파일을 더하거나 빼면 dev/make_sfx.py 의 SOUNDS 도 고친다.
## 어긋나면 tests/test_renpy_audio.py 가 실패한다.
define sg_sounds = {
    ## 단추와 대화
    "hover": "audio/ui_hover.ogg",            # 단추에 올림
    "click": "audio/ui_click.ogg",            # 단추 누름
    "choice": "audio/ui_choice.ogg",          # 선택지 고름
    "next": "audio/ui_next.ogg",              # 대사 넘김
    "send": "audio/ui_send.ogg",              # 글 보내기
    ## 호감도
    "up": "audio/score_up.ogg",
    "down": "audio/score_down.ogg",
    "big_up": "audio/score_big_up.ogg",
    "big_down": "audio/score_big_down.ogg",
    "odd": "audio/score_odd.ogg",             # 숫자가 아닌 변화 (NaN)
    ## 연출
    "thunder": "audio/fx_thunder.ogg",
    "thud": "audio/fx_thud.ogg",
    "sparkle": "audio/fx_sparkle.ogg",
    "heart": "audio/fx_heart.ogg",
    "dark": "audio/fx_dark.ogg",
    "alert": "audio/fx_alert.ogg",
    "glitch": "audio/fx_glitch.ogg",
    "whoosh": "audio/fx_whoosh.ogg",
    ## 엔딩
    "end_good": "audio/end_good.ogg",
    "end_calm": "audio/end_calm.ogg",
}

## 연출 이름(서버가 주는 한글 이름)과 소리. 여기 없는 연출은 소리가 없다.
define sg_fx_sounds = {
    "번개": "thunder",
    "흔들림": "thud",
    "반짝이": "sparkle",
    "하트": "heart",
    "암전": "dark",
    "가짜 오류창": "alert",
    "화면 깨짐": "glitch",
    "집중선": "whoosh",
}

## 단추 스타일마다 (누를 때, 올릴 때)의 소리. None 은 소리 없음.
## 기본 스타일(button)에는 걸지 않는다. 화면 전체를 덮는 투명한 단추(대사 넘김, 기다리는
## 동안의 가림판)가 그 스타일을 써서, 걸면 화면 어디를 눌러도 소리가 난다.
define sg_button_sounds = {
    "sg_card": ("click", "hover"),
    "sg_choice": ("choice", "hover"),
    "sg_send": ("send", None),
    "sg_primary": ("click", "hover"),
    "sg_secondary": ("click", "hover"),
    "sg_ghost_button": ("click", "hover"),
    "sg_fx_err_ok": ("click", None),
}

## 엔딩 등급(band_id)과 소리. 여기 없는 등급은 차분한 음이다.
define sg_ending_sounds = {
    "great": "end_good",
    "good": "end_good",
}

## 배경음 파일. 앞에서부터 찾아서 처음 있는 것을 쓴다. 하나도 없으면 배경음이 없다.
define sg_bgm_files = ("audio/bgm.ogg", "audio/bgm.mp3")


## 다른 파일의 스타일과 sg_fx_play 가 다 만들어진 뒤에 돌아야 하므로 순서를 늦춘다.
init 900 python:

    import os

    ## SOGAETING_MUTE 가 비어 있지 않고 0 이 아니면 전부 끈다.
    sg_audio_muted = os.environ.get("SOGAETING_MUTE", "").strip() not in ("", "0")

    sg_audio_found = { }      # 소리 이름 -> 파일 경로 또는 None. 한 번 찾은 것을 적어 둔다

    def sg_audio_oops(where):
        """소리는 조용히 실패한다. 무슨 일이 있었는지만 log.txt 에 남긴다."""
        try:
            import traceback
            renpy.display.log.write("sg_audio: %s 에서 문제가 생겨 건너뛴다.", where)
            renpy.display.log.write("%s", traceback.format_exc())
        except Exception:
            pass

    def sg_sound_file(name):
        """소리 이름의 파일 경로. 꺼 두었거나, 모르는 이름이거나, 파일이 없으면 None."""
        if sg_audio_muted or not isinstance(name, str):
            return None
        if name not in sg_audio_found:
            path = sg_sounds.get(name)
            try:
                if not (isinstance(path, str) and renpy.loadable(path)):
                    path = None
            except Exception:
                path = None
            sg_audio_found[name] = path
        return sg_audio_found[name]

    def sg_sfx(name):
        """효과음 하나를 낸다. 여러 소리가 겹쳐도 서로 끊지 않는다(audio 채널)."""
        try:
            path = sg_sound_file(name)
            if path is not None:
                renpy.play(path, channel="audio")
        except Exception:
            sg_audio_oops("sg_sfx")

    def sg_score_sound(change):
        """호감도 변화에 맞는 소리 이름. 낼 소리가 없으면 None."""
        if change is None or isinstance(change, bool):
            return None
        if isinstance(change, str):
            text = change.strip().replace("−", "-").replace(",", "")   # 빼기 기호, 천 단위 쉼표("+60,000")도 받는다
            if not text or text.startswith("±"):             # 변화 없음
                return None
            try:
                change = float(text)
            except ValueError:
                return "odd"
        if not isinstance(change, (int, float)):
            return None
        if change != change:                                 # NaN
            return "odd"
        if change == 0:
            return None
        if change > 0:
            return "big_up" if change >= sg_score_big_up else "up"
        return "big_down" if -change >= sg_score_big_down else "down"

    def sg_sfx_score(change):
        """호감도가 움직일 때의 소리. change 는 숫자나 팝업 글("+8", "-10", "±0", "+60,000", "NaN")."""
        try:
            sg_sfx(sg_score_sound(change))
        except Exception:
            sg_audio_oops("sg_sfx_score")

    def sg_sfx_ending(band_id):
        """엔딩이 나올 때의 소리. band_id 는 서버가 준 엔딩 등급."""
        try:
            sg_sfx(sg_ending_sounds.get(band_id, "end_calm"))
        except Exception:
            sg_audio_oops("sg_sfx_ending")

    class SgSfx(Action, FieldEquality):
        """화면의 action 목록에 넣는 효과음. 예: action [ SgSfx("next"), Return(1) ]"""

        identity_fields = [ ]
        equality_fields = [ "name" ]

        def __init__(self, name):
            self.name = name

        def __call__(self):
            sg_sfx(self.name)

    class SgSfxScore(Action, FieldEquality):
        """화면의 action 목록에 넣는 호감도 소리. 예: SgSfxScore(v["popup"])"""

        identity_fields = [ ]
        equality_fields = [ "change" ]

        def __init__(self, change):
            self.change = change

        def __call__(self):
            sg_sfx_score(self.change)

    ############################################################################
    ## 음량
    ############################################################################

    def sg_audio_setup():
        """게임이 켜질 때 한 번, 효과음과 배경음의 음량을 맨 위의 값으로 맞춘다.

        이 게임에는 환경설정 화면이 없어서 음량을 바꿀 곳이 여기뿐이다.
        """
        try:
            for mixer, volume in (("sfx", sg_sfx_volume), ("music", sg_bgm_volume)):
                renpy.game.preferences.set_volume(mixer, max(0.0, min(1.0, float(volume))))
                renpy.game.preferences.set_mute(mixer, False)
        except Exception:
            sg_audio_oops("sg_audio_setup")

    config.start_callbacks.append(sg_audio_setup)

    ############################################################################
    ## 단추 소리
    ############################################################################

    def sg_audio_apply_styles():
        """단추 스타일에 누를 때와 올릴 때의 소리를 얹는다."""
        for name, (press, over) in sg_button_sounds.items():
            try:
                if sg_sound_file(press) is not None:
                    getattr(style, name).activate_sound = sg_sound_file(press)
                if sg_sound_file(over) is not None:
                    getattr(style, name).hover_sound = sg_sound_file(over)
            except Exception:
                ## 그 스타일이 없다(이름이 바뀌었거나 파일이 빠졌다). 그 단추만 소리 없이 둔다.
                pass

    class SgAudioStyles(object):
        """미뤄진 style 문들과 같은 줄에 서서, 그것들이 다 적용된 다음에 소리를 얹는다."""

        def apply(self):
            try:
                sg_audio_apply_styles()
            except Exception:
                sg_audio_oops("sg_audio_apply_styles")

    ## gui.init 을 쓰는 게임에서는 style 문이 init 때 실행되지 않고 init 이 끝난 뒤로 미뤄진다
    ## (Ren'Py 가 미뤄 둔 목록을 언어를 정할 때 차례로 적용한다). 지금 스타일을 고치면 아직
    ## 없는 스타일이 많으므로, 그 목록의 맨 뒤에 넣어서 다른 파일의 style 문 다음에 돌게 한다.
    try:
        if config.defer_styles:
            import sys
            sys.modules["renpy.translation"].deferred_styles.append(SgAudioStyles())
        else:
            sg_audio_apply_styles()
    except Exception:
        sg_audio_oops("단추 소리")

    ############################################################################
    ## 연출 소리
    ############################################################################

    def sg_fx_sound_names(names):
        """연출 이름 목록에서 낼 소리 이름을 차례로 고른다. 같은 소리는 한 번만."""
        if isinstance(names, str):
            names = [ names ]
        try:
            names = [ name for name in names ]
        except TypeError:
            return [ ]
        known = globals().get("sg_fx_table")
        out = [ ]
        for name in names:
            if not isinstance(name, str) or name not in sg_fx_sounds:
                continue
            if known is not None and name not in known:      # sg_fx.rpy 가 모르는 연출
                continue
            if sg_fx_sounds[name] not in out:
                out.append(sg_fx_sounds[name])
        return out

    ## sg_fx.rpy 가 만든 sg_fx_play 를 보관해 두고, 소리를 낸 뒤 그것을 부르는 함수로 바꾼다.
    ## sg_core.rpy 는 부를 때마다 store.sg_fx_play 를 찾으므로 바꾼 함수가 불린다.
    sg_fx_play_silent = globals().get("sg_fx_play")

    if sg_fx_play_silent is not None:

        def sg_fx_play(names, narration=""):
            """연출을 건다(sg_fx.rpy). 소리가 어울리는 연출이면 소리도 낸다."""
            try:
                for sound in sg_fx_sound_names(names):
                    sg_sfx(sound)
            except Exception:
                sg_audio_oops("sg_fx_play")
            return sg_fx_play_silent(names, narration=narration)

    ############################################################################
    ## 배경음
    ############################################################################
    ##
    ## options.rpy 가 config.has_music 을 꺼 두어서 기본 music 채널은 음량 조절이 안 된다.
    ## 그래서 음량(music 믹서)을 따르는 채널을 따로 둔다.

    renpy.music.register_channel("sg_bgm", mixer="music", loop=True)

    sg_bgm_file = None
    if not sg_audio_muted:
        for sg_audio_name in sg_bgm_files:
            try:
                if renpy.loadable(sg_audio_name):
                    sg_bgm_file = sg_audio_name
                    break
            except Exception:
                pass
    sg_audio_name = None

    def sg_bgm_start():
        """배경음 파일이 있으면 되풀이 재생한다. 이미 나오고 있으면 그대로 둔다."""
        try:
            if sg_bgm_file is not None:
                renpy.music.play(sg_bgm_file, channel="sg_bgm", loop=True, fadein=1.0, if_changed=True)
        except Exception:
            sg_audio_oops("sg_bgm_start")

    def sg_audio_on_label(name, abnormal):
        """고르기 화면(label sg_select)에 들어올 때 배경음을 켠다."""
        if name == "sg_select":
            sg_bgm_start()

    config.label_callbacks.append(sg_audio_on_label)

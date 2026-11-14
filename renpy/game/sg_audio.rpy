## sg_audio.rpy: 효과음과 배경음 자리.
##
## 소리 파일은 audio/ 에 있고 dev/make_sfx.py 가 합성해서 만든다. 받아 온 소리는 없다.
## 이 파일은 다른 .rpy 를 고치지 않고 소리를 붙인다.
##   단추 소리    sg_screens.rpy 의 단추 스타일에 activate_sound, hover_sound 를 얹는다
##   연출 소리    sg_fx.rpy 의 sg_fx_play 를 감싼다. sg_fx.rpy 가 없으면 아무 일도 없다
##   배경음       상황마다 곡을 바꾼다. 고르기 화면은 menu, 대화 중에는 호감도에 따라 talk, high, low,
##                엔딩에서는 배경음을 줄이고 엔딩 음을 들려준다. 네 곡은 같은 모티프의 다른 편곡이다.
##                상황별 파일이 없으면 audio/bgm.ogg (또는 bgm.mp3) 한 곡을 계속 튼다
##
## 다른 파일에서 부르는 것. 전부 아무것도 돌려주지 않고, 파일이나 소리 장치가 없어도 조용히 지나간다.
##   sg_sfx(name)              효과음 하나. name 은 아래 sg_sounds 의 이름
##   sg_sfx_score(change)      호감도 변화. 숫자나 팝업 글("+7", "-14", "±0", "NaN")을 준다
##   sg_sfx_ending(band_id)    엔딩 등장. "great", "good" 은 팡파르, 나머지는 차분한 음
##   sg_bgm_for_score(score)   대화 중 배경음을 호감도에 맞춘다 (sg_core.rpy 의 sg_enter_turn 이 부른다)
##   sg_bgm_ending()           엔딩에서 배경음을 줄인다
##   SgSfx(name), SgSfxScore(change)    화면의 action 목록에 넣는 꼴
##
## 환경변수 SOGAETING_MUTE=1 이면 효과음과 배경음을 모두 끈다.

## 음량. 0.0(안 들림)에서 1.0(파일에 담긴 크기 그대로) 사이. 0.5 는 절반(-6dB)이다.
## 효과음 파일은 이미 -12dB 아래로 작게 만들어져 있다.
define sg_sfx_volume = 0.8
define sg_bgm_volume = 0.2

## 호감도가 한 번에 이만큼 움직이면 큰 변화의 소리를 낸다. 서버는 바라던 말에 캐릭터마다 5-8점,
## 다정한 말에 2점을 올리고, -1에 5점, -2에 10점을 내린 뒤 반응의 세기에 따라 0.6-1.4배를 곱한다
## (sogaeting/director.py의 POINTS, hit_points, STRENGTH_SCALE).
## sg_stage.rpy 의 큰 변화 연출(sg_stage_big_up, sg_stage_big_down)과 같은 기준이다.
define sg_score_big_up = 3
define sg_score_big_down = 8

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

## 상황별 배경음. 같은 모티프(renpy/dev/music/motif.mid)로 분위기만 바꿔 만든 곡이다.
##   menu  고르기 화면. 신나는 디스코 뱀프
##   talk  대화 중, 호감도 보통
##   high  대화 중, 호감도가 높을 때. 들뜬 편곡
##   low   대화 중, 호감도가 낮을 때. 단조로 가라앉은 편곡
define sg_bgm_moods = {
    "menu": "audio/bgm_menu.ogg",
    "talk": "audio/bgm_talk.ogg",
    "high": "audio/bgm_high.ogg",
    "low": "audio/bgm_low.ogg",
}
## 상황별 파일이 없을 때 대신 쓰는 한 곡. 앞에서부터 찾아서 처음 있는 것을 쓴다.
define sg_bgm_files = ("audio/bgm.ogg", "audio/bgm.mp3")
## 호감도 구간. 서버의 구간(sogaeting/director.py band_of: 40, 65)과 같다. 경계에서 곡이 자꾸 바뀌지 않게
## 들어갈 때와 나올 때 5점 차이를 둔다 (65점에 high로 들어가면 60점 아래로 내려가야 talk로 돌아온다)
define sg_bgm_high_in = 65
define sg_bgm_high_out = 60
define sg_bgm_low_in = 40
define sg_bgm_low_out = 45
## 곡을 바꿀 때 새 곡이 커지는 시간과 앞 곡이 줄어드는 시간(초). 두 곡이 겹치며 바뀐다.
## Ren'Py의 페이드는 dB로 고르게 움직인다(2026-11-14 사인파로 잼: 페이드 시간 동안 약 -36dB에서 0dB까지).
## 그래서 둘을 같은 시간으로 겹치면 한가운데서 합친 소리가 15dB나 꺼진다. 앞 곡은 천천히(4초) 줄이고
## 새 곡은 빨리(1.2초) 키워 꺼짐을 6dB 안으로 줄인다. 대화 중 곡은 반복 음형만 나오는 조용한 두 마디로
## 시작해서, 앞 곡의 꼬리와 겹쳐도 덜 부딪힌다
define sg_bgm_fade_in = 1.2
define sg_bgm_fade_out = 4.0
## 엔딩에서 배경음을 줄이는 시간(초). 엔딩 음과 오래 겹치지 않게 짧게 둔다
define sg_bgm_ending_fade = 1.5


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
    ##
    ## 채널은 둘이다. 한 채널에서 곡을 바꾸면 앞 곡이 다 줄어든 뒤에야 새 곡이 시작해서, 그 사이에
    ## 소리가 거의 끊긴다(2026-11-14 SDL disk 출력으로 확인: 1.5초 줄고, 거의 무음, 1.5초 커짐).
    ## 새 곡은 쉬고 있는 채널에서 커지게 하고 앞 곡은 원래 채널에서 줄여서 두 곡이 겹치며 바뀌게 한다.

    sg_bgm_channels = ("sg_bgm_a", "sg_bgm_b")
    for sg_audio_channel in sg_bgm_channels:
        renpy.music.register_channel(sg_audio_channel, mixer="music", loop=True)
    sg_audio_channel = None

    def sg_audio_first_loadable(names):
        for name in names:
            try:
                if renpy.loadable(name):
                    return name
            except Exception:
                pass
        return None

    sg_bgm_file = None if sg_audio_muted else sg_audio_first_loadable(sg_bgm_files)
    sg_bgm_paths = { }
    if not sg_audio_muted:
        for sg_audio_name, sg_audio_path in sg_bgm_moods.items():
            sg_bgm_paths[sg_audio_name] = sg_audio_first_loadable((sg_audio_path,)) or sg_bgm_file
    sg_audio_name = sg_audio_path = None

    ## 지금 나오는 상황 이름 (menu, talk, high, low). 엔딩에서 줄였으면 None
    sg_bgm_now = None
    ## 지금 곡이 나오는 채널과 파일. 곡이 없으면 None
    sg_bgm_channel_now = None
    sg_bgm_path_now = None

    def sg_bgm_play(mood):
        """그 상황의 곡으로 바꾼다. 같은 파일이 이미 나오고 있으면 그대로 둔다.

        새 곡은 쉬고 있는 채널에서 처음부터 커지고, 앞 곡은 그동안 줄어든다."""
        global sg_bgm_now, sg_bgm_channel_now, sg_bgm_path_now
        try:
            path = sg_bgm_paths.get(mood)
            if path is None:
                return
            if path == sg_bgm_path_now and sg_bgm_channel_now is not None:
                sg_bgm_now = mood
                return
            old = sg_bgm_channel_now
            new = sg_bgm_channels[1] if old == sg_bgm_channels[0] else sg_bgm_channels[0]
            renpy.music.play(path, channel=new, loop=True, fadein=sg_bgm_fade_in, fadeout=0)
            if old is not None:
                renpy.music.stop(channel=old, fadeout=sg_bgm_fade_out)
            sg_bgm_now, sg_bgm_channel_now, sg_bgm_path_now = mood, new, path
        except Exception:
            sg_audio_oops("sg_bgm_play")

    def sg_bgm_start():
        """고르기 화면의 배경음을 튼다."""
        sg_bgm_play("menu")

    def sg_bgm_mood_for(score, now):
        """호감도와 지금 상황으로 대화 중의 곡을 고른다. 경계에서는 지금 곡을 조금 더 붙든다."""
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            return now if now in ("talk", "high", "low") else "talk"
        if now == "high":
            return "high" if score >= sg_bgm_high_out else ("low" if score < sg_bgm_low_in else "talk")
        if now == "low":
            return "low" if score < sg_bgm_low_out else ("high" if score >= sg_bgm_high_in else "talk")
        if score >= sg_bgm_high_in:
            return "high"
        if score < sg_bgm_low_in:
            return "low"
        return "talk"

    def sg_bgm_for_score(score):
        """대화 중 배경음을 호감도에 맞춘다."""
        try:
            sg_bgm_play(sg_bgm_mood_for(score, sg_bgm_now))
        except Exception:
            sg_audio_oops("sg_bgm_for_score")

    def sg_bgm_ending():
        """엔딩: 배경음을 줄여서 엔딩 음이 들리게 한다. 고르기 화면으로 돌아가면 menu 곡이 다시 나온다."""
        global sg_bgm_now, sg_bgm_channel_now, sg_bgm_path_now
        try:
            for channel in sg_bgm_channels:
                renpy.music.stop(channel=channel, fadeout=sg_bgm_ending_fade)
            sg_bgm_now = sg_bgm_channel_now = sg_bgm_path_now = None
        except Exception:
            sg_audio_oops("sg_bgm_ending")

    def sg_audio_on_label(name, abnormal):
        """고르기 화면(label sg_select)에 들어올 때 배경음을 켠다."""
        if name == "sg_select":
            sg_bgm_start()

    config.label_callbacks.append(sg_audio_on_label)

## 게임 설정.
##
## 축제 부스에서 여러 사람이 차례로 하는 게임이라 주 메뉴, 저장, 불러오기, 되감기,
## 넘기기, 빠른 메뉴, 오른쪽 클릭 메뉴를 모두 끈다. 켜면 곧장 캐릭터 고르기 화면이 나온다.


## 기본 ##########################################################################

## 창 제목에 쓰는 게임 이름.
define config.name = _("AI 연애 시뮬레이터: 소개팅")

define gui.show_name = False

define config.version = "1.0"

define gui.about = ""

## 배포판의 실행 파일과 폴더 이름. ASCII만 쓴다.
define build.name = "sogaeting"


## 소리 ##########################################################################

## 효과음은 sg_audio.rpy 가 audio 채널로 직접 낸다. 배경음은 audio/bgm.ogg 를 넣으면 나온다.
## 아래 두 값은 환경설정 화면의 음량 막대를 숨기는 용도로만 남아 있다.
define config.has_sound = False
define config.has_music = False
define config.has_voice = False


## 전환 ##########################################################################

define config.enter_transition = None
define config.exit_transition = None
define config.intra_transition = None
define config.after_load_transition = None
define config.end_game_transition = None

## 대사는 Ren'Py의 say 문이 아니라 sg_screens.rpy의 화면이 그린다.
define config.window = "hide"
define config.window_show_transition = None
define config.window_hide_transition = None


## 환경설정 기본값 ####################################################################

default preferences.text_cps = 0
default preferences.afm_enable = False


## 부스용 잠금 ######################################################################

## 되감기(rollback)를 끈다.
define config.rollback_enabled = False
define config.hard_rollback_limit = 0

## 넘기기를 끈다.
define config.allow_skipping = False

## 저장을 끈다. 판의 상태는 서버 메모리에만 있다.
define config.has_autosave = False
define config.autosave_on_quit = False
define config.autosave_on_choice = False
define config.autosave_on_input = False
define config.has_quicksave = False

## images/ 폴더의 그림을 이름으로 자동 등록하지 않는다. 캐릭터마다 같은 파일 이름
## (neutral.png 등)을 쓰기 때문이다. 그림은 sg_assets.rpy가 경로로 찾는다.
define config.images_directory = None

init python:

    ## 메뉴, 되감기, 넘기기, 창 숨기기, 화면 갈무리 같은 기본 단축키를 지운다.
    ## 직접 말하기 입력 중에 글쇠가 엉뚱한 기능을 부르지 않게 하려는 것이기도 하다.
    ## 전체 화면 전환(F11, Alt+Enter)은 부스 운영자가 쓰도록 남긴다.
    for sg_key in (
        "game_menu", "rollback", "rollforward", "skip", "toggle_skip", "fast_skip",
        "stop_skipping", "toggle_afm", "hide_windows", "screenshot", "help",
        "self_voicing", "clipboard_voicing", "debug_voicing", "extra_voicing",
        "accessibility", "progress_screen", "bubble_editor", "director",
        "save_delete", "save_page_prev", "save_page_next", "performance",
    ):
        config.keymap[sg_key] = [ ]
    config.keymap["toggle_fullscreen"] = [ "alt_K_RETURN", "alt_K_KP_ENTER", "K_F11" ]
    del sg_key

    ## 창 닫기 단추는 묻지 않고 바로 끈다. 저장할 것이 없다.
    config.quit_action = Quit(confirm=False)


## 세이브 디렉토리 ####################################################################
##
## 저장은 하지 않지만 Ren'Py가 환경설정을 이 이름의 폴더에 둔다.

define config.save_directory = "sogaeting-lte-ann"


## 아이콘 #########################################################################

define config.window_icon = "gui/window_icon.png"


## 빌드 구성 #######################################################################

init python:

    build.classify('**.bak', None)
    build.classify('**/.**', None)
    build.classify('**/#**', None)
    build.classify('**/thumbs.db', None)

    ## 그림을 만드는 개발용 스크립트와 시험은 배포판에 넣지 않는다.
    build.classify('game/images/**.py', None)
    build.classify('game/sg_tests.rpy', None)
    build.classify('game/sg_tests.rpyc', None)

    build.documentation('*.html')
    build.documentation('*.txt')

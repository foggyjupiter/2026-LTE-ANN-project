# 소개팅 게임 화면 (Ren'Py)

이 폴더는 Ren'Py 8.5.3으로 만든 게임 화면이다. 대화는 로컬 서버(`sogaeting/server.py`)가 맡고, 게임은 화면만 그린다. 레포 맨 위의 `run_booth` 가 서버와 게임을 한 번에 켠다.

## 윈도우에서 한 줄로 켜기

PowerShell 창에 아래 한 줄을 붙여 넣고 Enter를 누른다. Python이 없으면 winget으로 설치하고, 게임 코드와 Ren'Py SDK를 내 사용자 폴더의 `sogaeting-booth` 폴더에 받은 뒤 켠다. 처음 한 번 Gemini 키를 묻는다(그냥 Enter면 가짜 모델). 켤 때마다 게임 코드를 새로 받는다. 하는 일은 레포 맨 위의 `booth.ps1`에 적혀 있다.

```
irm https://raw.githubusercontent.com/foggyjupiter/2026-LTE-ANN-project/refs/heads/main/booth.ps1 | iex
```

키를 다시 넣으려면 `sogaeting-booth\.env`를 지우고 다시 실행한다. 아래의 준비는 이 방법을 쓰지 않을 때만 한다.

## 준비 (PC마다 한 번)

### 1. Python

Python 3.10 이상을 [python.org](https://www.python.org/downloads/)에서 받아 설치한다. 윈도우에서는 설치 첫 화면 아래쪽의 "Add python.exe to PATH"를 꼭 체크한다.

### 2. Ren'Py SDK 8.5.3

게임을 띄우는 프로그램이다. 설치하지 않고 압축만 풀면 된다. 윈도우 10 이상에서 돈다.

1. <https://www.renpy.org/release/8.5.3> 을 연다.
2. 윈도우용 `renpy-8.5.3-sdk.7z.exe` 를 받는다. (맥은 `.dmg`, 리눅스는 `.tar.bz2`)
3. 받은 파일을 더블클릭하고 Extract를 누른다. `renpy-8.5.3-sdk` 폴더가 생긴다. 안에 `renpy.exe` 가 있다.
4. 그 폴더를 아래 가운데 한 곳에 둔다. 실행기가 위에서부터 차례로 찾는다.
   - 이 레포 폴더 안 (`run_booth.bat` 옆)
   - 이 레포 폴더 바로 옆, 또는 그 옆의 `sdk` 폴더 안
   - 내 사용자 폴더, 그 안의 `sdk`, `Downloads`(다운로드), `Desktop`(바탕 화면), `Documents`(문서)

폴더 이름은 `renpy-8.5.3-sdk` 그대로 두거나 `renpy-sdk` 로 바꾼다. zip으로 받아 풀어도 된다. 풀다가 같은 이름의 폴더가 한 겹 더 생겨도 알아서 찾는다.

다른 곳에 두었다면 환경변수 `RENPY_SDK` 에 그 폴더의 경로를 적는다. 이 값이 있으면 그곳만 본다.

### 3. 모델 키 (실제 모델로 할 때만)

레포 맨 위의 `.env` 에 적는다. 방법은 `sogaeting/README.md` 에 있다. 실행기는 키를 읽지 않는다. 서버가 읽는다.

## 켜기

- 윈도우: `run_booth.bat` 을 더블클릭한다.
- 리눅스, 맥: 터미널에서 `./run_booth.sh` 를 실행한다.

검은 창(터미널)이 먼저 뜨고, 곧 게임이 전체 화면으로 뜬다. 검은 창에는 서버 기록이 찍힌다. **검은 창은 닫지 말고 둔다.** 닫으면 서버가 꺼진다.

끌 때는 게임을 끈다(게임 메뉴의 종료하기, 또는 창 닫기). 서버도 같이 꺼진다. 검은 창에서 Ctrl-C를 눌러도 둘 다 꺼진다.

명령으로 켤 수도 있다. 레포 맨 위 폴더에서 실행한다. 리눅스와 맥에서는 `python` 대신 `python3` 을 쓴다.

```
python run_booth.py               실제 모델, 전체 화면
python run_booth.py --fake        가짜 모델
python run_booth.py --windowed    전체 화면 대신 창으로
python run_booth.py --port 8080   서버 포트를 직접 정하기
```

`run_booth.bat --fake` 처럼 배치 파일이나 셸 스크립트 뒤에 붙여도 된다. 섞어 써도 된다.

켤 때마다 전체 화면으로 시작한다. 켜진 뒤에는 F11로 창과 전체 화면을 오갈 수 있다.

## 가짜 모델로 켜기

키도 인터넷도 없이 화면만 확인할 때 쓴다. 정해진 대사가 나온다.

```
python run_booth.py --fake
```

더블클릭으로 켜고 싶으면 `run_booth.bat` 의 바로 가기를 만들고, 바로 가기 속성의 "대상" 맨 끝에 한 칸 띄고 `--fake` 를 붙인다.

## 그림 넣기

1. 그림을 `art/` 에 둔다. `tools/make_art.py` 로 뽑으면 여기에 생긴다(`tools/README.md`). 직접 그린 그림도 같은 이름으로 넣으면 된다.
2. 실행기를 켠다. 켤 때마다 새 그림과 바뀐 그림만 게임 폴더로 복사한다.

```
art/sprites/<캐릭터 id>/<표정>.png   ->   renpy/game/images/sprites/<캐릭터 id>/<표정>.png
art/bg/<장소>.jpg                   ->   renpy/game/images/bg/<장소>.jpg
```

- 캐릭터 id: `astra`, `gemma`, `sora`, `nova`, `mistral`, `haiku`. 표정: `neutral`, `smile`, `blush`, `pout`, `shock`, `dark`.
- `art/raw/`, `art/preview.png`, `art/manifest.json` 은 복사하지 않는다.
- 그림을 고칠 때는 `art/` 쪽을 고친다. `renpy/game/images/` 쪽을 직접 고치면 다음에 켤 때 `art/` 의 그림으로 덮인다.
- `art/` 에서 지운 그림은 게임 폴더에서 저절로 지워지지 않는다. 직접 지운다.
- 그림이 없는 캐릭터와 장소는 자리표시 그림으로 나온다.

## 문제가 생기면

먼저 검은 창의 글을 본다. `[부스]` 로 시작하는 줄은 실행기가, 나머지는 서버가 찍은 것이다.

| 보이는 것 | 할 일 |
|---|---|
| 검은 창에 `Python was not found` | 준비 1번. 설치할 때 PATH 체크를 빠뜨렸으면 다시 설치한다. |
| `Ren'Py SDK를 찾지 못했습니다` | 준비 2번. 안내에 찍힌 자리에 SDK 폴더를 둔다. |
| `N번 포트는 이미 다른 프로그램이 쓰고 있습니다`, `서버를 켤 수 없습니다` | `--port` 를 빼고 켠다. 빈 포트를 알아서 고른다. 전에 켠 검은 창이 남아 있으면 닫는다. |
| `서버가 20초 안에 답하지 않았습니다` | 그 위에 찍힌 서버의 오류 글을 본다. |
| `[gemini-flash] HTTP 400`, `401` | 키나 모델명이 틀렸다. `sogaeting/README.md` 를 본다. |
| 캐릭터가 말은 안 하고 괄호 속 행동만 한다 | 모델이 답을 못 준 것이다. 레포 맨 위 폴더에서 `python -m sogaeting.check` 를 실행하면 키마다, 모델마다 무엇이 문제인지(하루 한도, 틀린 키, 구글 과부하, 인터넷) 한 줄씩 나온다. 한 줄로 켜기를 쓰면 켤 때마다 알아서 점검한다. |
| 게임이 오류 화면을 띄우거나 바로 꺼진다 | `renpy/traceback.txt`, `renpy/errors.txt`, `renpy/log.txt` 를 본다. |
| 게임이 서버에 연결하지 못한다 | 검은 창이 닫혔거나 서버가 꺼졌다. 게임을 끄고 다시 켠다. |

- 서버 주소와 포트는 검은 창의 `[부스] 서버를 켭니다: http://127.0.0.1:8000` 줄에 찍힌다. 포트를 안 정해 주면 8000부터 비어 있는 번호를 쓴다. 브라우저로 그 주소 뒤에 `/api/status` 를 붙여 열었을 때 글이 나오면 서버는 살아 있다.
- `traceback.txt` 는 게임이 실행 도중 멈춘 까닭, `errors.txt` 는 대본(`.rpy`)의 문법 오류, `log.txt` 는 게임이 켜지면서 남긴 기록이다. 셋 다 `renpy/` 폴더에 생긴다.
- 윈도우에서 Ctrl-C를 누르면 "일괄 작업을 끝내시겠습니까 (Y/N)?" 하고 묻는다. Y를 누른다.

## 실행기가 하는 일

`run_booth.py` 는 표준 라이브러리만 쓴다. 차례는 이렇다.

1. Ren'Py SDK를 찾는다.
2. `art/` 의 그림을 `renpy/game/images/` 로 복사한다.
3. 서버를 켜고(`python -m sogaeting.server --port N`) `/api/status` 가 답할 때까지 기다린다.
4. 게임을 띄운다. 윈도우는 SDK의 `renpy.exe`, 리눅스와 맥은 `renpy.sh` 다. 이때 환경변수를 준다.
   - `SOGAETING_URL`: 서버 주소. `game/sg_config.rpy` 가 읽는다.
   - `SOGAETING_WINDOW`: `fullscreen` 또는 `windowed`. `dev/booth/sg_booth.rpy` 가 읽어서 창 상태를 정한다.
   - `RENPY_SEARCHPATH`: `dev/booth` 폴더. 이 값이 있어야 Ren'Py가 `sg_booth.rpy` 를 읽는다.
   - 프록시 설정은 빼고 준다. 게임은 이 PC 안의 서버하고만 이야기한다.
5. 게임이 꺼지면 서버를 끈다.

게임만 따로 켜려면(Ren'Py 실행기에서 열 때 등) 서버를 먼저 켜 둔다. 게임은 `SOGAETING_URL` 이 없으면 `http://127.0.0.1:8000` 으로 간다.

```
python -m sogaeting.server --fake
```

## 개발용 캡처 도구 (dev/rtest.sh)

화면이 없는 리눅스(컨테이너)에서 게임 화면을 확인하는 도구다. 가상 화면에서 Ren'Py 시험을 돌리고 캡처를 남긴다. `xvfb-run` 이 있어야 한다.

```
python3 -m sogaeting.server --fake --port 8101 &
RENPY_SDK=/path/to/renpy-8.5.3-sdk renpy/dev/rtest.sh sg_flow 8101
```

- 첫째 값은 시험 이름이다. `renpy/game/` 의 `.rpy` 파일에 `testcase <이름>:` 으로 적은 것이다.
  - `sg_flow`: 고르기부터 엔딩까지 한 판 (`game/sg_tests.rpy`)
  - `sg_gimmicks`: 캐릭터 여섯 명의 고유 장치 표시 (`game/sg_tests.rpy`)
  - `sg_fx_demo`: 연출 15가지. 서버가 필요 없다 (`game/sg_fx_demo.rpy`)
  - `sg_stage_demo`: 표정별 동작과 만화 기호. 서버가 필요 없다 (`game/sg_stage_demo.rpy`)
  - `sg_stage_flow`: 실제 흐름에서 동작과 기호가 나오는지 (`game/sg_stage_demo.rpy`)
  - `sg_tests.rpy` 의 나머지 시험(기다림, 오류, 긴 글 등)은 일부러 느리거나 고장 난 임시 서버가 있어야 해서 이 한 줄로는 돌릴 수 없다.
- 시험이 300초 안에 끝나지 않으면 끈다. `RTEST_TIMEOUT=600` 처럼 바꿀 수 있다.
- 둘째 값은 서버 포트다. 안 적으면 8000이다. 서버는 따로 켜 두어야 한다.
- `RENPY_SDK` 는 꼭 적는다. 이 도구는 SDK를 알아서 찾지 않는다.
- 캡처는 `renpy/tests/screenshots/` 에 생긴다. 시험 안에서 `screenshot "이름.png"` 로 찍은 것이다.
- 세이브와 설정은 그때마다 새 임시 폴더를 쓴다. 지난 시험의 설정이 남지 않는다.

같은 환경에서 실행기까지 돌려 보려면 앞에 `xvfb-run` 을 붙인다. 가상 화면 없이 켜면 게임이 화면을 못 찾고 오류 글만 계속 찍는다.

```
xvfb-run -a python3 run_booth.py --fake --windowed
```

## 소리

- 효과음 20개는 코드로 합성해서 만든 것이다(`game/audio/*.ogg`). 다시 만들려면 `python3 renpy/dev/make_sfx.py` (numpy와 ffmpeg가 있어야 한다).
- 배경음은 상황마다 바뀐다(`game/sg_audio.rpy`). 네 곡은 같은 모티프(4마디)를 분위기만 바꿔 편곡한 것이다.

  | 상황 | 파일 | 편곡 |
  |---|---|---|
  | 고르기 화면 | `game/audio/bgm_menu.ogg` | 뮤직박스, 첼레스타, 글로켄슈필, 현악 패드 (112 BPM, 약 2분 48초) |
  | 대화 중, 호감도 보통 | `game/audio/bgm_talk.ogg` | 잔잔한 편곡 (104 BPM, 약 3분) |
  | 대화 중, 호감도 65점 이상 | `game/audio/bgm_high.ogg` | 들뜬 뱀프 편곡 (116 BPM, 약 2분 42초) |
  | 대화 중, 호감도 40점 미만 | `game/audio/bgm_low.ogg` | 단조로 가라앉은 편곡 (79 BPM, 약 3분 52초) |
  | 엔딩 | 배경음을 줄이고 엔딩 음을 들려준다 | |

  - 곡은 1.5초 동안 겹치며 바뀐다. 구간 경계에서 곡이 자꾸 바뀌지 않게 들어갈 때와 나올 때 5점 차이를 둔다(65점에 들뜬 곡으로 들어가면 60점 아래로 내려가야 돌아온다).
  - 상황별 파일이 없으면 `game/audio/bgm.ogg`(또는 `bgm.mp3`) 한 곡을 계속 튼다. 저작권 문제가 없는 음악만 넣는다.
  - 만든 방법(2026-11-14): 사용자의 작곡 도구 레포 `foggyjupiter/fl-studio-plugin`(커밋 a1b87a1)의 arranger. 처음 만든 뮤직박스 곡의 주제 첫 4마디를 모티프(`dev/music/motif.mid`)로 뽑고, 같은 모티프로 분위기마다 `python -m arranger.cli song --genre <dev/music/game_ost_handmade의 절대 경로, .json 빼고> --key C --seed 21 --mood <musicbox|peaceful|vamp> --tempo <112|104|116> --template loop_long --progressions manual --motif dev/music/motif.mid --motif-key C --motif-chords "C | Dm7 | Em | G"` 를 돌렸다. 모티프의 코드를 정하지 않으면 도구가 Am - Dm7 - G로 붙여서 단조처럼 침울하게 들렸다(사용자 확인). low만 `--key Cm --mood sad` 이고 모티프 코드는 도구에 맡겼다. 렌더링은 `python -m tools.render_audio out/<번호>/song.mid --soundfont sgm -o bgm_<상황>.ogg`.
  - 채보 자료는 쓰지 않았다. 이 도구는 기본으로 코드 진행, 반주 음형(오스티나토), 베이스, 드럼 패턴 일부를 원곡 채보에서 가져오는데, 그 비율(`data.share`)을 모두 0으로 바꾼 프로파일(`dev/music/game_ost_handmade.json`)로 만들었다. 멜로디와 편곡은 도구의 규칙과 확률로 새로 만든 것이다.
  - 소리는 SGM-V2.01 사운드폰트와 그 레포에 들어 있는 자체 칩 사운드폰트(`soundfonts/chip_leads.sf2`)만 썼다. 원곡 게임 사운드폰트는 라이선스 때문에 받지 않았다(도구가 고른 게임 음색은 SGM의 같은 번호 악기로 나온다).
  - 곡마다의 MIDI는 `dev/music/bgm_<상황>.mid` 에 있다.
- 음량은 `game/sg_audio.rpy` 맨 위의 `sg_sfx_volume`, `sg_bgm_volume` 으로 맞춘다.
- 소리를 전부 끄려면 환경변수 `SOGAETING_MUTE=1` 을 주고 켠다.
- 이 소리들은 만든 환경에서 귀로 들어 보지 못했다. 부스 PC에서 처음 켤 때 작은 음량으로 들어 보고 맞춘다.

## 꾸밈 그림 다시 만들기

화면에 쓰는 장식 그림은 전부 코드로 만든다. Pillow가 있어야 한다. 그림을 고치려면 스크립트를 고친 뒤 다시 돌린다.

| 그림 | 만드는 스크립트 |
|---|---|
| 연출 (`game/images/fx/`) | `python3 renpy/dev/make_fx_art.py renpy/game/images/fx` |
| 대사창, 선택지, 하트 게이지 등 (`game/images/ui/gal_*.png`) | `renpy/dev/make_ui_art.py` |
| 만화 기호 (`game/images/emote/`) | `renpy/dev/make_emote_art.py` |
| 자리표시 캐릭터와 배경 (`game/images/placeholder/`) | `renpy/game/images/sg_make_images.py` |

## 캐릭터 연기 맞추기

진짜 캐릭터 그림을 넣은 뒤 만화 기호가 머리에서 벗어나 뜨면 `game/sg_stage.rpy` 맨 위의 `sg_stage_head`(얼굴 한가운데 자리)와 `sg_stage_spots` 를 고친다. 배경이 천천히 움직이는 것이 거슬리면 `sg_stage_bg_move = False` 로 끈다.

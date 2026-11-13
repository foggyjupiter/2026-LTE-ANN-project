# 소개팅 (AI 연애 시뮬레이터 2단계)

캐릭터를 고르고 한 판(등장, 답 7번, 엔딩)을 하는 프로그램이다. 화면은 세 가지다: 부스용 Ren'Py 화면, 브라우저 화면, 터미널. 서버와 엔진은 설치할 패키지가 없다. Python 3.10 이상이면 된다.

설계는 `docs/superpowers/specs/2026-11-13-sogaeting-design.md`, 캐릭터는 `docs/characters.md`에 있다.

## 부스에서 켜기 (Ren'Py 화면)

레포 맨 위의 `run_booth.bat`(윈도우)이나 `run_booth.sh`(맥, 리눅스)를 더블클릭한다. 서버와 게임이 함께 켜지고, 게임을 끄면 서버도 꺼진다. Ren'Py SDK 8.5.3이 있어야 한다. 설치와 문제 해결은 `renpy/README.md`에 있다.

```
python run_booth.py           # 실제 모델
python run_booth.py --fake    # 키 없이 가짜 모델로 시연
```

Ren'Py는 화면만 그린다. 대화는 전부 아래의 서버가 맡는다.

## 브라우저로 하기

레포 맨 위 폴더에서 실행한다. 윈도우에서는 `python3` 대신 `python`을 쓴다.

```
python3 -m sogaeting.server --fake   # 키 없이 가짜 모델로 시연
python3 -m sogaeting.server          # 실제 모델
```

터미널에 찍힌 주소(기본 `http://127.0.0.1:8000/`)를 크롬으로 열고 전체 화면(F11)으로 둔다. 끌 때는 터미널에서 Ctrl-C를 누른다.

- 캐릭터를 바로 지정해서 열기: `http://127.0.0.1:8000/?character=haru`
- 다른 포트: `--port 8080`
- 판이 끝난 뒤 결과 읽기(3단계용): `GET /api/session/<판 id>/result`, 또는 `results/` 폴더의 파일
- 3분 동안 입력이 없으면 판을 버리고 첫 화면으로 돌아간다.
- 연출만 따로 보기: `http://127.0.0.1:8000/fx-demo.html`

캐릭터 그림을 `sogaeting/web/assets/characters/<캐릭터 id>/<표정>.png`로 넣으면 픽셀 얼굴 대신 그 그림이 나온다. 표정은 `neutral`, `smile`, `blush`, `pout`, `shock`, `dark`다.

## 터미널로 하기

```
python3 -m sogaeting --fake          # 키 없이 가짜 모델로 시연
python3 -m sogaeting                 # 실제 모델. 캐릭터를 번호로 고른다
python3 -m sogaeting haru            # 캐릭터를 바로 지정
```

캐릭터 id: `giulhee`(아스트라), `oeun`(젬마), `anna`(소라), `relu`(노바), `haru`(미스트랄), `boxhyun`(하이쿠)

진행 중에 1, 2, 3을 치면 선택지를 고르고, 다른 글을 치면 그대로 입력된다. `q`를 치면 곧장 엔딩으로 간다.

## 실제 모델 연결

레포 맨 위 폴더에 `.env` 파일을 만들고 키를 적는다. 이 파일은 `.gitignore`에 들어 있어서 커밋되지 않는다. 키를 코드나 다른 파일에 적지 않는다.

```
GEMINI_API_KEY=여기에_키
GROQ_API_KEY=있으면_적기
```

Gemini 키만 있어도 된다. 호출 순서와 모델명은 `sogaeting/llm.py`의 `PROVIDERS`에 있다. 터미널에 `[gemini-flash-lite] HTTP 400`이나 `401`이 찍히면 모델명이나 키가 틀린 것이다.

- 예비 키: `GEMINI_API_KEY=키1,키2,키3`처럼 쉼표로 이어 적으면 한도(429)가 찬 키를 건너뛰고 다음 키를 쓴다. 한도는 키가 아니라 프로젝트마다 잡히므로 같은 프로젝트의 키를 여러 개 적어도 소용이 없다. 다른 사람 계정에서 만든 키여야 한다.
- 지금 쓰는 모델은 `gemini-3.5-flash-lite`, 예비로 `gemini-3.1-flash-lite`, Groq 키가 있으면 `openai/gpt-oss-120b`다. 2026-11-13에 무료 등급 키로 재 보니 설계의 주 모델 `gemini-3.8-flash`는 15번 중 한 번도 답하지 못해서(과부하) 기본 목록에서 뺐다.
- 유료 키로 `gemini-3.8-flash`를 쓰려면 `.env`에 `GEMINI_MAIN_MODEL=gemini-3.8-flash` 한 줄을 적는다. 그 모델을 맨 먼저 부른다. 적은 뒤에는 아래 시험 도구로 응답 시간을 잰다.
- 한 턴에 10초 안에 답이 없으면 캐릭터별 대체 대사가 나간다. 무료 등급에서는 과부하가 몰리는 시간에 열 턴에 한 번쯤 그랬다.
- **무료 등급에는 하루 한도가 있다.** 2026-11-13에 확인한 값은 모델마다 프로젝트당 하루 500번이다. 한 판에 9-10번 부르므로 키 하나로 주 모델 약 50판, 예비 모델까지 합쳐 약 100판이다. 미국 서부 시간 자정(한국 시간 오후 5시)에 풀린다. 축제 날 판이 더 많을 것 같으면 다른 사람 계정에서 만든 키를 예비 키로 적거나 유료 키를 쓴다. 하루 한도가 찬 키는 30분 동안 건너뛴다.

키가 없거나 인터넷이 끊기면 캐릭터별 대체 대사로 엔딩까지 간다.

### 실제 모델로 한 판씩 돌려 보기

```
python3 -m sogaeting.playtest               # 여섯 캐릭터를 정해 둔 각본으로 한 판씩
python3 -m sogaeting.playtest --only haru   # 한 명만
python3 -m sogaeting.playtest --fake        # 키 없이
```

`results/playtest/` 에 캐릭터별 대화 전문과 요약(응답 시간, 대체 대사 횟수, 답한 모델)이 생긴다. 리허설 때 이것으로 말맛과 속도를 본다.

## 테스트

```
python3 -m unittest discover -s tests -t .
```

네트워크를 쓰지 않는다.

## 구조

| 파일 | 하는 일 |
|---|---|
| `director.py` | 진행자. 한 판의 순서, 뇌절 강도, 씨앗, 연출 거르기, 호감도, 엔딩 등급 |
| `actor.py` | 배우. 모델에 보낼 지시문을 만들고 모델의 답(JSON)을 읽는다. 답에 캐릭터가 모르는 말(AI, 프롬프트), 아슬아슬한 말의 되받기, 대사 예시 베끼기, 너무 긴 겉말(하이쿠)이 있으면 한 번 고쳐 쓰게 한다 |
| `gimmicks.py` | 캐릭터별 고유 장치 여섯 개 |
| `safety.py` | 입력 다듬기(100자), 금지어 검사 |
| `content.py` | `data/`의 JSON을 읽는다 |
| `llm.py` | 모델 호출. 제공자를 차례로 시도한다 |
| `fake_llm.py` | 키 없이 돌려 볼 때 쓰는 가짜 모델 |
| `cli.py` | 터미널 실행기 |
| `server.py` | 로컬 서버. 엔진을 JSON API로 감싸고 `web/`의 파일을 내준다 |
| `playtest.py` | 실제 모델로 정해 둔 각본을 돌려 대화 전문과 응답 시간을 남긴다 |
| `../run_booth.py` | 서버와 Ren'Py 게임을 함께 켠다 |
| `../renpy/` | 부스용 Ren'Py 화면(고르기, 대화, 엔딩, 연출 15가지). 서버를 HTTP로 부른다 |
| `web/app.js`, `style.css`, `index.html` | 화면 세 개(고르기, 대화, 엔딩) |
| `web/fx.js`, `fx.css` | 화면 연출 15가지 |

## 내용 고치기

코드를 건드리지 않고 `sogaeting/data/`의 JSON만 고치면 된다.

- 캐릭터의 말투, 반응, 대체 대사: `data/characters/<id>.json`
- 씨앗 낱말(학교 드립은 여기에 추가): `data/seeds.json`
- 한 판의 길이와 강도: `data/schedule.json`
- 금지어: `data/banned.json`

## 결과

판이 끝나면 `results/` 폴더에 캐릭터, 호감도(0-100), 등급, 엔딩 이름, 칭호, 끝난 시각이 JSON으로 저장된다. 대화 원문은 저장하지 않는다.

## 아직 없는 것

- 캐릭터 그림. Ren'Py 화면에는 자리표시 그림이 나온다. 뽑는 요청문은 `docs/art-prompts-gpt.md`, 넣는 법은 `tools/README.md`에 있다. 배경 8장은 `art/bg/`에 있다.
- 효과음과 BGM.
- 윈도우에서 `run_booth.bat`을 돌려 본 기록, 한글 직접 입력(IME)을 실제 키보드로 쳐 본 기록. 둘 다 부스 PC에서 확인해야 한다.
- Groq 예비 모델과 유료 Gemini 키로 돌려 본 기록.

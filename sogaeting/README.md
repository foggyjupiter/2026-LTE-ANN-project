# 소개팅 (AI 연애 시뮬레이터 2단계)

캐릭터를 고르고 한 판(등장, 답 7번, 엔딩)을 하는 프로그램이다. 브라우저 화면과 터미널, 두 가지로 돌릴 수 있다. 설치할 패키지가 없다. Python 3.10 이상과 크롬이면 된다.

설계는 `docs/superpowers/specs/2026-11-13-sogaeting-design.md`, 캐릭터는 `docs/characters.md`에 있다.

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

캐릭터 id: `giulhee`(기울희), `oeun`(전외운), `anna`(안나), `relu`(한렐루), `haru`(신하루), `boxhyun`(박스현)

진행 중에 1, 2, 3을 치면 선택지를 고르고, 다른 글을 치면 그대로 입력된다. `q`를 치면 곧장 엔딩으로 간다.

## 실제 모델 연결

레포 맨 위 폴더에 `.env` 파일을 만들고 키를 적는다. 이 파일은 `.gitignore`에 들어 있어서 커밋되지 않는다. 키를 코드나 다른 파일에 적지 않는다.

```
GEMINI_API_KEY=여기에_키
GROQ_API_KEY=있으면_적기
```

Gemini 키만 있어도 된다. 호출 순서와 모델명은 `sogaeting/llm.py`의 `PROVIDERS`에 있다. 터미널에 `[gemini-flash] HTTP 400`이나 `401`이 찍히면 모델명이나 키가 틀린 것이다.

키가 없거나 인터넷이 끊기면 캐릭터별 대체 대사로 엔딩까지 간다.

## 테스트

```
python3 -m unittest discover -s tests -t .
```

네트워크를 쓰지 않는다.

## 구조

| 파일 | 하는 일 |
|---|---|
| `director.py` | 진행자. 한 판의 순서, 뇌절 강도, 씨앗, 연출 거르기, 호감도, 엔딩 등급 |
| `actor.py` | 배우. 모델에 보낼 지시문을 만들고 모델의 답(JSON)을 읽는다 |
| `gimmicks.py` | 캐릭터별 고유 장치 여섯 개 |
| `safety.py` | 입력 다듬기(100자), 금지어 검사 |
| `content.py` | `data/`의 JSON을 읽는다 |
| `llm.py` | 모델 호출. 제공자를 차례로 시도한다 |
| `fake_llm.py` | 키 없이 돌려 볼 때 쓰는 가짜 모델 |
| `cli.py` | 터미널 실행기 |
| `server.py` | 로컬 서버. 엔진을 JSON API로 감싸고 `web/`의 파일을 내준다 |
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

- 캐릭터 그림. 지금은 픽셀 얼굴이 대신 나온다.
- 효과음과 BGM.
- 실제 모델로 돌려 본 기록. 키를 넣고 한 판 해 보면서 말맛과 응답 속도를 확인해야 한다.

# 소개팅 엔진 (AI 연애 시뮬레이터 2단계)

화면 없이 터미널에서 한 판(등장, 답 7번, 엔딩)이 돌아가는 엔진이다. 설치할 패키지가 없다. Python 3.10 이상이면 된다.

설계는 `docs/superpowers/specs/2026-11-13-sogaeting-design.md`, 캐릭터는 `docs/characters.md`에 있다.

## 돌려 보기

레포 맨 위 폴더에서 실행한다. 윈도우에서는 `python3` 대신 `python`을 쓴다.

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

## 내용 고치기

코드를 건드리지 않고 `sogaeting/data/`의 JSON만 고치면 된다.

- 캐릭터의 말투, 반응, 대체 대사: `data/characters/<id>.json`
- 씨앗 낱말(학교 드립은 여기에 추가): `data/seeds.json`
- 한 판의 길이와 강도: `data/schedule.json`
- 금지어: `data/banned.json`

## 결과

판이 끝나면 `results/` 폴더에 캐릭터, 호감도(0-100), 등급, 엔딩 이름, 칭호, 끝난 시각이 JSON으로 저장된다. 대화 원문은 저장하지 않는다.

## 아직 없는 것

브라우저 화면과 서버. `Session.start()`, `reply()`, `finish()`가 돌려주는 dict를 그대로 화면에 넘기면 되게 만들어 두었다.

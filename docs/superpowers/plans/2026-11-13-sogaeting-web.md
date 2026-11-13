# 소개팅 서버와 화면 Implementation Plan

> **For agentic workers:** 세 작업자가 동시에 진행한다. 각자 자기 Task의 파일만 만들고 고친다. 다른 Task의 파일은 "Interfaces"에 적힌 대로 존재한다고 믿고 쓴다. git 명령은 실행하지 않는다.

**Goal:** 브라우저에서 캐릭터를 고르고 한 판을 끝까지 할 수 있게 한다.

**Architecture:** 로컬 Python 서버(`sogaeting/server.py`)가 엔진의 `Session`을 JSON API로 감싸고 `sogaeting/web/`의 정적 파일을 내준다. 화면(`app.js`)은 API가 돌려준 dict를 그대로 그린다. 화면 연출(`fx.js`)은 이름 목록을 받아 재생하는 독립 부품이다.

**Tech Stack:** Python 3.10 이상 표준 라이브러리(`http.server`), 빌드 단계 없는 HTML, CSS, JS. 최신 크롬만 지원한다.

**Spec:** `docs/superpowers/specs/2026-11-13-sogaeting-design.md` 5.2, 5.7, 5.9, 5.12절. 엔진의 반환값 모양은 `docs/superpowers/plans/2026-11-13-sogaeting-engine.md` Task 4.

## Global Constraints

- 외부 패키지, CDN, 외부 글꼴 주소, 외부 이미지를 쓰지 않는다. 필요한 것은 전부 `sogaeting/web/` 안에 있다.
- 서버 테스트 실행: `python3 -m unittest discover -s tests -t .` (네트워크 없이, 가짜 모델로)
- 모델이 만든 글은 화면에 넣을 때 반드시 `textContent`나 텍스트 노드로 넣는다. `innerHTML`에 넣지 않는다.
- 문자열과 화면 문구에 물결표(`~`)와 em dash를 쓰지 않는다.
- 화면 문구는 한국어, 참가자 눈높이의 쉬운 말로 쓴다. 단추는 누르면 일어나는 일을 그대로 적는다("보내기", "엔딩 보러 가기", "다시 하기").
- 이모지를 쓰지 않는다. 하트와 표정은 픽셀 도형으로 그린다.

## 디자인 방향 (세 Task 공통, 이대로 따른다)

**개념: 모눈종이 위의 픽셀 미연시.** 과학고 학생의 모눈 공책에 그린 연애 시뮬레이션이다. 바탕은 모눈종이, 글자는 픽셀 글꼴, 점수는 빨간 펜 채점 표시, 강조는 형광펜이다. 화면 구성은 누구나 알아보는 정통 미연시(가운데 인물, 아래 대사창)를 그대로 쓴다.

| 이름 | 값 | 쓰는 곳 |
|---|---|---|
| `--paper` | `#F4F7FB` | 바탕 |
| `--grid` | `#C7D3E8` | 모눈 선 |
| `--ink` | `#1B2559` | 글자, 테두리 (교복 남색) |
| `--red` | `#E23B4E` | 호감도, 팝업, 하트 (빨간 펜) |
| `--marker` | `#FFE65A` | 형광펜, 고른 것 |
| `--accent` | 캐릭터 대표색 | 이름표, 초상 테두리. `#stage`에 인라인으로 넣는다 |
| `--cell` | `22px` | 모눈 한 칸. 간격과 크기는 이 값의 배수로 잡는다 |

- 글꼴: `Galmuri11`(본문과 대사, 22px), `Galmuri11` Bold(숫자와 단추), `Galmuri14`(이름표와 제목, 28px 또는 42px). 파일은 `sogaeting/web/fonts/`에 있다: `Galmuri11.woff2`, `Galmuri11-Bold.woff2`, `Galmuri14.woff2`. 픽셀 글꼴이므로 크기는 11px 또는 14px의 정수배만 쓰고 `font-smooth`류 보정을 끈다.
- 모양: 테두리는 2px 또는 4px의 `--ink` 실선. 둥근 모서리, 부드러운 그림자, 그라데이션을 쓰지 않는다. 그림자가 필요하면 4px 어긋난 단색 사각형(픽셀 그림자)을 쓴다.
- 정렬: 내용은 가운데 놓인 폭 960px 기둥 안에서 왼쪽 정렬.
- 움직임: 참가자의 행동에 답하는 것(대사가 타자 치듯 나옴, 팝업, 곡선이 한 칸 늘어남)과 모델이 고른 연출만 움직인다. 단추에 마우스를 올렸을 때의 꾸밈, 화면 진입 애니메이션은 넣지 않는다. 움직임은 `steps()`로 끊어서 픽셀 느낌을 낸다.
- 힘을 주는 곳은 한 군데다: 호감도. 빨간 펜 팝업과 답마다 한 칸씩 그려지는 호감도 곡선. 나머지는 조용하게 둔다.

```
┌────────────────────────────────────────────────────────────────┐
│ 답 3/7                                호감도 64   곡선 ／＼＿／ │
│                                                                │
│                    ┌──────────┐                   +140         │
│                    │ 픽셀 얼굴 │                   사유: 숨소리 │
│                    └──────────┘                                │
│  지문 한 줄                                                    │
│  ┌ ┄ 속마음 ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┄ ┐       │
│  ┌[기울희]──────────────────────────────────────────────┐      │
│  │ 대사                                                  │      │
│  └───────────────────────────────────────────────────────┘     │
│  [선택지 1]  [선택지 2]  [선택지 3]                             │
│  [직접 입력                                    ] [보내기]       │
│                                              엔딩 보러 가기     │
└────────────────────────────────────────────────────────────────┘
```

## File Structure

| 파일 | 책임 | 담당 |
|---|---|---|
| `sogaeting/server.py`, `tests/test_server.py` | JSON API, 정적 파일, 판 보관 | Task W1 |
| `sogaeting/web/index.html`, `style.css`, `app.js` | 화면 세 개(고르기, 대화, 엔딩)와 그리기 | Task W2 |
| `sogaeting/web/fx.js`, `fx.css`, `fx-demo.html` | 연출 15가지 | Task W3 |

이미 있는 것: `sogaeting/web/fonts/*.woff2`, `sogaeting/web/assets/characters/README.md`, 엔진 전체.

---

### Task W1: 서버

**Files:** Create `sogaeting/server.py`, `tests/test_server.py`

**Interfaces (Consumes):** `sogaeting.director.Session`, `save_result`; `sogaeting.content.list_character_ids`, `load_character`; `sogaeting.fake_llm.fake_llm`; `sogaeting.llm.load_dotenv`, `status_line`, `stats`.

**Interfaces (Produces):**

```python
# sogaeting/server.py
def make_server(host="127.0.0.1", port=8000, *, llm=None, results_dir="results",
                web_dir=None, session_ttl=900) -> http.server.ThreadingHTTPServer
def main(argv=None) -> int      # python3 -m sogaeting.server [--fake] [--host H] [--port N] [--results DIR]
```

`llm`을 안 주면 엔진 기본값(실제 모델)을 쓴다. `web_dir` 기본값은 `sogaeting/web`. 테스트는 `port=0`으로 띄우고 `server.server_address`에서 포트를 읽는다.

**API (전부 JSON, UTF-8):**

| 요청 | 성공 응답 |
|---|---|
| `GET /api/characters` | `200` `[{"id", "name", "attribute", "motif", "color", "intro"}]`. `motif`는 모티브 이름, `intro`는 캐릭터의 `attitude` 첫 문장. 순서는 `giulhee, oeun, anna, relu, haru, boxhyun` |
| `POST /api/session` 본문 `{"character": "haru"}` | `201` `{"session_id": str, "character": {"id", "name", "attribute", "motif", "color"}, "turn": {...}}`. `turn`은 `Session.start()`의 dict |
| `POST /api/session/<id>/reply` 본문 `{"text": "..."}` | `200` `Session.reply()`의 dict |
| `POST /api/session/<id>/finish` | `200` `{"ending": {...}, "result": {...}}`. 처음 부를 때 `save_result`로 한 번만 저장한다. 다시 불러도 같은 값을 돌려주고 또 저장하지 않는다 |
| `GET /api/session/<id>/result` | `200` `Session.result()`의 dict |
| `GET /api/status` | `200` `{"calls", "failures", "last_provider", "sessions"}` |

**오류 응답:** 본문은 `{"error": "한국어 설명"}`.

- `400`: JSON이 아님, 본문이 dict가 아님, `character`나 `text`가 없거나 문자열이 아님, 빈 입력(`ValueError`), 본문이 10KB를 넘음
- `404`: 모르는 캐릭터, 모르는 판, 모르는 경로, 아직 끝나지 않은 판의 `result`
- `409`: 이미 끝난 판에 `reply` (`RuntimeError`)
- `405`: 맞는 경로에 틀린 메서드

**정적 파일:** `GET /`는 `index.html`. 그 밖의 `GET`은 `web_dir` 아래의 파일을 내준다(`/app.js`, `/fonts/Galmuri11.woff2`, `/assets/...`). `web_dir` 밖으로 나가는 경로(`..`, 절대 경로, 인코딩된 `%2e%2e`)는 `404`. 확장자별 `Content-Type`: html, css, js, json, png, jpg, svg, woff2, mp3, ogg. 쿼리 문자열(`/?character=haru`)은 무시하고 경로만 본다. 정적 파일과 API 모두 `Cache-Control: no-store`.

**판 보관:** 판 id는 `secrets.token_urlsafe(8)`. 판마다 잠금을 두어 같은 판의 요청이 겹치면 차례로 처리한다. 새 판을 만들 때마다 마지막 요청으로부터 `session_ttl`초가 지난 판을 지운다. 지워진 판은 `404`.

**`main`:** `load_dotenv()`를 부르고 서버를 띄운 뒤 접속 주소를 찍는다. `--fake`면 가짜 모델. 모델을 부른 요청이 끝날 때마다 `status_line()`을 찍는다. Ctrl-C로 조용히 끝난다. 기본 요청 로그(`log_message`)는 끈다.

**Tests (`tests/test_server.py`):** `fake_llm`과 임시 결과 폴더로 서버를 띄우고 `urllib`로 요청한다.

- 캐릭터 목록이 여섯 개이고 순서와 키가 맞다.
- 한 판 전체: 판 만들기(201) → `reply` 7번 → `finish`. 마지막 `reply`의 `finale`이 참이다. 결과 폴더에 파일이 정확히 하나 생기고, `finish`를 다시 불러도 하나다. `result`가 `finish`의 `result`와 같다.
- 오류: 모르는 캐릭터 404, 모르는 판 404, 빈 `text` 400, `text`가 숫자 400, JSON이 아닌 본문 400, 끝난 판에 `reply` 409, 끝나지 않은 판의 `result` 404, `GET /api/session` 405, 10KB 넘는 본문 400.
- 정적 파일: `/`가 200이고 `text/html`. `/fonts/Galmuri11.woff2`가 200이고 `font/woff2`. `/../server.py`와 `/%2e%2e/server.py`가 404. `/?character=haru`가 200.
- 판 정리: `session_ttl=0`으로 띄우면 새 판을 만든 뒤 앞 판이 404가 된다.
- 응답의 한글이 깨지지 않는다(`ensure_ascii=False`, `charset=utf-8`).
- `/`와 정적 파일 테스트는 `index.html`이 아직 없을 수 있으므로 임시 `web_dir`에 작은 파일을 만들어 넣고 검사한다.

---

### Task W2: 화면 뼈대

**Files:** Create `sogaeting/web/index.html`, `sogaeting/web/style.css`, `sogaeting/web/app.js`

**Interfaces (Consumes):** Task W1의 API. Task W3의 `window.Fx.play(names, opts)`, `window.Fx.clear()`. `turn`과 `ending` dict의 모양은 엔진 계획서 Task 4.

**Interfaces (Produces, W3이 기대는 것):**

- `index.html`은 `<head>`에서 `style.css`, `fx.css` 순으로, `<body>` 끝에서 `fx.js`, `app.js` 순으로 불러온다.
- 대화 화면 전체를 감싸는 `<div id="stage">` (`position: relative; overflow: hidden`). 그 안의 마지막 자식으로 빈 `<div id="fx-layer"></div>`. 초상은 `id="portrait"`.
- `:root`에 위 표의 CSS 변수와 `@font-face` 세 개를 정의한다.
- `fx-`로 시작하는 class와 id는 쓰지 않는다 (W3의 것).

**화면 세 개.** 한 번에 하나만 보인다.

1. **고르기** (`#screen-select`): 제목 "전학생 환영 소개팅", 한 줄 안내 "오늘 전학 온 당신, 누구와 마주 앉을까요?", 캐릭터 카드 여섯 장(픽셀 얼굴, 이름, 속성, 모티브, `intro`). 카드를 누르면 그 캐릭터로 판을 시작한다. 아래에 "실명과 학번은 적지 마세요." 주소에 `?character=<id>`가 있으면 이 화면을 건너뛴다.
2. **대화** (`#screen-play`, 안에 `#stage`): 위 스케치대로.
3. **엔딩** (`#screen-ending`): 성적표 모양의 카드 한 장. 캐릭터 이름, 등급(빨간 도장 모양), 엔딩 이름(가장 큰 글자), 후일담, 칭호, 최종 호감도, 호감도 곡선, "이번 판의 명대사". 판 중에 속마음이 가려져 나온 적이 있으면 "가려졌던 속마음" 아래에 `ending.inners`를 순서대로 보여 준다. 단추: "다시 하기"(같은 캐릭터), "다른 캐릭터 고르기".

**답 하나를 그리는 규칙** (`turn` dict):

- `narration`이 있으면 지문 줄에, 없으면 그 줄을 숨긴다.
- 대사: `extras.say_marked`가 있으면 그것을 쓰고 `" [출처 필요]"`를 빨간 위첨자 딱지로 그린다. `extras.highlights`가 있으면 대사 안의 그 부분들에 형광펜을 칠한다. 대사는 타자 치듯 한 글자씩 나오고(초당 약 40자), 대사창을 누르거나 Enter를 누르면 한 번에 다 나온다.
- 속마음: `extras.inner_masked`가 있으면 그것을, 없으면 `inner`를 쓴다. 비어 있으면 숨긴다.
- `heard`가 있으면 대사창 위에 "들은 말: ..."로 보여 준다.
- 표정: `face`에 맞는 초상. `assets/characters/<id>/<face>.png`가 있으면 그 그림, 없으면 픽셀 얼굴(캐릭터 색 바탕, 표정 여섯 가지를 사각형으로 그린 SVG).
- 호감도: 숫자와 곡선(가로 0-7, 세로 0-100, 시작점 50). `popup`이 `null`이 아니면 빨간 펜 팝업으로 `popup`과 "사유: `reason`"을 띄우고 다음 답이 올 때까지 둔다. `reason`이 비어 있으면 사유 줄을 뺀다. `notes`는 팝업 아래에 한 줄씩.
- `fallback`이 참이면 대사를 지문처럼(기울임 없이, 옅은 색) 그리고 팝업을 띄우지 않는다.
- 선택지: `choices`가 3개면 단추 세 개, 아니면 숨긴다. 단추를 누르면 그 글을 입력으로 보낸다. 입력창이 비어 있을 때 숫자 키 1, 2, 3으로도 고른다.
- 입력창: 100자 제한, Enter로 보내기. 빈 글은 보내지 않는다.
- 진행: "답 3/7". 등장 때는 "등장".
- `finale`이 참이면 선택지와 입력창 대신 "엔딩 보기" 단추 하나를 보여 준다. "엔딩 보러 가기"는 판 중 언제나 눌러서 곧장 `finish`를 부른다.
- 답을 받을 때마다 `Fx.play(turn.fx, {narration: turn.narration})`. 화면을 바꿀 때 `Fx.clear()`.
- 기다리는 동안: 대사창에 "…"이 깜빡이고 입력과 단추가 잠긴다.
- 요청이 실패하면 대사창 아래에 "서버와 연결이 끊겼습니다. 서버를 켠 터미널을 확인하세요."와 "다시 보내기" 단추. 400 오류는 서버가 준 `error` 글을 보여 준다.
- 3분 동안 아무 입력(키, 누르기)이 없으면 판을 버리고 고르기 화면으로 돌아간다. 고르기 화면에서는 이 시계를 돌리지 않는다.

**확인:** 서버(`python3 -m sogaeting.server --fake --port 8765`)를 띄우고 크롬으로 세 화면을 직접 캡처해서 본다. 1366×768에서 스크롤 없이 한 화면에 들어와야 한다.

---

### Task W3: 연출

**Files:** Create `sogaeting/web/fx.js`, `sogaeting/web/fx.css`, `sogaeting/web/fx-demo.html`

**Interfaces (Consumes, W2가 만드는 것):** `#stage`(대화 화면 전체, `position: relative; overflow: hidden`), 그 안의 `#fx-layer`(빈 div), `#portrait`(초상). CSS 변수 `--ink`, `--red`, `--marker`, `--paper`, `--accent`, `--cell`과 글꼴 `Galmuri11`, `Galmuri14`. 변수는 `var(--ink, #1B2559)`처럼 기본값과 함께 쓴다.

**Interfaces (Produces):**

```js
window.Fx = {
  NAMES: ["꽃잎", "반짝이", "집중선", "줌인", "자막", "하트",
          "흔들림", "암전", "붉은 화면", "흑백", "비", "번개", "스포트라이트", "화면 깨짐", "가짜 오류창"],
  play(names, opts) {},   // names: 문자열 배열. opts: {narration?: string}. 모르는 이름은 무시
  clear() {},             // 재생 중인 연출을 전부 즉시 걷는다
};
```

- `fx.css`가 `#fx-layer`의 배치(`position: absolute; inset: 0; pointer-events: none; z-index`)를 정한다.
- `fx.js`는 `#fx-layer` 안에만 요소를 만들고, `#stage`와 `#portrait`에는 `fx-`로 시작하는 class만 붙였다 뗀다. 다른 요소는 건드리지 않는다.
- 모든 연출은 스스로 끝나고 뒤를 치운다. 가벼운 연출은 3초 이내, 센 연출은 4초 이내. `play`를 다시 부르면 앞의 것을 먼저 `clear`한다.
- `#stage`, `#fx-layer`, `#portrait` 가운데 없는 것이 있어도 오류를 내지 않는다.
- `prefers-reduced-motion: reduce`에서는 움직임 없이 정지 화면으로 짧게 보여 준다.
- 모든 class, id, keyframes 이름은 `fx-`로 시작한다.

**연출 15가지** (모눈종이와 픽셀 느낌으로, `steps()`로 끊어서):

| 이름 | 모습 |
|---|---|
| 꽃잎 | 분홍 픽셀 꽃잎이 위에서 비스듬히 떨어진다 |
| 반짝이 | 십자 모양 픽셀 반짝임이 여기저기 깜빡인다 |
| 집중선 | 화면 가장자리에서 초상 쪽으로 모이는 남색 집중선 |
| 줌인 | 초상이 두 단계로 확 커졌다가 돌아온다 |
| 자막 | `narration`이 화면 한가운데 형광펜 띠 위에 큰 글자(`Galmuri14`)로 뜬다. `narration`이 없으면 아무 일도 없다 |
| 하트 | 빨간 픽셀 하트가 아래에서 떠오른다 |
| 흔들림 | `#stage` 전체가 좌우로 덜컹거린다 |
| 암전 | 화면이 단계적으로 어두워졌다가 돌아온다 |
| 붉은 화면 | 붉은 막이 덮이고 맥박처럼 두 번 뛴다 |
| 흑백 | `#stage`가 흑백이 되었다가 돌아온다 |
| 비 | 비스듬한 픽셀 빗줄기 |
| 번개 | 화면이 두 번 번쩍이고 픽셀 번개 한 줄기 |
| 스포트라이트 | 초상 둘레만 남기고 어두워진다 |
| 화면 깨짐 | 화면이 가로 조각으로 어긋나고 색이 갈라진다 |
| 가짜 오류창 | 옛 운영체제 모양의 오류창. 제목 "오류", 본문은 `narration`(없으면 "두근거림이 허용 범위를 넘었습니다"), "확인" 단추. 누르거나 4초가 지나면 닫힌다. 이 창만 `pointer-events: auto` |

**`fx-demo.html`:** `#stage`, `#portrait`, `#fx-layer`를 흉내 낸 작은 무대와 연출 이름 단추 15개, "전부 걷기" 단추, `narration` 입력칸. 서버 없이 파일을 열어도 동작한다(글꼴 경로는 상대 경로).

**확인:** 크롬으로 `fx-demo.html`을 열어 연출마다 재생 도중의 화면을 캡처해서 본다. 15개 모두 눈에 보이고 서로 구분되는지, 끝난 뒤 `#fx-layer`가 비고 `#stage`와 `#portrait`에 `fx-` class가 남지 않는지 확인한다.

---

## Self-Review

- 설계 문서 5.2절 화면은 W2, 5.7절 연출은 W3, 5.12절(주소로 캐릭터 넘겨받기, 결과 읽기, 여러 판 동시에)은 W1과 W2, 5.3절의 무입력 3분 초기화는 W2.
- 5.9절 고유 장치의 화면 표시: `say_marked`, `highlights`, `inner_masked`, `heard`, `notes`, `popup`은 W2의 "답 하나를 그리는 규칙"에 있다. 박스현의 엔딩 속마음 공개는 엔딩 화면에 있다.
- 효과음과 BGM은 이번 범위에 없다.

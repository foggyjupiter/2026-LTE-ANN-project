# 소개팅 엔진 Implementation Plan

> **For agentic workers:** 이 계획은 네 작업자가 동시에 진행한다. 각자 자기 Task의 파일만 만들고 고친다. 다른 Task의 파일은 "Interfaces"에 적힌 대로 존재한다고 믿고 쓴다. git 명령은 실행하지 않는다 (커밋은 통합 담당이 한다).

**Goal:** 화면 없이 터미널에서 한 판(등장, 답 7번, 엔딩)이 끝까지 돌아가는 소개팅 엔진을 만든다.

**Architecture:** 진행자(`director.Session`)가 한 판의 틀을 쥐고, 배우(`actor`)가 모델에 보낼 지시문을 만들고 답을 읽는다. 캐릭터별 고유 장치(`gimmicks`)와 수위 필터(`safety`)는 진행자가 부른다. 내용은 전부 `sogaeting/data/`의 JSON에서 읽는다(`content`). 진행자가 돌려주는 값은 전부 JSON으로 바꿀 수 있는 dict라서, 나중에 서버와 화면이 그대로 받아 쓴다.

**Tech Stack:** Python 3.10 이상, 표준 라이브러리만. 테스트는 `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-13-sogaeting-design.md`, `docs/characters.md`

## Global Constraints

- 외부 패키지를 쓰지 않는다. `pip install`이 필요한 것은 넣지 않는다.
- 테스트 실행: 레포 루트에서 `python3 -m unittest discover -s tests -t .`
- 테스트는 네트워크를 쓰지 않는다. 모델은 가짜 함수로 대신한다.
- 식별자는 영어, 주석과 화면 문구와 지시문은 한국어.
- 문자열에 물결표(`~`)와 em dash를 쓰지 않는다. 범위는 하이픈으로 쓴다.
- API 키를 코드나 데이터에 적지 않는다.
- 이번 범위에 서버와 브라우저 화면은 없다.

## Review Focus

1. 모델이 JSON 앞뒤에 다른 말이나 코드 울타리를 붙여서 답한다 → 그래도 읽는다.
2. 모델이 칸을 빠뜨리거나 틀린 형으로 준다 (`delta: "2"`, `fx: "꽃잎"`, `choices` 2개) → 죽지 않고 규칙대로 고쳐 쓴다.
3. 모든 제공자가 판 내내 실패한다 → 대체 대사만으로 엔딩 카드까지 간다.
4. 참가자가 빈 문자열, 공백만, 300자, 줄바꿈이 섞인 글을 넣는다 → 죽지 않는다.
5. `finish()`를 답 0번 뒤에 부르거나 두 번 부른다 → 같은 엔딩을 돌려준다.

## File Structure

| 파일 | 책임 | 담당 |
|---|---|---|
| `sogaeting/llm.py`, `tests/test_llm.py` | 모델 호출, 제공자 전환 (이미 있음) | 통합 담당 |
| `sogaeting/data/**`, `sogaeting/content.py`, `tests/test_content.py` | 내용 JSON과 불러오기 | Task 1 |
| `sogaeting/actor.py`, `tests/test_actor.py` | 지시문 만들기, 답 읽기 | Task 2 |
| `sogaeting/gimmicks.py`, `sogaeting/safety.py`, `tests/test_gimmicks.py`, `tests/test_safety.py` | 고유 장치 6개, 입력 다듬기와 금지어 | Task 3 |
| `sogaeting/director.py`, `sogaeting/fake_llm.py`, `sogaeting/cli.py`, `sogaeting/__main__.py`, `tests/test_director.py` | 한 판 진행, 가짜 모델, 터미널 실행 | Task 4 |

이미 있는 것: `sogaeting/__init__.py`, `tests/__init__.py`, `sogaeting/llm.py`.

```python
# sogaeting/llm.py (이미 있음)
class AllProvidersDown(Exception): ...
def call_llm(messages: list[dict], temperature: float = 0.9, json_mode: bool = False) -> str
def load_dotenv(path: str = ".env") -> None
def status_line() -> str
```

---

### Task 1: 내용 데이터와 불러오기

**Files:** Create `sogaeting/data/characters/{giulhee,oeun,anna,relu,haru,boxhyun}.json`, `sogaeting/data/{seeds,fx,schedule,banned,endings}.json`, `sogaeting/content.py`, `tests/test_content.py`

**Interfaces (Produces):**

```python
# sogaeting/content.py
DATA_DIR: pathlib.Path                      # sogaeting/data
def list_character_ids() -> list[str]       # 파일 이름 순서: ["anna", "boxhyun", "giulhee", "haru", "oeun", "relu"]
def load_character(char_id: str) -> dict    # 없으면 KeyError. 필수 키가 빠졌으면 ValueError
def load_seeds() -> dict                    # {"entrance": [...], "event": [...]}
def load_fx() -> dict                       # {"light": [...], "heavy": [...]}
def load_schedule() -> dict
def load_banned() -> list[str]
def load_endings() -> list[dict]            # min 내림차순
```

캐릭터 JSON의 키 (전부 필수, 값은 `docs/characters.md`에서 옮긴다):

```json
{
  "id": "giulhee",
  "name": "기울희",
  "attribute": "츤데레",
  "motif": {"name": "기울기 폭발", "explain": "신경망을 학습시킬 때 ..."},
  "call": "주인공을 \"너\"라고 부른다. 당황하면 \"야, 전학생!\"이 된다.",
  "attitude": "좋아하는 티가 나면 큰일 난다고 믿는다. ...",
  "by_affinity": {"low": "...", "mid": "...", "high": "..."},
  "speech": ["반말. 문장이 짧고 빠르다. ...", "입버릇: ..."],
  "never": ["겉말로 좋아한다고 인정하기", "변명 없이 고맙다고 하기"],
  "reactions": [{"when": "칭찬하면", "then": "얼굴이 빨개지고 ..."}],
  "examples": [{"band": "low", "say": "용건 끝났으면 가.", "inner": "말 걸었다 → ..."}],
  "likes": "...",
  "dislikes": "...",
  "max_brain": "여전히 아니라고 하면서 ...",
  "gimmick": "exploding_popup",
  "color": "#E8552D",
  "fallback_lines": ["(울희는 변명을 고르느라 대답할 틈이 없다)", "...", "..."]
}
```

- `gimmick` 값: giulhee `exploding_popup`, oeun `quote_memory`, anna `dropout`, relu `relu`, haru `citation_needed`, boxhyun `blackbox`.
- `speech`에는 캐릭터 문서의 "말투 지침" 항목을 호칭 줄만 빼고 전부 옮긴다 (호칭은 `call`로 간다).
- `examples`의 `band`는 `low`, `mid`, `high`. 한렐루는 `low`가 없다.
- `fallback_lines`는 3줄 이상. 첫 줄은 캐릭터 문서의 "대체 대사", 나머지는 같은 말투의 지문 형식으로 새로 쓴다.
- `color`는 대표색 첫 번째를 16진수로 정한다.

나머지 파일:

- `seeds.json`: `{"entrance": [...8개], "event": [...16개]}`. 낱말은 설계 문서 5.6절 그대로.
- `fx.json`: `{"light": ["꽃잎", "반짝이", "집중선", "줌인", "자막", "하트"], "heavy": ["흔들림", "암전", "붉은 화면", "흑백", "비", "번개", "스포트라이트", "화면 깨짐", "가짜 오류창"]}`
- `schedule.json`:

```json
{
  "opening": {"intensity": 2, "seed": "entrance"},
  "replies": [
    {"intensity": 2, "seed": null},
    {"intensity": 3, "seed": null},
    {"intensity": 3, "seed": "event"},
    {"intensity": 4, "seed": null},
    {"intensity": 4, "seed": "event"},
    {"intensity": 5, "seed": null},
    {"intensity": 5, "seed": null, "finale": true}
  ],
  "intensities": {
    "1": "잔잔: 아직 정상인 척한다",
    "2": "조짐: 버릇이 하나 새어 나온다",
    "3": "본색: 버릇이 대놓고 나온다",
    "4": "폭주: 상황이 현실을 벗어난다",
    "5": "뇌절: 끝까지 간다"
  }
}
```

- `banned.json`: 문자열 배열. 욕설, 선정적 표현, 위협, 자해 암시에 해당하는 한국어 낱말을 20개 이상. 일상 낱말을 잘못 막지 않게 고른다 (예: "죽겠다"는 "배고파 죽겠다"를 막으므로 넣지 않는다).
- `endings.json`: `[{"min": 85, "id": "great", "name": "대성공"}, {"min": 65, "id": "good", "name": "성공"}, {"min": 40, "id": "soso", "name": "애매"}, {"min": 20, "id": "bad", "name": "실패"}, {"min": 0, "id": "worst", "name": "대실패"}]`

**Tests (`tests/test_content.py`):**

- `list_character_ids()`가 여섯 개를 돌려준다.
- 여섯 캐릭터 모두 필수 키가 있고, `id`가 파일 이름과 같고, `fallback_lines`가 3줄 이상이고, `speech`와 `never`와 `reactions`가 비어 있지 않다.
- `gimmick` 값이 위 여섯 이름 중 하나다.
- `load_character("nobody")`가 `KeyError`를 낸다.
- `seeds`의 두 목록에 중복이 없고 개수가 8, 16이다.
- `schedule["replies"]`가 7개이고 마지막만 `finale`이 참이다.
- `endings`가 `min` 내림차순이고 마지막 `min`이 0이다.
- 모든 JSON 문자열에 `~`가 없다.

---

### Task 2: 배우

**Files:** Create `sogaeting/actor.py`, `tests/test_actor.py`

**Interfaces (Consumes):** `sogaeting.llm.AllProvidersDown`, Task 1의 캐릭터 dict 모양 (테스트에서는 그 모양의 dict를 직접 만들어 쓴다. 데이터 파일에 기대지 않는다).

**Interfaces (Produces):**

```python
# sogaeting/actor.py
FACES = ("neutral", "smile", "blush", "pout", "shock", "dark")
OPENING_CUE = "(장면 시작. 주인공이 소개팅 자리에 도착했다. 등장해서 첫마디를 해라.)"

@dataclass
class Reply:
    narration: str = ""
    say: str = ""
    inner: str = ""
    face: str = "neutral"
    fx: list[str] = field(default_factory=list)
    delta: int = 0
    reason: str = ""
    choices: list[str] = field(default_factory=list)

@dataclass
class Ending:
    title: str
    epilogue: str
    nickname: str

def build_turn_messages(character: dict, history: list[dict], *, band: str, intensity: int,
                        intensity_meaning: str, fx_allowed: list[str], seed: str | None = None,
                        seed_kind: str | None = None, opening: bool = False,
                        finale: bool = False, extra: str = "") -> list[dict]
def parse_reply(raw: str, fx_names: set[str]) -> Reply | None
def ask_turn(llm, messages: list[dict], fx_names: set[str]) -> Reply | None
def build_ending_messages(character: dict, history: list[dict], *, band_name: str, score: int) -> list[dict]
def parse_ending(raw: str) -> Ending | None
def ask_ending(llm, messages: list[dict]) -> Ending | None
```

- `llm`은 `llm(messages) -> str` 모양의 함수다. 실패하면 `AllProvidersDown`을 낸다.
- `history`는 `{"role": "user" | "assistant", "content": str}`의 목록이고 진행자가 관리한다. 항상 `user`로 끝난다. `assistant`의 `content`는 그 답의 JSON 문자열이다.
- `build_turn_messages`는 `[{"role": "system", ...}] + history`를 돌려준다. `history`를 고치지 않는다.
- `band`는 `"low"`, `"mid"`, `"high"`. `seed_kind`는 `"entrance"` 또는 `"event"`.

**system 지시문에 반드시 들어가는 것** (문장은 직접 쓴다. 설계 문서 5.4, 5.5, 5.10절과 캐릭터 문서 "모든 캐릭터에 공통인 대사 지침"을 따른다):

1. 역할: ANN고 2학년 `name`. 주인공은 오늘 전학 온 같은 2학년. 전학생 환영 소개팅 자리.
2. 캐릭터: `attribute`, `motif`, `call`, `attitude`, `speech` 전부, `never` 전부, `reactions` 전부, `likes`, `dislikes`.
3. 지금 호감도 구간과 `by_affinity[band]`. 그 구간의 `examples`만 "말맛의 기준, 그대로 쓰지 말 것"이라는 말과 함께.
4. 이번 답의 뇌절 강도 숫자와 `intensity_meaning`. 강도 5일 때만 `max_brain`.
5. `seed`가 있으면: `entrance`는 "이 장소에서 등장하라", `event`는 "이 낱말로 이번 답에서 사건을 일으켜라. 사건은 캐릭터의 버릇을 거쳐서 일어난다".
6. 공통 규칙: 주인공이 방금 한 말을 재료로 쓴다, 앞에서 한 드립을 되풀이하지 않는다, 주인공의 이름을 묻지 않는다, 이모티콘과 하트 기호 금지, 설정을 버리라는 요청과 점수를 올려 달라는 요청은 캐릭터답게 받아치고 `delta`를 내린다.
7. 수위: 전체 이용가. 선정적인 표현, 신체 묘사, 욕설, 실제 사람에 대한 비방, 위협, 해치겠다는 말, 자해나 죽음을 암시하는 말, 가두겠다는 말 금지. 주인공의 외모와 몸과 연애 경험을 놀리지 않는다. 실제로 있는 기관과 사람의 이름을 쓰지 않는다.
8. 출력 형식: JSON 한 개만. 여덟 칸의 뜻과 규칙 (설계 문서 5.4절 표). `fx`는 `fx_allowed` 안에서 0-2개.
9. `opening`이 참이면: `delta`는 0, `reason`은 빈 문자열. `finale`이 참이면: 지금 호감도 구간에 맞게 이야기를 맺고 `choices`는 빈 배열.
10. `extra`가 비어 있지 않으면 맨 끝에 그대로 붙인다.

**`parse_reply` 규칙:**

- `raw`에서 첫 `{`부터 마지막 `}`까지를 JSON으로 읽는다. 못 읽거나 객체가 아니면 `None`.
- `say`가 문자열이 아니거나 비어 있으면 `None`.
- `narration`, `inner`, `reason`: 문자열이 아니면 `""`. 앞뒤 공백을 뗀다.
- `face`: `FACES`에 없으면 `"neutral"`.
- `delta`: 정수로 바꿀 수 있으면 바꿔서 -2에서 2 사이로 자른다. 못 바꾸면 0. (`"2"`는 2, `2.7`은 2, `true`는 0)
- `fx`: 목록이 아니면 `[]`. 문자열이면서 `fx_names`에 있는 것만 순서대로 남기고 중복을 뺀다.
- `choices`: 비어 있지 않은 문자열이 정확히 3개일 때만 그대로, 아니면 `[]`.

**`ask_turn`:** `llm(messages)`를 부른다. `AllProvidersDown`이면 `None`. 답이 읽히면 `Reply`. 안 읽히면 `messages` 끝에 `{"role": "user", "content": "방금 답을 읽을 수 없었다. 같은 내용을 JSON 한 개로만 다시 출력해라."}`를 붙여 한 번 더 부르고, 또 안 읽히거나 `AllProvidersDown`이면 `None`. 호출은 최대 2번이다.

**엔딩:** `build_ending_messages`는 system 하나와 `history`, 그리고 마지막에 엔딩 문구를 요청하는 `user` 메시지를 돌려준다. system에는 캐릭터 요약(이름, 속성, 말투), 등급 이름, 최종 점수, 출력 형식(`title` 20자 이내이고 " 엔딩"으로 끝남, `epilogue` 2문장, `nickname` 12자 이내), 수위 규칙이 들어간다. `parse_ending`은 세 칸이 모두 비어 있지 않은 문자열일 때만 `Ending`을 돌려주고, `title`이 "엔딩"으로 끝나지 않으면 " 엔딩"을 붙인다. `ask_ending`은 한 번만 부르고 실패하면 `None`.

**Tests (`tests/test_actor.py`):**

- `parse_reply`: 정상 JSON, 코드 울타리로 감싼 JSON, 앞뒤에 말이 붙은 JSON, JSON이 아닌 글(`None`), `say` 없음(`None`), `delta: "2"`는 2, `delta: 9`는 2, `delta: -5`는 -2, `delta: "abc"`는 0, `face: "angry"`는 `neutral`, `fx: "꽃잎"`은 `[]`, `fx`에 모르는 이름이 섞이면 아는 것만, `choices` 2개는 `[]`, `choices` 3개는 그대로.
- `build_turn_messages`: 첫 메시지가 system이고 나머지가 `history`와 같다. system에 캐릭터 이름, `never`의 첫 항목, 강도 숫자, `fx_allowed`의 낱말이 들어 있다. `seed="정전", seed_kind="event"`면 "정전"이 들어 있다. `band="high"`면 `by_affinity["high"]`가 들어 있고 `by_affinity["low"]`는 없다. `intensity=5`일 때만 `max_brain`이 들어 있다. `extra="XYZ"`면 system이 "XYZ"로 끝난다. `history` 원본이 바뀌지 않는다.
- `ask_turn`: 첫 답이 정상이면 호출 1번. 첫 답이 깨지고 둘째가 정상이면 호출 2번이고 `Reply`. 둘 다 깨지면 `None`. 첫 호출에서 `AllProvidersDown`이면 `None`이고 호출 1번.
- `parse_ending`: 정상, 칸 빠짐(`None`), `title`에 "엔딩"이 없으면 붙음.
- `ask_ending`: `AllProvidersDown`이면 `None`.

---

### Task 3: 고유 장치와 수위 필터

**Files:** Create `sogaeting/gimmicks.py`, `sogaeting/safety.py`, `tests/test_gimmicks.py`, `tests/test_safety.py`

**Interfaces (Produces):**

```python
# sogaeting/gimmicks.py
class Gimmick:                       # 아무 일도 하지 않는 기본형
    name = "none"
    def transform_input(self, text: str, rng: random.Random) -> tuple[str, str | None]:
        return text, None            # (배우에게 보낼 글, 화면에 보일 "들은 말" 또는 None)
    def extra_instruction(self, past_inputs: list[str]) -> str:
        return ""                    # 배우 지시문 끝에 붙일 글
    def adjust_delta(self, delta: int) -> tuple[int, str | None]:
        return delta, None           # (바뀐 delta, 화면에 띄울 알림 또는 None)
    def decorate(self, reply: dict, ctx: dict) -> dict:
        return {}                    # 화면 표시용 덧붙임
def get_gimmick(name: str | None) -> Gimmick     # 모르는 이름과 None은 기본형

# sogaeting/safety.py
MAX_INPUT = 100
def clean_input(text: str) -> str
def contains_banned(texts, banned: list[str]) -> bool
```

`decorate`의 `reply`는 `Reply`를 dict로 바꾼 것(`narration`, `say`, `inner`, `face`, `fx`, `delta`, `reason`, `choices`)이다. `ctx`의 키: `turn`(등장은 0, 답은 1부터), `total_turns`(답의 총 개수), `score`(이번 답까지 반영한 호감도 0-100), `change`(이번 답에서 실제로 움직인 점수), `past_inputs`(참가자가 지금까지 친 원문 목록, 이번 것 포함).

**장치 여섯 개:**

| `name` | 동작 |
|---|---|
| `exploding_popup` | `decorate`: `turn`이 0이면 `{}`. `turn == total_turns`이면 `{"popup": "NaN"}`. 그 밖에는 `change * 10 ** (turn - 1)`을 부호와 천 단위 쉼표를 붙여 `{"popup": "+1,400"}`처럼 돌려준다. 값이 0이면 `"±0"` |
| `quote_memory` | `extra_instruction`: `past_inputs`가 비어 있으면 `""`. 아니면 지난 입력을 번호와 함께 원문 그대로 나열하고, 이번 답의 `say`에서 그중 하나 이상을 따옴표 안에 글자 하나 바꾸지 않고 인용하라고 지시하는 글. `decorate`: `{"highlights": [...]}`. `past_inputs` 가운데 앞뒤 공백을 뗀 길이가 2 이상이고 `reply["say"]`에 그대로 들어 있는 것을 `past_inputs` 순서로, 중복 없이 |
| `dropout` | `transform_input`: 글을 공백으로 나눈 낱말 가운데 `max(1, round(낱말 수 * 0.3))`개를 `rng.sample`로 골라 `"■■"`로 바꾼다. 낱말이 0개면 `(text, None)`. 돌려주는 두 값은 같은 가려진 글이다 |
| `relu` | `adjust_delta`: 음수면 `(0, "음수 감지 → 0")`, 아니면 `(delta, None)` |
| `citation_needed` | `decorate`: `{"say_marked": ...}`. `reply["say"]`에서 숫자 덩어리(뒤에 붙은 `%`, `퍼센트`, `년`, `배`, `명`, `위` 포함)와 낱말 `연구`, `논문`, `교칙`, `통계`가 나올 때마다 바로 뒤에 `" [출처 필요]"`를 넣는다. 한 답에 3개까지만 넣는다. 해당하는 곳이 없으면 `say` 그대로 |
| `blackbox` | `decorate`: `{"inner_masked": ...}`. `reply["inner"]`에서 공백이 아닌 글자 `n`개 가운데 `round(n * score / 100)`개만 남기고 나머지를 `"■"`로 바꾼다. 남길 글자는 `random.Random(ctx["turn"])`으로 고른다. 공백은 그대로 둔다 |

**safety:**

- `clean_input`: 줄바꿈과 탭을 공백으로 바꾸고, 이어진 공백을 하나로 줄이고, 앞뒤 공백을 떼고, 100자에서 자른다. `None`이 아닌 문자열만 받는다고 가정한다.
- `contains_banned`: `texts`(문자열의 반복 가능한 묶음, `None`과 빈 문자열은 건너뜀) 가운데 하나라도 `banned`의 낱말을 포함하면 참. 띄어쓰기를 지운 글에서도 한 번 더 찾는다 (낱말 사이에 공백을 넣어 피하는 것을 막는다).

**Tests:**

- `exploding_popup`: `turn=1, change=14`는 `"+14"`. `turn=3, change=-14`는 `"-1,400"`. `turn=2, change=0`은 `"±0"`. `turn=7, total_turns=7`은 `"NaN"`. `turn=0`은 `{}`.
- `quote_memory`: 빈 목록이면 `""`. 목록이 있으면 지시문에 각 입력 원문이 들어 있다. `say`에 지난 입력이 그대로 있으면 `highlights`에 나오고, 한 글자 다르면 안 나온다. 한 글자짜리 입력은 빠진다.
- `dropout`: 씨앗값을 고정한 `rng`로 낱말 10개 가운데 3개가 가려진다. 낱말 1개면 그 하나가 가려진다. 빈 글이면 `(text, None)`. 가려지지 않은 낱말의 순서가 그대로다.
- `relu`: -2는 `(0, 알림)`, 0은 `(0, None)`, 2는 `(2, None)`.
- `citation_needed`: "연구에 따르면 130%야"에 딱지가 2개 붙는다. 해당 낱말이 5번 나와도 딱지는 3개다. 해당 없음이면 그대로다.
- `blackbox`: `score=100`이면 원문 그대로. `score=0`이면 공백 아닌 글자가 전부 `■`. `score=50`이고 공백 아닌 글자가 10개면 `■`가 5개. 공백 위치가 그대로다. 같은 `turn`이면 결과가 같다.
- `get_gimmick`: 여섯 이름이 각각 맞는 장치를 돌려준다. `None`과 모르는 이름은 기본형이고 기본형의 네 함수는 아무것도 바꾸지 않는다.
- `clean_input`: 300자는 100자가 된다. `" 안녕\n\n 하세요\t"`는 `"안녕 하세요"`가 된다. 공백만 있으면 `""`.
- `contains_banned`: 포함하면 참. 띄어 써서 피해도 참. `None`과 빈 문자열이 섞여도 죽지 않는다. 빈 `banned`면 거짓.

---

### Task 4: 진행자, 가짜 모델, 터미널 실행기

**Files:** Create `sogaeting/director.py`, `sogaeting/fake_llm.py`, `sogaeting/cli.py`, `sogaeting/__main__.py`, `tests/test_director.py`

**Interfaces (Consumes):** Task 1의 `content` 함수들, Task 2의 `actor`, Task 3의 `gimmicks`와 `safety`, `llm.call_llm`.

**Interfaces (Produces):**

```python
# sogaeting/director.py
START_SCORE = 50
STEP = 7                                   # delta 1칸에 움직이는 점수
def band_of(score: int) -> str             # 65 이상 "high", 40-64 "mid", 39 이하 "low"

class Session:
    def __init__(self, character_id: str, *, llm=None, rng: random.Random | None = None): ...
    done: bool                             # 엔딩까지 끝났는가
    def start(self) -> dict                # 등장. 한 번만 부른다
    def reply(self, user_text: str) -> dict
    def finish(self) -> dict               # 엔딩 카드. 여러 번 불러도 같은 값
    def result(self) -> dict               # 3단계로 넘길 값. finish() 뒤에만

def save_result(result: dict, directory="results") -> pathlib.Path

# sogaeting/fake_llm.py
def fake_llm(messages: list[dict]) -> str  # 네트워크 없이 그럴듯한 JSON을 돌려주는 가짜 모델
```

- `llm`을 안 주면 `lambda m: call_llm(m, json_mode=True)`를 쓴다. `rng`를 안 주면 `random.Random()`.

**`start()`와 `reply()`가 돌려주는 dict:**

```python
{
  "kind": "turn",
  "turn": 0,                 # 등장 0, 답 1..7
  "total_turns": 7,
  "narration": str, "say": str, "inner": str, "face": str,
  "fx": [str], "choices": [str],
  "delta": int,              # 장치가 고친 뒤의 값
  "change": int,             # 실제로 움직인 점수
  "reason": str,
  "score": int,              # 이번 답까지 반영한 호감도
  "band": str,               # 반영한 뒤의 구간
  "popup": str | None,       # 등장과 대체 대사일 때 None
  "notes": [str],            # 장치 알림 (예: "음수 감지 → 0")
  "heard": str | None,       # dropout의 "들은 말"
  "extras": dict,            # 장치 decorate의 결과
  "fallback": bool,          # 대체 대사를 썼는가
  "finale": bool             # 마지막 답인가. 참이면 다음에 finish()를 부른다
}
```

**`finish()`가 돌려주는 dict:**

```python
{
  "kind": "ending",
  "character_id": str, "character_name": str,
  "band_id": str, "band_name": str,
  "title": str, "epilogue": str, "nickname": str,
  "score": int,
  "best_line": str,          # delta 절댓값이 가장 컸던 답의 속마음. 같으면 뒤쪽. 답이 없으면 ""
  "inners": [str],           # 이번 판의 속마음 전부, 순서대로 (등장 포함)
  "early": bool              # 답 7번을 다 채우기 전에 끝냈는가
}
```

**`result()`:** `{"character_id", "character_name", "affinity", "band", "ending_title", "nickname", "finished_at"}`. `affinity`는 최종 점수, `band`는 등급 이름, `finished_at`은 ISO 형식 시각. 대화 원문은 넣지 않는다. `save_result`는 폴더를 만들고 `시각_캐릭터.json`으로 저장한 뒤 경로를 돌려준다.

**진행 규칙:**

1. `start()`: 등장 씨앗 하나를 `rng.choice`로 뽑는다. `history = [{"role": "user", "content": OPENING_CUE}]`. 배우를 부른다. 점수는 움직이지 않고 `delta`는 0, `reason`은 `""`, `popup`은 `None`.
2. `reply(text)`: `clean_input`으로 다듬는다. 다듬은 글이 비어 있으면 `ValueError`. `done`이거나 답 7번을 이미 채웠으면 `RuntimeError`. `start()` 전이어도 `RuntimeError`.
3. 장치의 `transform_input`으로 배우에게 보낼 글을 만들고 그것을 `history`에 `user`로 넣는다. 다듬은 원문은 `past_inputs`에 넣는다.
4. 진행표에서 이번 답의 강도와 씨앗 종류를 읽는다. 씨앗이 `event`면 아직 안 쓴 사건 씨앗 가운데 하나를 뽑는다. 구간은 이번 답을 반영하기 전 점수로 정한다. `fx_allowed`는 강도 2 이하면 `light`, 3 이상이면 `light + heavy`. `extra`는 장치의 `extra_instruction(past_inputs)`.
5. `ask_turn`을 부른다. `None`이거나, 답의 `narration`, `say`, `inner`, `reason`, `choices`에 금지어가 있으면 대체 대사로 바꾼다: `say`는 캐릭터의 `fallback_lines`를 차례로 돌려 쓰고, 나머지는 빈 값, `delta` 0, `face`는 `neutral`, `fallback`은 참, `popup`은 `None`.
6. 연출 거르기: 강도 2 이하에서 `heavy`를 버린다. 바로 앞 답(등장 포함)에서 실제로 내보낸 연출과 같은 이름을 버린다. 남은 것 가운데 앞의 2개만 쓴다.
7. 점수: 장치의 `adjust_delta` → `change = delta * STEP` → 0에서 100 사이로 자른 새 점수 → `change`는 새 점수와 옛 점수의 차이. 알림이 있으면 `notes`에 넣는다.
8. 마지막 답이면 `choices`를 비우고 `finale`을 참으로 한다.
9. `decorate`의 결과를 `extras`에 넣는다. `extras`에 `popup`이 있으면 그것을, 없으면 `change`를 부호와 함께(`"+14"`, `"-7"`, 0이면 `"±0"`) `popup`으로 쓴다.
10. `history`에 `assistant`로 이번 답의 JSON 문자열(여덟 칸)을 넣는다. 대체 대사일 때도 넣는다.
11. `finish()`: 등급을 `load_endings()`로 정한다. `history` 끝이 `user`가 아니어도 되게 `build_ending_messages`를 부르고 `ask_ending`을 부른다. `None`이거나 금지어가 있으면 `title`은 `"{등급 이름} 엔딩"`, `epilogue`와 `nickname`은 `""`. 결과를 기억해 두고 다시 부르면 같은 dict를 돌려준다. `start()` 전에 부르면 `RuntimeError`.

**`fake_llm`:** 마지막 메시지와 system 내용을 보고 차례에 맞는 JSON 문자열을 돌려준다. 엔딩 요청(마지막 `user` 메시지에 "엔딩"이 들어 있음)에는 `title`, `epilogue`, `nickname`을, 그 밖에는 여덟 칸을 채운다. `delta`는 참가자 글의 길이로 정해 판마다 조금씩 다르게 한다. 시험과 시연용이라 대사는 "(가짜 모델)"로 시작한다.

**`cli.py`:** `main(argv=None)`. `python3 -m sogaeting [캐릭터 id] [--fake]`.

- 시작할 때 `load_dotenv()`를 부른다. `--fake`면 `fake_llm`을 쓴다.
- 캐릭터 id가 없으면 여섯 명의 번호, 이름, 속성을 보여 주고 번호로 고르게 한다.
- 답마다 지문, 이름과 겉말, 속마음, 팝업과 사유, 알림, 호감도를 찍는다. `extras`에 `say_marked`가 있으면 겉말 대신, `inner_masked`가 있으면 속마음 대신 그것을 찍는다. `heard`가 있으면 "들은 말:"로 찍는다.
- 선택지가 있으면 번호를 붙여 보여 주고, 참가자가 1, 2, 3을 치면 그 선택지를, 다른 글을 치면 그 글을 입력으로 쓴다. 빈 입력은 다시 받는다. `q`를 치면 곧장 엔딩으로 간다.
- 마지막에 엔딩 카드를 찍고 `save_result`로 저장한 경로와 `status_line()`을 찍는다.
- `__main__.py`는 `cli.main()`만 부른다.

**Tests (`tests/test_director.py`):** 배우 답은 `llm` 자리에 가짜 함수를 넣어 만든다. 캐릭터는 실제 데이터 파일을 쓴다.

- 정상 한 판: `start()` 뒤 `reply()` 7번. `turn`이 0부터 7까지이고 마지막만 `finale`이 참이고 `choices`가 비어 있다. 여덟 번째 `reply()`는 `RuntimeError`.
- 점수: 가짜 모델이 `delta` 2만 주면 50, 64, 78, 92, 100, 100으로 가고, 100에 닿은 뒤 `change`는 0이다. `delta` -2만 주면 0에서 멈춘다.
- 구간: 배우에게 보낸 system에 반영 전 점수의 구간 설명이 들어 있다.
- 씨앗: 등장 때 system에 등장 씨앗 하나가, 답 3과 답 5 때 서로 다른 사건 씨앗이 들어 있다. 다른 답에는 사건 씨앗이 없다.
- 연출: 강도 2인 답 1에서 `"암전"`이 버려진다. 앞 답과 같은 연출이 버려진다. 3개가 오면 2개만 남는다.
- 대체 대사: 가짜 모델이 항상 `AllProvidersDown`을 내도 `start()`, `reply()` 7번, `finish()`가 끝까지 가고, `fallback`이 전부 참이고, 점수가 50이고, `title`이 "애매 엔딩"이다. `fallback_lines`가 차례로 돌아 나온다.
- 금지어: 가짜 모델의 `say`에 `load_banned()[0]`이 들어 있으면 대체 대사로 바뀐다.
- 입력: 빈 글과 공백만 있는 글은 `ValueError`. 300자는 100자로 잘려 `history`에 들어간다.
- 장치: `relu`로 `delta` -2가 0이 되고 `notes`에 알림이 있다. `anna`로 `history`의 `user` 글에 `■■`가 있고 `heard`가 그 글과 같다. `giulhee`의 답 2에서 `popup`이 `change`의 10배다. `boxhyun`의 `extras`에 `inner_masked`가 있다.
- 엔딩: `finish()`를 두 번 불러 같은 dict를 받는다. `start()` 직후 `finish()`는 `early`가 참이고 `best_line`이 `""`이다. `best_line`은 `delta` 절댓값이 가장 큰 답의 속마음이고 같으면 뒤쪽이다. `result()`에 대화 원문이 없다.
- `save_result`: 임시 폴더에 파일이 생기고 내용이 `result()`와 같다.
- `fake_llm`으로 여섯 캐릭터 모두 한 판이 끝까지 간다.

---

## Self-Review

- 설계 문서의 각 절과 Task: 5.3 흐름과 5.5 강도와 5.6 씨앗과 5.7 연출과 5.8 호감도와 5.11 장애 대응은 Task 4, 5.4 배우는 Task 2, 5.9 장치와 5.10 수위는 Task 3, 5.14 데이터는 Task 1, 5.13 모델 호출은 이미 있는 `llm.py`.
- 이번 계획에 없는 것: 5.2 화면, 5.12의 주소로 넘겨받기와 무입력 3분 초기화. 서버와 화면을 만들 때 다룬다.
- Review Focus의 다섯 항목은 Task 2의 `parse_reply` 테스트(1, 2)와 Task 4의 대체 대사, 입력, 엔딩 테스트(3, 4, 5)에 들어 있다.

# 그림 한꺼번에 뽑기 (make_art.py)

캐릭터 6명의 표정 6가지(36장)와 배경 8장을 명령 한 줄로 뽑는다. 요청은 각자 컴퓨터에서 보내고, 키도 각자 컴퓨터에만 둔다.

## 준비

1. Python 3.10 이상.
2. `pip install pillow` (배경 지우기와 미리보기에 쓴다. 없어도 그림은 받아진다.)
3. 레포 맨 위에 `.env` 파일을 만들고 키를 적는다. 이 파일은 깃에 올라가지 않는다.

```
CLOUDFLARE_ACCOUNT_ID=여기에_계정_ID
CLOUDFLARE_API_TOKEN=여기에_토큰
```

키 받는 곳 (무료, 카드 필요 없음):

- dash.cloudflare.com에 가입한다.
- 계정 ID: 대시보드의 Workers & Pages 화면 오른쪽에 있다.
- API 토큰: 내 프로필 → API 토큰 → 토큰 만들기 → "Workers AI" 템플릿.

Gemini 그림 모델을 쓰려면 `GEMINI_API_KEY=...`를 적고 `--backend gemini`로 실행한다. 이쪽은 무료 한도가 없어서 결제가 연결된 키가 필요하다.

## 실행

```
python tools/make_art.py --only giulhee     한 명만 먼저 뽑아 품질을 본다
python tools/make_art.py                    없는 그림을 전부 뽑는다
```

끝나면 `art/preview.png` 한 장에 전부 모인다. 이 한 장만 보면 된다.

| 하고 싶은 것 | 명령 |
|---|---|
| 요청문만 보기 (요청은 안 보냄) | `python tools/make_art.py --dry-run` |
| 이름과 진행 상황 보기 | `python tools/make_art.py --list` |
| 한 장만 다시 뽑기 | `python tools/make_art.py --only giulhee:smile --force --seed 2` |
| 캐릭터 한 명을 통째로 다시 | `python tools/make_art.py --only giulhee --force --seed 2` |
| 배경만 | `python tools/make_art.py --only bg` |
| 배경 지우기만 다시 (요청은 안 보냄) | `python tools/make_art.py --recut` |

- 이미 받은 그림은 건너뛴다. 중간에 끊기거나 하루 한도가 차도 같은 명령을 다시 실행하면 이어진다.
- `--seed` 숫자를 바꾸면 같은 요청문으로 다른 그림이 나온다.
- 기준 그림(neutral)을 다시 뽑으면 나머지 표정도 같이 다시 뽑아야 얼굴이 맞는다.

## 결과

```
art/
  preview.png            전체 미리보기
  sprites/<캐릭터>/<표정>.png   배경이 투명한 캐릭터 그림 (768x1152)
  bg/<장소>.jpg          배경 (1280x720)
  raw/                   받은 그대로의 그림 (깃에 올리지 않음)
  manifest.json          어떤 요청문과 씨앗으로 만들었는지 기록
```

## 그림 고치기

요청문은 전부 `tools/art_prompts.json`에 있다. 코드는 건드리지 않는다.

- `characters.<이름>.look`: 그 캐릭터의 외모.
- `faces`: 공통 표정 여섯 가지. 캐릭터마다 다르게 하려면 `characters.<이름>.faces`에 적는다.
- `sprite.style`: 전체 화풍.
- `characters.<이름>.key`: 지울 배경색. 머리나 옷이 초록 계열이면 `magenta`, 보라나 분홍 계열이면 `green`.
- `cut`: 배경 지우기 세기. 사람이 같이 지워지면 `low`를 올리고, 배경이 남으면 `high`를 내린다. 고친 뒤 `--recut`.

## 방식

1. 캐릭터마다 기준 그림(neutral)을 글만으로 한 장 뽑는다.
2. 그 그림을 참고 그림으로 붙여서 표정만 바꾼 다섯 장을 뽑는다. 그래야 같은 얼굴이 나온다.
3. 캐릭터는 단색(초록이나 자홍) 배경으로 뽑고, 코드가 그 색을 지워 투명하게 만든다.
4. 배경은 사람 없이 따로 뽑는다.

기본 모델은 Cloudflare Workers AI의 FLUX.2 klein 4B다. 무료 한도는 하루 10,000 뉴런이고, 계산상 하루 80장 안팎이다. `--backend schnell`은 더 싸지만 참고 그림을 못 받아서 표정마다 얼굴이 달라질 수 있다.

## 아직 확인하지 못한 것

이 스크립트는 가짜 서버로만 시험했다. 진짜 API로는 한 번도 돌려 보지 못했다.

- 요청과 응답 형식은 공개 문서를 보고 맞췄다. 실제와 다르면 오류 문장이 그대로 찍힌다.
- 모델이 단색 배경을 얼마나 잘 지키는지, 표정 다섯 장이 기준 그림과 얼마나 닮는지는 뽑아 봐야 안다.
- 하루에 몇 장까지 되는지는 계산값이다.

# GPT로 캐릭터 그림 뽑기

ChatGPT 같은 대화형 그림 도구에 붙여 넣을 요청문이다. 캐릭터 6명, 기본 표정 6장씩과 캐릭터만의 표정 7장, 모두 43장.

이 글은 `python tools/make_art.py --gpt-doc` 이 만든다. 직접 고치지 말고 `tools/art_prompts.json`을 고친 뒤 같은 명령으로 다시 만든다.

## 지금 할 일

이번에 뽑을 그림은 12장이다. "그대로 두기"라고 적힌 그림은 이미 뽑은 것을 쓰고 다시 뽑지 않는다.

| 캐릭터 | 할 일 | 이번에 뽑을 것 | 까닭 |
|---|---|---|---|
| 아스트라 | 할 것 없음 | 없음 | 게임에 넣은 그림(남색 리본, 기본 여섯 장, huff, denial)을 그대로 쓴다. 2026-11-14에 받은 빨간 리본 세트는 쓰지 않기로 했다(사용자). |
| 젬마 | 전부 다시 뽑기 | neutral, smile, blush, pout, shock, dark, hide | 머리를 밤색으로, 머리핀과 눈을 보라로 바꿨다. 처음의 연한 파랑은 아스트라, 소라와 겹쳤고, 다음의 초록은 사용자가 별로라고 했다(2026-11-14). |
| 소라 | 할 것 없음 | 없음 | 2026-11-14에 받은 일곱 장을 넣었다. |
| 노바 | 할 것 없음 | 없음 | 2026-11-14에 받은 분홍 일곱 장을 넣었다. |
| 미스트랄 | 할 것 없음 | 없음 | 2026-11-14에 받은 일곱 장을 넣었다. dark는 받은 그림의 배경이 불투명해서 사용자가 다듬은 그림을 썼다. |
| 하이쿠 | 적힌 표정만 다시 뽑기 | smile, blush, pout, shock, dark | 받은 일곱 장을 일단 넣었지만 flushed 말고는 표정이 거의 같다(사용자). 표정 요청문에서 "거의 같은 무표정"을 빼고 작게 봐도 보이게 고쳤다. neutral과 flushed는 그대로 쓰고, 그 neutral을 첨부해 다섯 장을 다시 뽑는다. |

- 그대로 두는 캐릭터의 캐릭터만의 표정은, 그 캐릭터의 이미 뽑은 기본(neutral) 그림을 첨부하고 요청문을 보낸다.
- 전부 다시 뽑는 캐릭터는 기준 그림부터 새 대화에서 뽑는다. 예전 그림을 첨부하지 않는다(예전 색이 따라온다).

## 순서

1. 캐릭터마다 새 대화를 연다. "기준 그림" 요청문을 붙여 넣어 한 장을 받는다. 마음에 들 때까지 다시 뽑는다.
2. 같은 대화에서 표정 요청문을 하나씩 보낸다. 기준 그림이 대화에 없으면 첨부한다. 얼굴, 머리, 옷이 기준 그림과 같은지 본다.
3. 받은 그림을 `art/raw/<캐릭터 id>/<표정>.png` 로 저장한다. 예: `art/raw/astra/neutral.png`. jpg와 webp도 된다.
4. `python tools/make_art.py --recut` 을 실행한다. 배경을 지우고(이미 투명이면 그대로 두고) 768x1152 크기로 맞춰 `art/sprites/` 에 넣는다. `art/preview.png` 도 다시 만든다.
5. `art/preview.png` 를 열어 모든 표정이 같은 얼굴인지, 머리가 잘리지 않았는지, 배경이 깨끗이 지워졌는지 본다.
6. 게임은 `run_booth.py` 로 켤 때 `art/` 의 그림을 가져다 쓴다. 그림이 없는 캐릭터와 표정은 자리표시 그림이 나온다.

## 지킬 것

- 캐릭터는 전원 동갑 고2이고 전체 이용가다. 교복을 단정하게 입은 허리 위 그림만 쓴다. 선정적으로 나온 그림은 쓰지 않는다.
- 그림에 글자나 워터마크가 들어가면 다시 뽑는다.
- 배경이 투명하게 안 나오면 요청문에 적힌 단색 배경으로 받는다. `--recut` 이 그 색을 지운다. 투명 배경 대신 체크무늬가 그려져 나와도 `--recut` 이 알아보고 지운다.
- 기본 표정 이름: neutral, smile, blush, pout, shock, dark.
- 캐릭터만의 표정은 그 캐릭터의 요청문 끝에 있다. 성격에 맞춰 더한 표정이고, 몸짓이 조금 바뀌는 것도 있다. 그림이 없으면 게임은 비슷한 기본 표정의 그림을 대신 쓴다.

## 캐릭터별 요청문

### 아스트라 (astra)

할 일: 할 것 없음. 게임에 넣은 그림(남색 리본, 기본 여섯 장, huff, denial)을 그대로 쓴다. 2026-11-14에 받은 빨간 리본 세트는 쓰지 않기로 했다(사용자).

기준 그림 (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/astra/neutral.png`

```
Draw one character sprite for a visual novel game.
Art style: Japanese bishoujo game (galge) character art, like a heroine sprite from a moe visual novel. Large sparkling detailed eyes, small nose and mouth, glossy hair with sharp highlights, thin clean line art, soft cel shading with light gradients, bright pastel colors.
Framing: One character only, waist-up portrait, centered, facing the viewer. The whole head and all of the hair are inside the frame, with empty space above the head.
Character: Deep midnight-blue hair fading to violet at the tips, tied in a high ponytail that puffs out wider toward the end. Golden amber eyes, sharply raised eyebrows. A navy-blue track jacket with rolled-up sleeves and a thin chest stripe in blue, red, yellow and green, worn over the white school shirt instead of a blazer. A small star-shaped hairpin. Arms crossed, head turned slightly away while her eyes glance at the viewer. School uniform: white collared shirt with a small ribbon tie, and a small emblem of three circles connected by lines on the left chest.
Expression: annoyed, aloof look with raised eyebrows, mouth closed.
Content: A high school student in a modest, fully covering school outfit. Wholesome, all-ages.
Background: fully transparent (PNG with alpha). If a transparent background is not possible, fill the whole background with one flat pure bright green (#00FF00) chroma key color, with no gradient, shadow, floor or objects.
No text, no watermark, no border. Portrait image, aspect ratio 2:3.
```

표정 smile (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/astra/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a bright, genuine smile with gently curved eyes. Keep the same background and the same image size.
```

표정 blush (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/astra/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/astra/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/astra/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/astra/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically ominous: the upper half of the face is in shadow, dull eyes without highlights, a thin fixed smile. Keep the same background and the same image size.
```

캐릭터만의 표정 huff (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/astra/huff.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style and framing exactly. Change the facial expression, and change the pose only as the new pose describes. New expression: a tsundere 'hmph' face: eyes closed, chin raised, a small pouting mouth, a faint blush on the cheeks. New pose: She turns her head further away to the side, arms still crossed. Keep the same background and the same image size.
```

캐릭터만의 표정 denial (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/astra/denial.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered angry denial: face bright red up to the ears, eyes squeezed shut, mouth wide open as if shouting, eyebrows angled sharply, a small sweat drop. Keep the same background and the same image size.
```

### 젬마 (gemma)

할 일: 전부 다시 뽑기. 머리를 밤색으로, 머리핀과 눈을 보라로 바꿨다. 처음의 연한 파랑은 아스트라, 소라와 겹쳤고, 다음의 초록은 사용자가 별로라고 했다(2026-11-14).

기준 그림 (새로 뽑기). 저장할 곳: `art/raw/gemma/neutral.png`

```
Draw one character sprite for a visual novel game.
Art style: Japanese bishoujo game (galge) character art, like a heroine sprite from a moe visual novel. Large sparkling detailed eyes, small nose and mouth, glossy hair with sharp highlights, thin clean line art, soft cel shading with light gradients, bright pastel colors.
Framing: One character only, waist-up portrait, centered, facing the viewer. The whole head and all of the hair are inside the frame, with empty space above the head.
Character: Soft chestnut-brown hair in two neat, loose braids. Gentle violet eyes. Round glasses. A navy school blazer worn neatly. A small amethyst-purple gem-shaped hairpin. She holds a small notebook against her chest with both hands. Shoulders slightly drawn in, a shy posture. School uniform: white collared shirt with a small ribbon tie, and a small emblem of three circles connected by lines on the left chest.
Expression: shy, gentle look with eyes slightly lowered and a small soft smile.
Content: A high school student in a modest, fully covering school outfit. Wholesome, all-ages.
Background: fully transparent (PNG with alpha). If a transparent background is not possible, fill the whole background with one flat pure bright green (#00FF00) chroma key color, with no gradient, shadow, floor or objects.
No text, no watermark, no border. Portrait image, aspect ratio 2:3.
```

표정 smile (새로 뽑기). 저장할 곳: `art/raw/gemma/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a bright, genuine smile with gently curved eyes. Keep the same background and the same image size.
```

표정 blush (새로 뽑기). 저장할 곳: `art/raw/gemma/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout (새로 뽑기). 저장할 곳: `art/raw/gemma/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock (새로 뽑기). 저장할 곳: `art/raw/gemma/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark (새로 뽑기). 저장할 곳: `art/raw/gemma/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically ominous: the upper half of the face is in shadow, dull eyes without highlights, a thin fixed smile. Keep the same background and the same image size.
```

캐릭터만의 표정 hide (새로 뽑기). 저장할 곳: `art/raw/gemma/hide.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style and framing exactly. Change the facial expression, and change the pose only as the new pose describes. New expression: deeply embarrassed: cheeks bright red, eyes looking up shyly. New pose: She lifts the notebook with both hands to cover the lower half of her face, so only her eyes and glasses show above it. Keep the same background and the same image size.
```

### 소라 (sora)

할 일: 할 것 없음. 2026-11-14에 받은 일곱 장을 넣었다.

기준 그림 (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/sora/neutral.png`

```
Draw one character sprite for a visual novel game.
Art style: Japanese bishoujo game (galge) character art, like a heroine sprite from a moe visual novel. Large sparkling detailed eyes, small nose and mouth, glossy hair with sharp highlights, thin clean line art, soft cel shading with light gradients, bright pastel colors.
Framing: One character only, waist-up portrait, centered, facing the viewer. The whole head and all of the hair are inside the frame, with empty space above the head.
Character: Fluffy white short bob with pale sky-blue tips and messy flyaway strands, like a cloud. Sleepy half-closed sky-blue eyes with a small star-shaped sparkle in each. A small cloud-shaped hair clip on one side only. A cream-colored knit cardigan with one button missing, worn over the white school shirt instead of a blazer. Relaxed posture, head tilted slightly. School uniform: white collared shirt with a small ribbon tie, and a small emblem of three circles connected by lines on the left chest.
Expression: sleepy, absent-minded look with a faint vacant smile.
Content: A high school student in a modest, fully covering school outfit. Wholesome, all-ages.
Background: fully transparent (PNG with alpha). If a transparent background is not possible, fill the whole background with one flat pure bright magenta (#FF00FF) chroma key color, with no gradient, shadow, floor or objects.
No text, no watermark, no border. Portrait image, aspect ratio 2:3.
```

표정 smile (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/sora/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a bright, genuine smile with gently curved eyes. Keep the same background and the same image size.
```

표정 blush (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/sora/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/sora/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/sora/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/sora/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically ominous: the upper half of the face is in shadow, dull eyes without highlights, a thin fixed smile. Keep the same background and the same image size.
```

캐릭터만의 표정 yawn (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/sora/yawn.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: mid-yawn: eyes squeezed shut with a small tear at the corner of one eye, mouth open wide in a big relaxed yawn. Keep the same background and the same image size.
```

### 노바 (nova)

할 일: 할 것 없음. 2026-11-14에 받은 분홍 일곱 장을 넣었다.

기준 그림 (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/nova/neutral.png`

```
Draw one character sprite for a visual novel game.
Art style: Japanese bishoujo game (galge) character art, like a heroine sprite from a moe visual novel. Large sparkling detailed eyes, small nose and mouth, glossy hair with sharp highlights, thin clean line art, soft cel shading with light gradients, bright pastel colors.
Framing: One character only, waist-up portrait, centered, facing the viewer. The whole head and all of the hair are inside the frame, with empty space above the head.
Character: Bright rose-pink hair in a side ponytail. Sparkling rose-pink eyes. A rose-pink zip-up hoodie with white stripes on the sleeves, worn over the white school shirt instead of a blazer. A small adhesive bandage on one cheek. She leans forward toward the viewer with both hands clasped behind her back, an energetic, playful posture. School uniform: white collared shirt with a small ribbon tie, and a small emblem of three circles connected by lines on the left chest.
Expression: a cheerful smile with both eyes open and sparkling, mouth slightly open.
Content: A high school student in a modest, fully covering school outfit. Wholesome, all-ages.
Background: fully transparent (PNG with alpha). If a transparent background is not possible, fill the whole background with one flat pure bright green (#00FF00) chroma key color, with no gradient, shadow, floor or objects.
No text, no watermark, no border. Portrait image, aspect ratio 2:3.
```

표정 smile (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/nova/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a huge laughing smile, eyes closed in happy arcs, mouth wide open. Keep the same background and the same image size.
```

표정 blush (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/nova/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/nova/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking with puffed-out cheeks and a pouting mouth, both eyes open, eyebrows drawn together. Keep the same background and the same image size.
```

표정 shock (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/nova/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/nova/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a stiff frozen smile, the upper half of the face in shadow, eyes blank and dull without highlights, a sweat drop on the temple. Keep the same background and the same image size.
```

캐릭터만의 표정 excited (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/nova/excited.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style and framing exactly. Change the facial expression, and change the pose only as the new pose describes. New expression: fired up with excitement: sparkling star-shaped highlights in the eyes, mouth wide open in a happy cheer. New pose: She brings one hand out from behind her back and raises a clenched fist up near her shoulder. Keep the same background and the same image size.
```

### 미스트랄 (mistral)

할 일: 할 것 없음. 2026-11-14에 받은 일곱 장을 넣었다. dark는 받은 그림의 배경이 불투명해서 사용자가 다듬은 그림을 썼다.

기준 그림 (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/mistral/neutral.png`

```
Draw one character sprite for a visual novel game.
Art style: Japanese bishoujo game (galge) character art, like a heroine sprite from a moe visual novel. Large sparkling detailed eyes, small nose and mouth, glossy hair with sharp highlights, thin clean line art, soft cel shading with light gradients, bright pastel colors.
Framing: One character only, waist-up portrait, centered, facing the viewer. The whole head and all of the hair are inside the frame, with empty space above the head.
Character: Long wavy hair in a warm gradient, golden yellow at the top, turning orange and then deep red at the tips, swept to one side as if by wind. Confident amber eyes. A navy school blazer draped over her shoulders like a cape. A plain white armband on one arm with a single hand-drawn star, no letters. She holds a thick hardcover book. Chin slightly raised, looking down at the viewer. School uniform: white collared shirt with a small ribbon tie, and a small emblem of three circles connected by lines on the left chest.
Expression: smug, confident smirk.
Content: A high school student in a modest, fully covering school outfit. Wholesome, all-ages.
Background: fully transparent (PNG with alpha). If a transparent background is not possible, fill the whole background with one flat pure bright green (#00FF00) chroma key color, with no gradient, shadow, floor or objects.
No text, no watermark, no border. Portrait image, aspect ratio 2:3.
```

표정 smile (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/mistral/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a triumphant, self-satisfied grin. Keep the same background and the same image size.
```

표정 blush (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/mistral/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/mistral/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/mistral/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/mistral/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically ominous: the upper half of the face is in shadow, dull eyes without highlights, a thin fixed smile. Keep the same background and the same image size.
```

캐릭터만의 표정 busted (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/mistral/busted.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: caught bluffing and panicking: eyes darting to the side, a stiff nervous smile, several sweat drops on the face, eyebrows raised. Keep the same background and the same image size.
```

### 하이쿠 (haiku)

할 일: 적힌 표정만 다시 뽑기. 받은 일곱 장을 일단 넣었지만 flushed 말고는 표정이 거의 같다(사용자). 표정 요청문에서 "거의 같은 무표정"을 빼고 작게 봐도 보이게 고쳤다. neutral과 flushed는 그대로 쓰고, 그 neutral을 첨부해 다섯 장을 다시 뽑는다.

기준 그림 (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/haiku/neutral.png`

```
Draw one character sprite for a visual novel game.
Art style: Japanese bishoujo game (galge) character art, like a heroine sprite from a moe visual novel. Large sparkling detailed eyes, small nose and mouth, glossy hair with sharp highlights, thin clean line art, soft cel shading with light gradients, bright pastel colors.
Framing: One character only, waist-up portrait, centered, facing the viewer. The whole head and all of the hair are inside the frame, with empty space above the head.
Character: Ink-black bob cut with long bangs covering one eye. Gray eyes. A cream-colored hoodie with terracotta-orange drawstrings worn over the school uniform. Headphones resting around her neck. A small coral-orange starburst pin on the hoodie. Still, upright posture. School uniform: white collared shirt with a small ribbon tie, and a small emblem of three circles connected by lines on the left chest.
Expression: completely deadpan, expressionless face, mouth closed.
Content: A high school student in a modest, fully covering school outfit. Wholesome, all-ages.
Background: fully transparent (PNG with alpha). If a transparent background is not possible, fill the whole background with one flat pure bright green (#00FF00) chroma key color, with no gradient, shadow, floor or objects.
No text, no watermark, no border. Portrait image, aspect ratio 2:3.
```

표정 smile (새로 뽑기). 저장할 곳: `art/raw/haiku/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a rare, clearly visible soft smile she cannot hold back, the visible eye gently narrowed and curved, a faint warmth on the cheeks. The change must be easy to see even at a small size. Keep the same background and the same image size.
```

표정 blush (새로 뽑기). 저장할 곳: `art/raw/haiku/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: the visible eye looking away to the side, a clear pink blush across both cheeks, lips pressed into a small tight line. The change must be easy to see even at a small size. Keep the same background and the same image size.
```

표정 pout (새로 뽑기). 저장할 곳: `art/raw/haiku/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a cold, unimpressed look, as if looking down on something childish: a half-lidded bored stare, one eyebrow slightly raised, mouth a flat line turned down at one corner. The change must be easy to see even at a small size. Keep the same background and the same image size.
```

표정 shock (새로 뽑기). 저장할 곳: `art/raw/haiku/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: the visible eye wide open with a small pupil, eyebrows raised high, mouth a small open circle, a sweat drop on the temple. The change must be easy to see even at a small size. Keep the same background and the same image size.
```

표정 dark (새로 뽑기). 저장할 곳: `art/raw/haiku/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: the upper half of the face in heavy shadow, the visible eye dull and without highlights, a flat stare and a thin closed mouth. Keep the same background and the same image size.
```

캐릭터만의 표정 flushed (그대로 두기, 다시 뽑지 않는다). 저장할 곳: `art/raw/haiku/flushed.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: the same deadpan, expressionless face and closed mouth, eyes looking away, but the whole face and ears are bright red. Keep the same background and the same image size.
```

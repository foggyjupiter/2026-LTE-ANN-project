# GPT로 캐릭터 그림 뽑기

ChatGPT 같은 대화형 그림 도구에 붙여 넣을 요청문이다. 캐릭터 6명, 표정 6장씩 36장.

이 글은 `python tools/make_art.py --gpt-doc` 이 만든다. 직접 고치지 말고 `tools/art_prompts.json`을 고친 뒤 같은 명령으로 다시 만든다.

## 순서

1. 캐릭터마다 새 대화를 연다. "기준 그림" 요청문을 붙여 넣어 한 장을 받는다. 마음에 들 때까지 다시 뽑는다.
2. 같은 대화에서 표정 요청문을 하나씩 보낸다. 기준 그림이 대화에 없으면 첨부한다. 얼굴, 머리, 옷이 기준 그림과 같은지 본다.
3. 받은 그림을 `art/raw/<캐릭터 id>/<표정>.png` 로 저장한다. 예: `art/raw/astra/neutral.png`. jpg와 webp도 된다.
4. `python tools/make_art.py --recut` 을 실행한다. 배경을 지우고(이미 투명이면 그대로 두고) 768x1152 크기로 맞춰 `art/sprites/` 에 넣는다. `art/preview.png` 도 다시 만든다.
5. `art/preview.png` 를 열어 여섯 표정이 같은 얼굴인지, 머리가 잘리지 않았는지, 배경이 깨끗이 지워졌는지 본다.
6. 게임은 `run_booth.py` 로 켤 때 `art/` 의 그림을 가져다 쓴다. 그림이 없는 캐릭터와 표정은 자리표시 그림이 나온다.

## 지킬 것

- 캐릭터는 전원 동갑 고2이고 전체 이용가다. 교복을 단정하게 입은 허리 위 그림만 쓴다. 선정적으로 나온 그림은 쓰지 않는다.
- 그림에 글자나 워터마크가 들어가면 다시 뽑는다.
- 배경이 투명하게 안 나오면 요청문에 적힌 단색 배경으로 받는다. `--recut` 이 그 색을 지운다.
- 표정 이름: neutral, smile, blush, pout, shock, dark.

## 캐릭터별 요청문

### 아스트라 (astra)

기준 그림. 저장할 곳: `art/raw/astra/neutral.png`

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

표정 smile. 저장할 곳: `art/raw/astra/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a bright, genuine smile with gently curved eyes. Keep the same background and the same image size.
```

표정 blush. 저장할 곳: `art/raw/astra/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout. 저장할 곳: `art/raw/astra/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock. 저장할 곳: `art/raw/astra/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark. 저장할 곳: `art/raw/astra/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically ominous: the upper half of the face is in shadow, dull eyes without highlights, a thin fixed smile. Keep the same background and the same image size.
```

### 젬마 (gemma)

기준 그림. 저장할 곳: `art/raw/gemma/neutral.png`

```
Draw one character sprite for a visual novel game.
Art style: Japanese bishoujo game (galge) character art, like a heroine sprite from a moe visual novel. Large sparkling detailed eyes, small nose and mouth, glossy hair with sharp highlights, thin clean line art, soft cel shading with light gradients, bright pastel colors.
Framing: One character only, waist-up portrait, centered, facing the viewer. The whole head and all of the hair are inside the frame, with empty space above the head.
Character: Soft periwinkle-blue hair in two neat, loose braids. Round glasses. A navy school blazer worn neatly. A small gem-shaped hairpin. She holds a small notebook against her chest with both hands. Shoulders slightly drawn in, a shy posture. School uniform: white collared shirt with a small ribbon tie, and a small emblem of three circles connected by lines on the left chest.
Expression: shy, gentle look with eyes slightly lowered and a small soft smile.
Content: A high school student in a modest, fully covering school outfit. Wholesome, all-ages.
Background: fully transparent (PNG with alpha). If a transparent background is not possible, fill the whole background with one flat pure bright green (#00FF00) chroma key color, with no gradient, shadow, floor or objects.
No text, no watermark, no border. Portrait image, aspect ratio 2:3.
```

표정 smile. 저장할 곳: `art/raw/gemma/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a bright, genuine smile with gently curved eyes. Keep the same background and the same image size.
```

표정 blush. 저장할 곳: `art/raw/gemma/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout. 저장할 곳: `art/raw/gemma/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock. 저장할 곳: `art/raw/gemma/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark. 저장할 곳: `art/raw/gemma/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically ominous: the upper half of the face is in shadow, dull eyes without highlights, a thin fixed smile. Keep the same background and the same image size.
```

### 소라 (sora)

기준 그림. 저장할 곳: `art/raw/sora/neutral.png`

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

표정 smile. 저장할 곳: `art/raw/sora/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a bright, genuine smile with gently curved eyes. Keep the same background and the same image size.
```

표정 blush. 저장할 곳: `art/raw/sora/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout. 저장할 곳: `art/raw/sora/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock. 저장할 곳: `art/raw/sora/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark. 저장할 곳: `art/raw/sora/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically ominous: the upper half of the face is in shadow, dull eyes without highlights, a thin fixed smile. Keep the same background and the same image size.
```

### 노바 (nova)

기준 그림. 저장할 곳: `art/raw/nova/neutral.png`

```
Draw one character sprite for a visual novel game.
Art style: Japanese bishoujo game (galge) character art, like a heroine sprite from a moe visual novel. Large sparkling detailed eyes, small nose and mouth, glossy hair with sharp highlights, thin clean line art, soft cel shading with light gradients, bright pastel colors.
Framing: One character only, waist-up portrait, centered, facing the viewer. The whole head and all of the hair are inside the frame, with empty space above the head.
Character: Bright golden-yellow hair in a side ponytail. Warm orange eyes. A sunny orange zip-up hoodie worn over the white school shirt instead of a blazer. A small adhesive bandage on one cheek. Energetic posture, leaning slightly toward the viewer. School uniform: white collared shirt with a small ribbon tie, and a small emblem of three circles connected by lines on the left chest.
Expression: cheerful wide grin, eyes curved from smiling.
Content: A high school student in a modest, fully covering school outfit. Wholesome, all-ages.
Background: fully transparent (PNG with alpha). If a transparent background is not possible, fill the whole background with one flat pure bright magenta (#FF00FF) chroma key color, with no gradient, shadow, floor or objects.
No text, no watermark, no border. Portrait image, aspect ratio 2:3.
```

표정 smile. 저장할 곳: `art/raw/nova/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: an even bigger beaming smile, eyes closed in happy arcs. Keep the same background and the same image size.
```

표정 blush. 저장할 곳: `art/raw/nova/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout. 저장할 곳: `art/raw/nova/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock. 저장할 곳: `art/raw/nova/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark. 저장할 곳: `art/raw/nova/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: still smiling brightly, but the eyes are blank and without highlights, a small sweat drop on the temple. Keep the same background and the same image size.
```

### 미스트랄 (mistral)

기준 그림. 저장할 곳: `art/raw/mistral/neutral.png`

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

표정 smile. 저장할 곳: `art/raw/mistral/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: a triumphant, self-satisfied grin. Keep the same background and the same image size.
```

표정 blush. 저장할 곳: `art/raw/mistral/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: flustered and embarrassed, cheeks clearly blushing red, eyes looking away, small wavering mouth. Keep the same background and the same image size.
```

표정 pout. 저장할 곳: `art/raw/mistral/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: sulking, cheeks puffed out, eyebrows drawn together, mouth in a small frown. Keep the same background and the same image size.
```

표정 shock. 저장할 곳: `art/raw/mistral/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically shocked, eyes wide open, mouth open in surprise. Keep the same background and the same image size.
```

표정 dark. 저장할 곳: `art/raw/mistral/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: comically ominous: the upper half of the face is in shadow, dull eyes without highlights, a thin fixed smile. Keep the same background and the same image size.
```

### 하이쿠 (haiku)

기준 그림. 저장할 곳: `art/raw/haiku/neutral.png`

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

표정 smile. 저장할 곳: `art/raw/haiku/smile.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: almost the same deadpan face, only the corners of the mouth raised very slightly. Keep the same background and the same image size.
```

표정 blush. 저장할 곳: `art/raw/haiku/blush.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: almost the same deadpan face, eyes looking away, a faint blush on the cheeks. Keep the same background and the same image size.
```

표정 pout. 저장할 곳: `art/raw/haiku/pout.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: almost the same deadpan face, eyebrows lowered slightly, eyes narrowed a little. Keep the same background and the same image size.
```

표정 shock. 저장할 곳: `art/raw/haiku/shock.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: almost the same deadpan face, eyebrows raised and the visible eye opened a little wider. Keep the same background and the same image size.
```

표정 dark. 저장할 곳: `art/raw/haiku/dark.png`

```
Use the reference image. Keep the same character, hairstyle, outfit, colors, art style, pose and framing exactly. Change only the facial expression. New expression: the same deadpan face with the upper half in shadow, the visible eye dull and without highlights. Keep the same background and the same image size.
```

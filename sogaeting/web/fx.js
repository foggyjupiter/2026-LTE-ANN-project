/* fx.js: 소개팅 화면 연출 15가지 (Task W3)
 *
 * window.Fx.NAMES            연출 이름 15개
 * window.Fx.play(names, opts) 이름 목록을 받아 함께 튼다. opts: {narration?: string}
 * window.Fx.clear()          재생 중인 연출을 전부 즉시 걷는다
 *
 * 약속
 * - 요소는 #fx-layer 안에만 만든다.
 * - #stage 와 #portrait 에는 fx- 로 시작하는 class 만 붙였다 뗀다.
 * - 모든 연출은 스스로 끝나고 뒤를 치운다. 어떤 경우에도 오류를 던지지 않는다.
 */
(function () {
  "use strict";

  var NAMES = ["꽃잎", "반짝이", "집중선", "줌인", "자막", "하트",
               "흔들림", "암전", "붉은 화면", "흑백", "비", "번개", "스포트라이트", "화면 깨짐", "가짜 오류창"];

  var STILL_MS = 1200;   // 움직임 줄이기 설정일 때 정지 화면을 보여 주는 시간
  var DEFAULT_ERROR = "두근거림이 허용 범위를 넘었습니다";
  var SVG_NS = "http://www.w3.org/2000/svg";   // SVG 요소를 만들 때 쓰는 이름표일 뿐, 접속하는 주소가 아니다
  var FALLBACK = { ink: "#1B2559", red: "#E23B4E", marker: "#FFE65A", paper: "#F4F7FB", accent: "#E8552D" };

  var timers = [];   // 살아 있는 setTimeout 번호
  var live = [];     // 재생 중인 연출

  /* ---------- 작은 도구 ---------- */

  function byId(id) {
    try { return document.getElementById(id); } catch (e) { return null; }
  }

  function rand(a, b) { return a + Math.random() * (b - a); }
  function irand(a, b) { return Math.floor(rand(a, b + 1)); }
  function pick(list) { return list[Math.floor(Math.random() * list.length)]; }

  function later(ms, fn) {
    var id = setTimeout(function () {
      var at = timers.indexOf(id);
      if (at >= 0) timers.splice(at, 1);
      try { fn(); } catch (e) { /* 연출은 조용히 실패한다 */ }
    }, ms);
    timers.push(id);
    return id;
  }

  function el(tag, cls, parent) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (parent) parent.appendChild(node);
    return node;
  }

  function stripFx(node) {
    if (!node || !node.classList) return;
    var names = Array.prototype.slice.call(node.classList);
    for (var i = 0; i < names.length; i++) {
      if (names[i].indexOf("fx-") === 0) node.classList.remove(names[i]);
    }
  }

  function reducedMotion() {
    try {
      return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (e) {
      return false;
    }
  }

  function readColors(node) {
    var cs = null;
    try { cs = node ? window.getComputedStyle(node) : null; } catch (e) { cs = null; }
    function v(name) {
      var s = cs ? String(cs.getPropertyValue("--" + name) || "").trim() : "";
      return s || FALLBACK[name];
    }
    return { ink: v("ink"), red: v("red"), marker: v("marker"), paper: v("paper"), accent: v("accent") };
  }

  var rgbCache = {};
  function rgbOf(color) {
    if (rgbCache[color]) return rgbCache[color];
    var out = [27, 37, 89];
    try {
      var c = document.createElement("canvas");
      c.width = 1; c.height = 1;
      var g = c.getContext("2d");
      g.fillStyle = "#1B2559";
      g.fillStyle = color;
      g.fillRect(0, 0, 1, 1);
      var d = g.getImageData(0, 0, 1, 1).data;
      out = [d[0], d[1], d[2]];
    } catch (e) { /* 기본값을 쓴다 */ }
    rgbCache[color] = out;
    return out;
  }

  /* ---------- 픽셀 그림 ---------- */

  // 글자 하나가 픽셀 하나. "." 은 빈칸.
  // 꽃잎 한 장이 팔랑 도는 장면: 정면, 비스듬히, 옆. 곧게 선 것과 기운 것 두 벌
  var PETAL_A = [
    "....d....",
    "...dld...",
    "..dllpd..",
    ".dllppqd.",
    ".dlpppqd.",
    ".dlpppqd.",
    "..dppqd..",
    "...dqd...",
    "....d...."
  ];
  var PETAL_B = [
    "....d....",
    "...dld...",
    "..dlpqd..",
    "..dlpqd..",
    "..dlpqd..",
    "..dlpqd..",
    "..dlpqd..",
    "...dqd...",
    "....d...."
  ];
  var PETAL_C = [
    "....d....",
    "....d....",
    "...dpd...",
    "...dpd...",
    "...dpd...",
    "...dpd...",
    "...dpd...",
    "....d....",
    "....d...."
  ];
  var PETAL_DA = [
    "......dd.",
    "....ddpqd",
    "...dlppqd",
    "..dllppqd",
    ".dllpppd.",
    ".dlpppqd.",
    "dlpppqd..",
    "dpqqdd...",
    ".ddd....."
  ];
  var PETAL_DB = [
    ".......dd",
    ".....ddpd",
    "....dlppd",
    "...dlppd.",
    "..dlppd..",
    ".dlppd...",
    "dlppd....",
    "dppd.....",
    ".dd......"
  ];
  var PETAL_DC = [
    ".........",
    ".......d.",
    "......dpd",
    ".....dpd.",
    "....dpd..",
    "...dpd...",
    "..dpd....",
    ".dpd.....",
    "..d......"
  ];

  var HEART = [
    ".oo...oo.",
    "orro.orro",
    "orwrorrro",
    "orrrrrrso",
    ".orrrrso.",
    "..orrso..",
    "...oso...",
    "....o...."
  ];

  var SPARK_S = [
    "...........",
    "...........",
    "...........",
    "...........",
    ".....y.....",
    "....ywy....",
    ".....y.....",
    "...........",
    "...........",
    "...........",
    "..........."
  ];
  var SPARK_M = [
    "...........",
    "...........",
    ".....y.....",
    ".....y.....",
    "....yyy....",
    "..yyywyyy..",
    "....yyy....",
    ".....y.....",
    ".....y.....",
    "...........",
    "..........."
  ];
  var SPARK_L = [
    ".....y.....",
    ".....y.....",
    ".....y.....",
    "....yyy....",
    "...yywyy...",
    "yyyywwwyyyy",
    "...yywyy...",
    "....yyy....",
    ".....y.....",
    ".....y.....",
    ".....y....."
  ];

  var DROP = [
    "...b", "...b", "...b",
    "..b.", "..b.", "..b.",
    ".b..", ".b..", ".b..",
    "b...", "b...", "b..."
  ];

  var SAW = [
    "k.....",
    "kk....",
    "kkk...",
    "kkkk..",
    "kkkkk.",
    "kkkkkk",
    "kkkkkk",
    "kkkkk.",
    "kkkk..",
    "kkk...",
    "kk....",
    "k....."
  ];

  var ERR_ICON = [
    "...ooooo...",
    "..orrrrro..",
    ".orrrrrrro.",
    "orrwrrrwrro",
    "orrrwrwrrro",
    "orrrrwrrrro",
    "orrrwrwrrro",
    "orrwrrrwrro",
    ".orrrrrrro.",
    "..orrrrro..",
    "...ooooo..."
  ];

  var CLOSE_X = [
    "k...k",
    ".k.k.",
    "..k..",
    ".k.k.",
    "k...k"
  ];

  function transposed(rows) {
    var out = [];
    for (var x = 0; x < rows[0].length; x++) {
      var line = "";
      for (var y = 0; y < rows.length; y++) line += rows[y].charAt(x);
      out.push(line);
    }
    return out;
  }

  function mirrored(rows) {
    var out = [];
    for (var y = 0; y < rows.length; y++) out.push(rows[y].split("").reverse().join(""));
    return out;
  }

  // 그림 둘레에 한 픽셀짜리 테두리를 두른다.
  function outlined(rows, ch) {
    var h = rows.length, w = rows[0].length, out = [], x, y;
    function filled(px, py) {
      return py >= 0 && py < h && px >= 0 && px < w && rows[py].charAt(px) !== ".";
    }
    for (y = -1; y <= h; y++) {
      var line = "";
      for (x = -1; x <= w; x++) {
        if (filled(x, y)) line += rows[y].charAt(x);
        else if (filled(x - 1, y) || filled(x + 1, y) || filled(x, y - 1) || filled(x, y + 1)) line += ch;
        else line += ".";
      }
      out.push(line);
    }
    return out;
  }

  var spriteCache = {};

  // frames: 같은 크기의 그림 여러 장. 가로로 이어 붙인 한 장으로 만든다.
  function sprite(key, frames, pal) {
    var id = key;
    for (var k in pal) id += "|" + k + pal[k];
    if (spriteCache[id]) return spriteCache[id];
    var h = frames[0].length, w = frames[0][0].length;
    var c = document.createElement("canvas");
    c.width = w * frames.length;
    c.height = h;
    var g = c.getContext("2d");
    for (var f = 0; f < frames.length; f++) {
      for (var y = 0; y < h; y++) {
        for (var x = 0; x < w; x++) {
          var color = pal[frames[f][y].charAt(x)];
          if (!color) continue;
          g.fillStyle = color;
          g.fillRect(f * w + x, y, 1, 1);
        }
      }
    }
    var made = { url: c.toDataURL("image/png"), w: w, h: h, n: frames.length };
    spriteCache[id] = made;
    return made;
  }

  // 픽셀 그림 한 장을 unit 배로 키워 놓는다.
  function put(box, sp, unit, cls) {
    var node = el("i", "fx-sprite " + cls);
    var s = node.style;
    s.width = sp.w * unit + "px";
    s.height = sp.h * unit + "px";
    s.backgroundImage = "url(" + sp.url + ")";
    s.backgroundSize = sp.w * sp.n * unit + "px " + sp.h * unit + "px";
    s.setProperty("--fx-sheet", -(sp.w * sp.n * unit) + "px");
    s.setProperty("--fx-frames", String(sp.n));
    s.setProperty("--fx-u", unit + "px");
    box.appendChild(node);
    return node;
  }

  function place(node, x, y) {
    node.style.left = Math.round(x) + "px";
    node.style.top = Math.round(y) + "px";
  }

  // 낮은 해상도로 그려서 unit 배로 키우는 캔버스. 계단진 픽셀 모양이 된다.
  function pixelCanvas(cw, ch, unit, cls) {
    var c = document.createElement("canvas");
    c.width = cw;
    c.height = ch;
    c.className = "fx-canvas " + cls;
    c.style.width = cw * unit + "px";
    c.style.height = ch * unit + "px";
    return c;
  }

  /* ---------- 무대 재기 ---------- */

  function measure(opts) {
    var stage = byId("stage"), layer = byId("fx-layer"), portrait = byId("portrait");
    var ref = layer || stage;
    var W = ref ? ref.clientWidth : 0, H = ref ? ref.clientHeight : 0;
    var narration = "";
    if (opts && typeof opts.narration === "string") narration = opts.narration.trim();

    var env = {
      stage: stage, layer: layer, portrait: portrait,
      W: W, H: H,
      cx: W / 2, cy: H / 2, px: 0, py: 0, pw: 0, ph: 0, hasPortrait: false,
      still: reducedMotion(),
      narration: narration,
      colors: readColors(ref)
    };

    // 초상의 자리를 #fx-layer 기준 좌표로 바꾼다. 무대가 transform 으로 줄어 있어도 맞는다.
    if (portrait && ref && W > 0 && H > 0) {
      var rr = ref.getBoundingClientRect(), pr = portrait.getBoundingClientRect();
      var kx = rr.width / W || 1, ky = rr.height / H || 1;
      var ox = layer ? 0 : ref.clientLeft, oy = layer ? 0 : ref.clientTop;
      if (pr.width > 0 && pr.height > 0) {
        env.pw = pr.width / kx;
        env.ph = pr.height / ky;
        env.px = (pr.left - rr.left) / kx - ox;
        env.py = (pr.top - rr.top) / ky - oy;
        env.cx = env.px + env.pw / 2;
        env.cy = env.py + env.ph / 2;
        env.hasPortrait = true;
      }
    }

    env.box = function (cls) {
      if (!layer || !(W > 0) || !(H > 0)) return null;
      return el("div", "fx-box " + cls + (env.still ? " fx-still" : ""), layer);
    };
    return env;
  }

  /* ---------- 연출 하나의 생애 ---------- */

  function Run(env) {
    this.env = env;
    this.boxes = [];
    this.marks = [];
    this.dead = false;
  }

  Run.prototype.box = function (cls) {
    var b = this.env.box(cls);
    if (b) this.boxes.push(b);
    return b;
  };

  Run.prototype.mark = function (node, cls) {
    if (!node || !node.classList) return;
    node.classList.add(cls);
    this.marks.push([node, cls]);
  };

  Run.prototype.unmark = function (node, cls) {
    if (!node || !node.classList) return;
    node.classList.remove(cls);
    for (var i = this.marks.length - 1; i >= 0; i--) {
      if (this.marks[i][0] === node && this.marks[i][1] === cls) this.marks.splice(i, 1);
    }
  };

  Run.prototype.end = function () {
    if (this.dead) return;
    this.dead = true;
    var i;
    for (i = 0; i < this.marks.length; i++) {
      try { this.marks[i][0].classList.remove(this.marks[i][1]); } catch (e) { /* 넘어간다 */ }
    }
    for (i = 0; i < this.boxes.length; i++) {
      try {
        if (this.boxes[i].parentNode) this.boxes[i].parentNode.removeChild(this.boxes[i]);
      } catch (e) { /* 넘어간다 */ }
    }
    this.marks = [];
    this.boxes = [];
    var at = live.indexOf(this);
    if (at >= 0) live.splice(at, 1);
  };

  // ms 뒤에 스스로 끝난다. 움직임 줄이기 설정이면 정지 화면만 짧게 보여 준다.
  Run.prototype.life = function (ms, keepWhenStill) {
    var self = this;
    var t = (this.env.still && !keepWhenStill) ? STILL_MS : ms;
    later(t, function () { self.end(); });
  };

  /* ---------- 연출 15가지 ---------- */

  var EFFECTS = {};

  // 꽃잎: 분홍 픽셀 꽃잎이 팔랑거리며 위에서 비스듬히 떨어진다. 2.9초
  EFFECTS["꽃잎"] = function (env, run) {
    var box = run.box("fx-box-petals");
    if (!box) return run.end();
    var pal = { d: "#D94F7C", p: "#FF8FB0", l: "#FFD0DC", q: "#F26B94" };
    var a = PETAL_A, b = PETAL_B, c = PETAL_C, ma = mirrored(a), mb = mirrored(b);
    var da = PETAL_DA, db = PETAL_DB, dc = PETAL_DC, ta = transposed(da), tb = transposed(db);
    var sheets = [
      sprite("petal", [a, a, a, b, c, mb, ma, ma, ma, mb, c, b], pal),
      sprite("petal-tilt", [da, da, da, db, dc, tb, ta, ta, ta, tb, dc, db], pal)
    ];
    var count = 44;
    for (var i = 0; i < count; i++) {
      var unit = pick([3, 4, 4, 5, 6]);
      var sp = sheets[i % 3 === 0 ? 0 : 1];
      var node = put(box, sp, unit, "fx-petal");
      var w = sp.w * unit, h = sp.h * unit;
      node.style.rotate = pick([0, 90, 180, 270]) + "deg";
      if (env.still) {
        place(node, rand(0, env.W - w), rand(0, env.H - h));
        node.style.backgroundPosition = -(pick([0, 0, 3, 6, 6, 9]) * w) + "px 0";
        continue;
      }
      // 한 장이 같은 길을 두 번 떨어진다. 처음부터 화면이 차 있고, 2.9초 전에 마지막 장이 빠진다
      var dur = rand(1.15, 1.4), n = Math.round(dur * 12);
      var stepY = Math.ceil((env.H + h * 2) / n / unit) * unit;
      var stepX = Math.round(stepY * rand(0.3, 0.55) / unit) * unit;
      var dx = stepX * n, dy = stepY * n;
      place(node, rand(-dx, env.W - w * 0.5), -h);
      node.style.setProperty("--fx-dx", dx + "px");
      node.style.setProperty("--fx-dy", dy + "px");
      node.style.setProperty("--fx-dur", dur.toFixed(2) + "s");
      node.style.setProperty("--fx-n", String(n));
      node.style.setProperty("--fx-delay", rand(-dur, 2.8 - 2 * dur).toFixed(2) + "s");
      node.style.setProperty("--fx-spin", rand(0.9, 1.3).toFixed(2) + "s");
    }
    run.life(2900);
  };

  // 반짝이: 십자 모양 픽셀 반짝임이 여기저기 깜빡인다. 2.4초
  EFFECTS["반짝이"] = function (env, run) {
    var box = run.box("fx-box-sparks");
    if (!box) return run.end();
    var pal = { y: env.colors.marker, w: "#FFFFFF", o: env.colors.ink };
    var s = outlined(SPARK_S, "o"), m = outlined(SPARK_M, "o"), l = outlined(SPARK_L, "o");
    var sp = sprite("spark", [s, m, l, m, s], pal);
    var count = 24;
    for (var i = 0; i < count; i++) {
      var unit = pick([3, 4, 4, 6]);
      var node = put(box, sp, unit, "fx-spark");
      var w = sp.w * unit, h = sp.h * unit;
      place(node, rand(0, env.W - w), rand(0, env.H - h));
      if (env.still) {
        node.style.backgroundPosition = -(pick([1, 2, 2]) * w) + "px 0";
        continue;
      }
      node.style.setProperty("--fx-delay", rand(0, 1.3).toFixed(2) + "s");
    }
    run.life(2400);
  };

  // 집중선: 가장자리에서 초상 쪽으로 모이는 남색 선. 세 장을 번갈아 보여 준다. 1.4초
  function linesCanvas(env) {
    var unit = 4;
    var cw = Math.ceil(env.W / unit), ch = Math.ceil(env.H / unit);
    var c = pixelCanvas(cw, ch, unit, "fx-lines-frame");
    var g = c.getContext("2d");
    var img = g.createImageData(cw, ch), d = img.data;
    var ink = rgbOf(env.colors.ink);
    var cx = env.cx / unit, cy = env.cy / unit;
    var clear = (env.hasPortrait ? Math.max(env.pw, env.ph) * 0.62 : Math.min(env.W, env.H) * 0.24) / unit;

    // 각도를 잘게 나눈 칸마다 선이 시작하는 반지름을 적어 둔다. 선이 없는 칸은 무한대.
    var BINS = 1440, inner = new Float32Array(BINS), i;
    for (i = 0; i < BINS; i++) inner[i] = Infinity;
    var a = irand(0, 10);
    while (a < BINS) {
      var width = irand(3, 13);
      var tip = clear * rand(1.0, 1.8);
      var taper = clear * rand(0.5, 1.4);
      for (i = 0; i < width; i++) {
        var t = Math.abs(i + 0.5 - width / 2) / (width / 2);
        inner[(a + i) % BINS] = tip + t * taper;
      }
      a += width + irand(8, 26);
    }

    for (var y = 0; y < ch; y++) {
      for (var x = 0; x < cw; x++) {
        var dx = x + 0.5 - cx, dy = y + 0.5 - cy;
        var r = Math.sqrt(dx * dx + dy * dy * 1.35);
        var bin = Math.floor((Math.atan2(dy, dx) + Math.PI) / (2 * Math.PI) * BINS) % BINS;
        if (r >= inner[bin]) {
          var o = (y * cw + x) * 4;
          d[o] = ink[0]; d[o + 1] = ink[1]; d[o + 2] = ink[2]; d[o + 3] = 255;
        }
      }
    }
    g.putImageData(img, 0, 0);
    return c;
  }

  EFFECTS["집중선"] = function (env, run) {
    var box = run.box("fx-box-lines");
    if (!box) return run.end();
    var frames = env.still ? 1 : 3;
    for (var f = 0; f < frames; f++) {
      var c = linesCanvas(env);
      c.style.animationDelay = (-f * 0.09).toFixed(2) + "s";
      box.appendChild(c);
    }
    run.life(1400);
  };

  // 줌인: 초상이 두 단계로 확 커졌다가 돌아온다. 1.3초
  // 자리가 넉넉하면 1.4배와 1.8배, 무대 밖으로 잘릴 것 같으면 1.25배와 1.5배
  EFFECTS["줌인"] = function (env, run) {
    var pw = env.hasPortrait ? env.pw : 176, ph = env.hasPortrait ? env.ph : 176;
    var room = Math.min(env.cx / (pw / 2), (env.W - env.cx) / (pw / 2),
                        env.cy / (ph / 2), (env.H - env.cy) / (ph / 2));
    var big = room >= 1.8;
    var steps = big ? [1.4, 1.8] : [1.25, 1.5];
    if (env.hasPortrait) {
      run.mark(env.portrait, env.still ? "fx-zoom-still" : "fx-zoom");
      if (big) run.mark(env.portrait, "fx-zoom-big");
    }
    var box = run.box("fx-box-zoom");
    if (box) {
      for (var i = env.still ? 1 : 0; i < steps.length; i++) {
        var k = steps[i];
        var w = Math.round(pw * k) + 44, h = Math.round(ph * k) + 44;
        var frame = el("div", "fx-zoom-frame fx-zoom-frame-" + (i + 1), box);
        frame.style.width = w + "px";
        frame.style.height = h + "px";
        place(frame, env.cx - w / 2, env.cy - h / 2);
        for (var c = 1; c <= 4; c++) el("i", "fx-zoom-corner fx-zoom-corner-" + c, frame);
        el("span", "fx-zoom-label", frame).textContent = k + "배";
      }
    }
    run.life(1300);
  };

  // 자막: narration 을 화면 한가운데 형광펜 띠 위에 크게 띄운다. 없으면 아무 일도 없다. 2.8초
  EFFECTS["자막"] = function (env, run) {
    if (!env.narration) return run.end();
    var box = run.box("fx-box-caption");
    if (!box) return run.end();
    var band = el("div", "fx-caption-band", box);
    var text = el("p", "fx-caption-text", band);
    text.textContent = env.narration;
    // 두 줄 안에 들어오는 가장 큰 글자를 고른다 (Galmuri14 의 정수배)
    var sizes = [56, 42, 28];
    for (var i = 0; i < sizes.length; i++) {
      text.style.fontSize = sizes[i] + "px";
      if (sizes[i] === 28) text.classList.add("fx-caption-small");
      var lines = Math.round(text.scrollHeight / (sizes[i] * 1.5));
      if (lines <= 2) break;
    }
    run.life(2800);
  };

  // 하트: 빨간 픽셀 하트가 아래에서 떠오른다. 2.8초
  EFFECTS["하트"] = function (env, run) {
    var box = run.box("fx-box-hearts");
    if (!box) return run.end();
    var sp = sprite("heart", [HEART],
                    { o: env.colors.ink, r: env.colors.red, w: "#FFFFFF", s: "#A81F36" });
    var count = 18;
    for (var i = 0; i < count; i++) {
      var unit = pick([4, 6, 6, 8]);
      var node = put(box, sp, unit, "fx-heart");
      var w = sp.w * unit, h = sp.h * unit;
      if (env.still) {
        place(node, rand(0, env.W - w), rand(env.H * 0.2, env.H - h));
        continue;
      }
      var dur = rand(1.3, 1.9), n = Math.round(dur * 11);
      var rise = rand(0.45, 0.95) * env.H + h;
      var stepY = Math.round(rise / n / unit) * unit;
      var stepX = irand(-1, 1) * unit;
      place(node, rand(w * 0.5, env.W - w * 1.5), env.H + unit);
      node.style.setProperty("--fx-dx", stepX * n + "px");
      node.style.setProperty("--fx-dy", -(stepY * n) + "px");
      node.style.setProperty("--fx-dur", dur.toFixed(2) + "s");
      node.style.setProperty("--fx-n", String(n));
      node.style.setProperty("--fx-delay", rand(0, 0.8).toFixed(2) + "s");
    }
    run.life(2800);
  };

  // 흔들림: #stage 전체가 좌우로 덜컹거린다. 양옆에 남색 톱니가 튄다. 0.8초
  EFFECTS["흔들림"] = function (env, run) {
    if (env.stage && !env.still) run.mark(env.stage, "fx-shake");
    var box = run.box("fx-box-shake");
    if (box) {
      var sp = sprite("saw", [SAW], { k: env.colors.ink });
      var sides = ["fx-saw-left", "fx-saw-right"];
      for (var i = 0; i < sides.length; i++) {
        var strip = el("div", "fx-saw " + sides[i], box);
        strip.style.backgroundImage = "url(" + sp.url + ")";
        strip.style.backgroundSize = sp.w * 4 + "px " + sp.h * 4 + "px";
      }
    }
    run.life(800);
  };

  // 암전: 모눈 칸을 네 단계로 칠해 어두워졌다가 돌아온다. 어둠 속에서 눈만 깜빡인다. 2.2초
  EFFECTS["암전"] = function (env, run) {
    var box = run.box("fx-box-blackout");
    if (!box) return run.end();
    var levels = env.still ? 3 : 4;
    for (var i = 1; i <= levels; i++) el("div", "fx-dither fx-dither-" + i, box);
    if (env.hasPortrait && !env.still) {
      var eyes = el("div", "fx-eyes", box);
      place(eyes, env.cx, env.cy);
    }
    run.life(2200);
  };

  // 붉은 화면: 붉은 막이 덮이고 맥박처럼 두 번 뛴다. 2.2초
  EFFECTS["붉은 화면"] = function (env, run) {
    var box = run.box("fx-box-red");
    if (!box) return run.end();
    el("div", "fx-film fx-red-film", box);
    el("div", "fx-film fx-red-frame", box);
    if (!env.still) el("div", "fx-film fx-red-beat", box);
    run.life(2200);
  };

  // 흑백: #stage 가 두 단계로 흑백이 되었다가 돌아온다. 망점과 위아래 띠가 덮인다. 2.6초
  EFFECTS["흑백"] = function (env, run) {
    var stage = env.stage;
    var box = run.box("fx-box-mono");
    if (box) {
      el("div", "fx-film fx-tone", box);
      el("div", "fx-bar fx-bar-top", box);
      el("div", "fx-bar fx-bar-bottom", box);
    }
    if (!stage) return run.life(2600);
    if (env.still) {
      run.mark(stage, "fx-mono-2");
    } else {
      run.mark(stage, "fx-mono-1");
      later(130, function () {
        if (run.dead) return;
        run.unmark(stage, "fx-mono-1");
        run.mark(stage, "fx-mono-2");
      });
      later(2470, function () {
        if (run.dead) return;
        run.unmark(stage, "fx-mono-2");
        run.mark(stage, "fx-mono-1");
      });
    }
    run.life(2600);
  };

  // 비: 비스듬한 픽셀 빗줄기가 쏟아지고 화면이 조금 어두워진다. 3.4초
  EFFECTS["비"] = function (env, run) {
    var box = run.box("fx-box-rain");
    if (!box) return run.end();
    el("div", "fx-film fx-rain-film", box);
    var near = sprite("drop", [DROP], { b: env.colors.ink });
    var far = sprite("drop", [DROP], { b: "#5E78C4" });
    var count = 84;
    for (var i = 0; i < count; i++) {
      var isNear = i % 2 === 0;
      var sp = isNear ? near : far, unit = isNear ? 4 : 2;
      var node = put(box, sp, unit, "fx-drop");
      var w = sp.w * unit, h = sp.h * unit;
      if (env.still) {
        place(node, rand(0, env.W - w), rand(0, env.H - h));
        continue;
      }
      var dur = isNear ? rand(0.5, 0.7) : rand(0.8, 1.1);
      var n = Math.round(dur * 14);
      var stepY = Math.ceil((env.H + h * 2) / n / (unit * 3)) * unit * 3;
      var dy = stepY * n, dx = -dy / 3;
      place(node, rand(0, env.W - dx), -h);
      node.style.setProperty("--fx-dx", dx + "px");
      node.style.setProperty("--fx-dy", dy + "px");
      node.style.setProperty("--fx-dur", dur.toFixed(2) + "s");
      node.style.setProperty("--fx-n", String(n));
      node.style.setProperty("--fx-delay", (-rand(0, dur)).toFixed(2) + "s");
    }
    run.life(3400);
  };

  // 번개: 화면이 두 번 번쩍이고 픽셀 번개 한 줄기가 내리친다. 1.5초
  function boltCanvas(env) {
    var unit = 6;
    var cw = Math.ceil(env.W / unit), ch = Math.ceil(env.H / unit);
    var c = pixelCanvas(cw, ch, unit, "fx-bolt-line");
    var g = c.getContext("2d");

    // 길게 내리긋고 옆으로 짧게 꺾이기를 되풀이하는 지그재그
    var dir = pick([-1, 1]);
    var x = cw * rand(0.3, 0.7), y = -4;
    var yEnd = ch * rand(0.6, 0.74);
    var pts = [[x, y]];
    while (y < yEnd) {
      y += rand(17, 25); x += dir * rand(7, 12);
      pts.push([x, y]);
      y += rand(0, 2); x -= dir * rand(10, 15);
      pts.push([x, y]);
    }
    y += rand(16, 22); x += dir * rand(8, 12);
    pts.push([x, y]);

    // 꺾이는 자리에서 뻗는 가지 하나
    var at = 2 * irand(1, Math.max(1, Math.floor((pts.length - 3) / 2)));
    var bx = pts[at][0], by = pts[at][1];
    var branch = [[bx, by], [bx - dir * rand(9, 13), by + rand(10, 14)], [bx - dir * rand(4, 7), by + rand(11, 14)]];
    branch[2][0] = branch[1][0] + (branch[2][0] - bx);
    branch[2][1] = branch[1][1] + (branch[2][1] - by) * 0.6;

    function stroke(path, size, color, taper) {
      g.fillStyle = color;
      for (var i = 0; i < path.length - 1; i++) {
        var x0 = path[i][0], y0 = path[i][1], x1 = path[i + 1][0], y1 = path[i + 1][1];
        var len = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)), steps = Math.max(1, Math.ceil(len));
        for (var s = 0; s <= steps; s++) {
          var t = s / steps;
          var whole = (i + t) / (path.length - 1);
          var b = taper ? Math.max(1, Math.round(size * (1 - 0.5 * whole))) : size;
          var px = Math.round(x0 + (x1 - x0) * t - b / 2), py = Math.round(y0 + (y1 - y0) * t - b / 2);
          g.fillRect(px, py, b, b);
        }
      }
    }

    // 아래로 갈수록 가늘어진다. 남색 테두리, 형광 노랑, 흰 심
    stroke(pts, 8, env.colors.ink, true);
    stroke(branch, 5, env.colors.ink, true);
    stroke(pts, 5, env.colors.marker, true);
    stroke(branch, 2, env.colors.marker, true);
    stroke(pts, 2, "#FFFFFF", true);
    return c;
  }

  EFFECTS["번개"] = function (env, run) {
    var box = run.box("fx-box-bolt");
    if (!box) return run.end();
    el("div", "fx-film fx-bolt-dark", box);
    if (!env.still) el("div", "fx-film fx-bolt-flash", box);
    box.appendChild(boltCanvas(env));
    run.life(1500);
  };

  // 스포트라이트: 초상 둘레만 남기고 어두워진다. 불빛이 자리를 찾느라 두 번 헛짚는다. 3초
  function spotCanvas(env) {
    var unit = 8, pad = 12;
    var cw = Math.ceil(env.W / unit) + pad * 2, ch = Math.ceil(env.H / unit) + pad * 2;
    var c = pixelCanvas(cw, ch, unit, "fx-spot-mask");
    c.style.left = -(pad * unit) + "px";
    c.style.top = -(pad * unit) + "px";
    var g = c.getContext("2d");
    var img = g.createImageData(cw, ch), d = img.data;
    var cx = env.cx / unit + pad, cy = env.cy / unit + pad;
    var radius = (env.hasPortrait
      ? Math.sqrt(env.pw * env.pw + env.ph * env.ph) / 2 * 0.98
      : Math.min(env.W, env.H) * 0.26) / unit;
    var ring = 2;
    for (var y = 0; y < ch; y++) {
      for (var x = 0; x < cw; x++) {
        var dx = x + 0.5 - cx, dy = y + 0.5 - cy;
        var r = Math.sqrt(dx * dx + dy * dy);
        var alpha = 205;
        if (r <= radius) alpha = 0;
        else if (r <= radius + ring) alpha = 110;
        else if (dy < 0) {
          // 위에서 내려오는 빛기둥: 조금 덜 어둡다
          var t = Math.min(1, Math.max(0, (y - 0) / Math.max(1, cy)));
          var half = radius * (0.35 + 0.65 * t);
          if (Math.abs(dx) <= half) alpha = 140;
        }
        var o = (y * cw + x) * 4;
        d[o] = 11; d[o + 1] = 16; d[o + 2] = 48; d[o + 3] = alpha;
      }
    }
    g.putImageData(img, 0, 0);
    return c;
  }

  EFFECTS["스포트라이트"] = function (env, run) {
    var box = run.box("fx-box-spot");
    if (!box) return run.end();
    box.appendChild(spotCanvas(env));
    run.life(3000);
  };

  // 화면 깨짐: 화면이 가로 조각으로 어긋나고 빨강과 청록으로 색이 갈라진다. 1.5초
  function svg(name, attrs, parent) {
    var node = document.createElementNS(SVG_NS, name);
    for (var k in attrs) node.setAttribute(k, String(attrs[k]));
    if (parent) parent.appendChild(node);
    return node;
  }

  var GLITCH_BANDS = 7, GLITCH_BARS = 6;

  // #stage 에 거는 SVG 필터. 띠마다 가로로 밀고(feDisplacementMap) 빨강 채널과 나머지를 반대로 민다.
  function glitchFilter(box) {
    var root = svg("svg", { "class": "fx-glitch-svg", width: 0, height: 0, "aria-hidden": "true" }, box);
    var filter = svg("filter", {
      id: "fx-glitch-filter", x: 0, y: 0, width: 1, height: 1,
      filterUnits: "objectBoundingBox", primitiveUnits: "userSpaceOnUse",
      "color-interpolation-filters": "sRGB"
    }, root);
    svg("feFlood", { "flood-color": "rgb(128,128,128)", result: "fx-neutral" }, filter);
    var bands = [], i;
    for (i = 0; i < GLITCH_BANDS; i++) {
      bands.push(svg("feFlood", {
        x: 0, y: -100, width: 10, height: 10, "flood-color": "rgb(128,128,128)", result: "fx-band" + i
      }, filter));
    }
    var map = svg("feMerge", { result: "fx-map" }, filter);
    svg("feMergeNode", { "in": "fx-neutral" }, map);
    var mask = svg("feMerge", { result: "fx-mask" }, filter);
    for (i = 0; i < GLITCH_BANDS; i++) {
      svg("feMergeNode", { "in": "fx-band" + i }, map);
      svg("feMergeNode", { "in": "fx-band" + i }, mask);
    }
    // scale 510 이면 빨강 값 R 이 정확히 (2R - 255)px 을 뜻한다. 정수 픽셀이라 흐려지지 않는다.
    svg("feDisplacementMap", {
      "in": "SourceGraphic", in2: "fx-map", scale: 510,
      xChannelSelector: "R", yChannelSelector: "G", result: "fx-moved"
    }, filter);
    svg("feComposite", { "in": "fx-moved", in2: "fx-mask", operator: "in", result: "fx-cut" }, filter);
    var merged = svg("feMerge", { result: "fx-torn" }, filter);
    svg("feMergeNode", { "in": "SourceGraphic" }, merged);
    svg("feMergeNode", { "in": "fx-cut" }, merged);
    svg("feColorMatrix", {
      "in": "fx-torn", type: "matrix", result: "fx-r",
      values: "1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"
    }, filter);
    var offR = svg("feOffset", { "in": "fx-r", dx: 0, dy: 0, result: "fx-r2" }, filter);
    svg("feColorMatrix", {
      "in": "fx-torn", type: "matrix", result: "fx-gb",
      values: "0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"
    }, filter);
    var offGB = svg("feOffset", { "in": "fx-gb", dx: 0, dy: 0, result: "fx-gb2" }, filter);
    svg("feComposite", {
      "in": "fx-r2", in2: "fx-gb2", operator: "arithmetic", k1: 0, k2: 1, k3: 1, k4: 0
    }, filter);
    return { bands: bands, offR: offR, offGB: offGB };
  }

  EFFECTS["화면 깨짐"] = function (env, run) {
    var box = run.box("fx-box-glitch");
    if (!box) return run.end();
    var W = env.W, H = env.H, cell = 22;
    var filt = null;
    if (env.stage) {
      try { filt = glitchFilter(box); } catch (e) { filt = null; }
    }
    var bars = [], i;
    for (i = 0; i < GLITCH_BARS; i++) bars.push(el("div", "fx-glitch-bar", box));
    var barColors = [env.colors.red, env.colors.marker, env.colors.ink, "#2FD3E6", "#2FD3E6", env.colors.paper];

    // level 2: 크게 어긋남, 1: 살짝, 0: 멀쩡
    function frame(level) {
      var b, shift;
      if (filt) {
        var active = level === 2 ? irand(4, GLITCH_BANDS) : level === 1 ? 2 : 0;
        for (b = 0; b < GLITCH_BANDS; b++) {
          var band = filt.bands[b];
          if (b >= active) {
            band.setAttribute("y", -100);
            band.setAttribute("height", 10);
            continue;
          }
          var rows = pick(level === 2 ? [1, 1, 2, 2, 3, 4] : [1, 2]);
          var top = irand(0, Math.max(0, Math.floor(H / cell) - rows)) * cell;
          shift = (level === 2 ? irand(12, 90) : irand(4, 16)) * pick([-1, 1]);
          var red = Math.max(0, Math.min(255, 128 + shift));
          band.setAttribute("x", 0);
          band.setAttribute("y", top);
          band.setAttribute("width", W);
          band.setAttribute("height", rows * cell);
          band.setAttribute("flood-color", "rgb(" + red + ",128,128)");
        }
        var split = level === 2 ? pick([6, 8, 10]) : level === 1 ? 4 : 0;
        filt.offR.setAttribute("dx", -split);
        filt.offGB.setAttribute("dx", split);
      }
      var shown = level === 2 ? GLITCH_BARS : level === 1 ? 2 : 0;
      for (b = 0; b < GLITCH_BARS; b++) {
        var s = bars[b].style;
        if (b >= shown) { s.display = "none"; continue; }
        var bw = irand(3, 24) * cell;
        s.display = "block";
        s.width = bw + "px";
        s.height = pick([4, 8, 8, 12, 22]) + "px";
        s.left = irand(-4, Math.floor(W / cell)) * cell - bw / 2 + "px";
        s.top = irand(0, Math.floor(H / 4) - 6) * 4 + "px";
        s.background = pick(barColors);
      }
    }

    frame(2);
    if (filt) run.mark(env.stage, "fx-glitch");
    if (!env.still) {
      var script = [2, 2, 1, 0, 2, 2, 0, 1, 2, 0, 0, 2, 2, 1, 0];
      for (i = 1; i < script.length; i++) {
        (function (level, at) {
          later(at, function () { if (!run.dead) frame(level); });
        })(script[i], i * 100);
      }
    }
    run.life(1500);
  };

  // 가짜 오류창: 옛 운영체제 모양의 오류창이 석 장 겹쳐 뜬다. "확인" 을 누르거나 3.9초가 지나면 닫힌다
  EFFECTS["가짜 오류창"] = function (env, run) {
    var box = run.box("fx-box-err");
    if (!box) return run.end();
    var stack = el("div", "fx-err-stack", box);
    var closeX = sprite("close", [CLOSE_X], { k: env.colors.ink });
    var icon = sprite("erricon", [ERR_ICON], { o: env.colors.ink, r: env.colors.red, w: "#FFFFFF" });

    function titleBar(parent) {
      var bar = el("div", "fx-err-bar", parent);
      el("span", "fx-err-title", bar).textContent = "오류";
      var x = el("i", "fx-err-x", bar);
      x.style.backgroundImage = "url(" + closeX.url + ")";
      x.style.backgroundSize = closeX.w * 2 + "px " + closeX.h * 2 + "px";
    }

    for (var i = 1; i <= 2; i++) titleBar(el("div", "fx-err-ghost fx-err-ghost-" + i, stack));

    var win = el("div", "fx-err-win", stack);
    win.setAttribute("role", "alertdialog");
    win.setAttribute("aria-label", "오류");
    titleBar(win);
    var body = el("div", "fx-err-body", win);
    put(body, icon, 4, "fx-err-icon");
    el("p", "fx-err-msg", body).textContent = env.narration || DEFAULT_ERROR;
    var foot = el("div", "fx-err-foot", win);
    var ok = el("button", "fx-err-ok", foot);
    ok.type = "button";
    ok.textContent = "확인";
    // 누르기 전에 입력칸의 포커스를 빼앗지 않는다
    ok.addEventListener("mousedown", function (ev) { ev.preventDefault(); });
    ok.addEventListener("click", function () { run.end(); });

    run.life(3900, true);
  };

  /* ---------- 바깥으로 내놓는 것 ---------- */

  function clear() {
    try {
      for (var i = 0; i < timers.length; i++) clearTimeout(timers[i]);
      timers = [];
      var runs = live.slice();
      for (var r = 0; r < runs.length; r++) {
        try { runs[r].end(); } catch (e) { /* 넘어간다 */ }
      }
      live = [];
      var layer = byId("fx-layer");
      if (layer) {
        while (layer.firstChild) layer.removeChild(layer.firstChild);
      }
      stripFx(byId("stage"));
      stripFx(byId("portrait"));
    } catch (e) { /* 걷다가 생긴 문제는 삼킨다 */ }
  }

  function play(names, opts) {
    try {
      clear();
      var asked = typeof names === "string" ? [names] : (Array.isArray(names) ? names : []);
      var list = [];
      for (var i = 0; i < asked.length; i++) {
        if (typeof asked[i] === "string" && NAMES.indexOf(asked[i]) >= 0 && list.indexOf(asked[i]) < 0) {
          list.push(asked[i]);
        }
      }
      if (!list.length) return;
      var env = measure(opts);
      for (var n = 0; n < list.length; n++) {
        var run = new Run(env);
        live.push(run);
        try {
          EFFECTS[list[n]](env, run);
        } catch (e) {
          run.end();
        }
      }
    } catch (e) { /* 연출이 본 화면을 멈추게 하지 않는다 */ }
  }

  window.Fx = {
    NAMES: NAMES.slice(),
    play: play,
    clear: clear
  };
})();

/* app.js: 소개팅 화면 (고르기, 대화, 엔딩)
 *
 * 서버가 돌려준 dict를 그대로 그린다. 판단은 하지 않는다.
 * 모델이 만든 글은 전부 textContent나 텍스트 노드로만 넣는다.
 */
(function () {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";
  var TYPE_MS = 25;                 // 타자 속도: 초당 약 40자
  var IDLE_MS = 3 * 60 * 1000;      // 이만큼 입력이 없으면 고르기 화면으로
  var START_SCORE = 50;
  var CITE_SPLIT = /\s?\[출처 필요\]/;
  var CONNECTION_ERROR = "서버와 연결이 끊겼습니다. 서버를 켠 터미널을 확인하세요.";
  var SKIN = "#FFE8D2";
  var INK = "#1B2559";
  var INK_SOFT = "#5A6590";
  var RED = "#E23B4E";
  var WHITE = "#FFFFFF";

  var state = {
    characters: [],
    character: null,     // 지금 판의 캐릭터 {id, name, color, ...}
    sessionId: null,
    scores: [START_SCORE],
    masked: false,       // 속마음이 가려져 나온 적이 있는가
    hasArt: false,       // 캐릭터 그림 파일이 있는가
    busy: false,
    retry: null,         // 실패한 요청을 다시 하는 함수
    typing: null,        // {timer, done}
    idleTimer: null,
    screen: "select",
    runId: 0             // 화면을 떠난 뒤 도착한 응답을 버리기 위한 번호
  };

  function $(id) { return document.getElementById(id); }

  /* ---------- 서버 ---------- */

  function api(method, path, body) {
    var options = { method: method, headers: {} };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    return fetch(path, options).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          var err = new Error((data && data.error) || CONNECTION_ERROR);
          err.status = res.status;
          throw err;
        }
        return data;
      });
    }, function () {
      var err = new Error(CONNECTION_ERROR);
      err.status = 0;
      throw err;
    });
  }

  /* ---------- 화면 전환 ---------- */

  function show(screen) {
    state.screen = screen;
    ["select", "play", "ending"].forEach(function (name) {
      $("screen-" + name).hidden = name !== screen;
    });
    if (window.Fx && window.Fx.clear) window.Fx.clear();
    stopTyping();
    resetIdle();
  }

  function resetIdle() {
    if (state.idleTimer) clearTimeout(state.idleTimer);
    state.idleTimer = null;
    if (state.screen === "select") return;
    state.idleTimer = setTimeout(function () {
      if (state.screen !== "select") showSelect();   // 판을 버린다. 결과는 남기지 않는다
    }, IDLE_MS);
  }

  /* ---------- 픽셀 얼굴 ---------- */

  function rect(svg, x, y, w, h, fill) {
    var r = document.createElementNS(SVG_NS, "rect");
    r.setAttribute("x", x);
    r.setAttribute("y", y);
    r.setAttribute("width", w);
    r.setAttribute("height", h);
    r.setAttribute("fill", fill);
    svg.appendChild(r);
  }

  /* 16x16 칸에 그리는 얼굴. 머리 색이 캐릭터의 대표색이다. */
  function pixelFace(color, face) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 16 16");
    svg.setAttribute("shape-rendering", "crispEdges");
    svg.setAttribute("aria-hidden", "true");
    var hair = color || INK;

    rect(svg, 5, 1, 6, 1, hair);        // 정수리
    rect(svg, 3, 2, 10, 11, hair);      // 뒷머리
    rect(svg, 4, 5, 8, 7, SKIN);        // 얼굴
    rect(svg, 4, 4, 8, 1, hair);        // 앞머리
    rect(svg, 4, 5, 2, 1, hair);
    rect(svg, 10, 5, 2, 1, hair);
    rect(svg, 7, 12, 2, 1, SKIN);       // 목
    rect(svg, 2, 13, 12, 3, INK);       // 블레이저
    rect(svg, 6, 13, 4, 1, WHITE);      // 깃
    rect(svg, 7, 14, 2, 1, RED);        // 리본

    if (face === "smile") {
      rect(svg, 5, 8, 2, 1, INK); rect(svg, 9, 8, 2, 1, INK);         // 감은 눈
      rect(svg, 6, 10, 1, 1, INK); rect(svg, 9, 10, 1, 1, INK); rect(svg, 7, 11, 2, 1, INK);
    } else if (face === "blush") {
      rect(svg, 5, 7, 2, 2, INK); rect(svg, 9, 7, 2, 2, INK);
      rect(svg, 4, 9, 2, 1, RED); rect(svg, 10, 9, 2, 1, RED);
      rect(svg, 7, 10, 2, 1, INK);
    } else if (face === "pout") {
      rect(svg, 6, 7, 2, 2, INK); rect(svg, 10, 7, 2, 2, INK);       // 눈을 옆으로 돌림
      rect(svg, 7, 10, 2, 1, INK); rect(svg, 6, 11, 1, 1, INK); rect(svg, 9, 11, 1, 1, INK);
    } else if (face === "shock") {
      rect(svg, 5, 6, 2, 3, INK); rect(svg, 9, 6, 2, 3, INK);         // 커진 눈
      rect(svg, 7, 10, 2, 2, INK);
    } else if (face === "dark") {
      rect(svg, 4, 5, 8, 4, INK_SOFT);                               // 얼굴 위쪽에 드리운 그늘
      rect(svg, 5, 8, 1, 1, WHITE); rect(svg, 10, 8, 1, 1, WHITE);
      rect(svg, 6, 10, 4, 1, INK);
    } else {
      rect(svg, 5, 7, 2, 2, INK); rect(svg, 9, 7, 2, 2, INK);
      rect(svg, 7, 10, 2, 1, INK);
    }
    return svg;
  }

  function drawPortrait(face) {
    var box = $("portrait");
    box.textContent = "";
    var c = state.character;
    if (state.hasArt) {
      var img = document.createElement("img");
      img.alt = "";
      img.onerror = function () {     // 이 표정의 그림만 없을 때
        box.textContent = "";
        box.appendChild(pixelFace(c.color, face));
      };
      img.src = "assets/characters/" + encodeURIComponent(c.id) + "/" + encodeURIComponent(face) + ".png";
      box.appendChild(img);
    } else {
      box.appendChild(pixelFace(c.color, face));
    }
  }

  /* 그림 파일이 있는지 한 번만 알아본다. 없으면 깨진 그림 표시 없이 픽셀 얼굴을 쓴다. */
  function probeArt(id) {
    return new Promise(function (resolve) {
      var img = new Image();
      img.onload = function () { resolve(true); };
      img.onerror = function () { resolve(false); };
      img.src = "assets/characters/" + encodeURIComponent(id) + "/neutral.png";
    });
  }

  /* ---------- 호감도 곡선 ---------- */

  function drawCurve(svg, scores) {
    svg.textContent = "";
    svg.setAttribute("shape-rendering", "crispEdges");
    var step = 148 / 7;
    var points = scores.map(function (s, i) {
      return [6 + i * step, 68 - s * 0.64];
    });
    var mid = document.createElementNS(SVG_NS, "line");   // 50점 기준선
    mid.setAttribute("x1", 0); mid.setAttribute("x2", 160);
    mid.setAttribute("y1", 36); mid.setAttribute("y2", 36);
    mid.setAttribute("stroke", "#C7D3E8");
    mid.setAttribute("stroke-width", 1);
    mid.setAttribute("stroke-dasharray", "4 4");
    svg.appendChild(mid);
    if (points.length > 1) {
      var line = document.createElementNS(SVG_NS, "polyline");
      line.setAttribute("points", points.map(function (p) { return p.join(","); }).join(" "));
      line.setAttribute("fill", "none");
      line.setAttribute("stroke", RED);
      line.setAttribute("stroke-width", 2);
      svg.appendChild(line);
    }
    points.forEach(function (p) {
      rect(svg, Math.round(p[0]) - 3, Math.round(p[1]) - 3, 6, 6, RED);
    });
  }

  /* ---------- 대사 ---------- */

  function stopTyping() {
    if (state.typing) {
      clearInterval(state.typing.timer);
      state.typing = null;
    }
  }

  function finishTyping() {
    if (!state.typing) return;
    var done = state.typing.done;
    stopTyping();
    done();
  }

  function appendHighlighted(el, text, highlights) {
    var rest = text;
    while (rest) {
      var best = null;
      for (var i = 0; i < highlights.length; i++) {
        var at = rest.indexOf(highlights[i]);
        if (at !== -1 && (best === null || at < best.at)) best = { at: at, text: highlights[i] };
      }
      if (!best) {
        el.appendChild(document.createTextNode(rest));
        return;
      }
      if (best.at > 0) el.appendChild(document.createTextNode(rest.slice(0, best.at)));
      var mark = document.createElement("mark");
      mark.textContent = best.text;
      el.appendChild(mark);
      rest = rest.slice(best.at + best.text.length);
    }
  }

  /* 다 나온 대사에 출처 딱지와 형광펜을 입힌다. */
  function decorateSay(turn) {
    var el = $("say");
    var extras = turn.extras || {};
    var text = typeof extras.say_marked === "string" ? extras.say_marked : (turn.say || "");
    var highlights = Array.isArray(extras.highlights)
      ? extras.highlights.filter(function (h) { return typeof h === "string" && h; })
      : [];
    el.textContent = "";
    var parts = text.split(CITE_SPLIT);
    parts.forEach(function (part, i) {
      appendHighlighted(el, part, highlights);
      if (i < parts.length - 1) {
        var tag = document.createElement("span");
        tag.className = "cite";
        tag.textContent = "출처 필요";
        el.appendChild(tag);
      }
    });
  }

  function typeSay(turn) {
    var el = $("say");
    var text = turn.say || "";
    stopTyping();
    el.classList.remove("is-waiting");
    el.classList.toggle("is-fallback", !!turn.fallback);
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !text) {
      decorateSay(turn);
      return;
    }
    var chars = Array.from(text);
    var shown = 0;
    el.textContent = "";
    state.typing = {
      done: function () { decorateSay(turn); },
      timer: setInterval(function () {
        shown += 1;
        el.textContent = chars.slice(0, shown).join("");
        if (shown >= chars.length) finishTyping();
      }, TYPE_MS)
    };
  }

  function setText(id, text) {
    var el = $(id);
    el.textContent = text || "";
    el.hidden = !text;
  }

  /* ---------- 답 하나 그리기 ---------- */

  function renderTurn(turn) {
    var extras = turn.extras || {};
    if (typeof extras.inner_masked === "string") state.masked = true;

    $("progress").textContent = turn.turn === 0 ? "등장" : "답 " + turn.turn + "/" + turn.total_turns;
    if (turn.turn > 0) state.scores.push(turn.score);
    $("score").textContent = turn.score;
    drawCurve($("curve"), state.scores);

    drawPortrait(turn.face || "neutral");
    setText("narration", turn.narration);
    setText("heard", turn.heard);
    setText("inner", typeof extras.inner_masked === "string" ? extras.inner_masked : turn.inner);
    typeSay(turn);

    // 빨간 펜 팝업
    var popup = $("popup");
    if (turn.popup !== null && turn.popup !== undefined && !turn.fallback) {
      $("popup-num").textContent = turn.popup;
      setText("popup-reason", turn.reason ? "사유: " + turn.reason : "");
      var notes = $("popup-notes");
      notes.textContent = "";
      (turn.notes || []).forEach(function (note) {
        var li = document.createElement("li");
        li.textContent = note;
        notes.appendChild(li);
      });
      popup.classList.toggle("is-long", String(turn.popup).length > 6);
      popup.hidden = false;
      popup.classList.remove("is-new");
      void popup.offsetWidth;            // 애니메이션을 다시 시작시킨다
      popup.classList.add("is-new");
    } else {
      popup.hidden = true;
    }

    // 선택지와 입력
    var choices = $("choices");
    choices.textContent = "";
    var list = Array.isArray(turn.choices) && turn.choices.length === 3 && !turn.finale ? turn.choices : [];
    list.forEach(function (text, i) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "choice";
      var key = document.createElement("span");
      key.className = "choice-key";
      key.textContent = String(i + 1);
      button.appendChild(key);
      button.appendChild(document.createTextNode(text));
      button.addEventListener("click", function () { send(text); });
      choices.appendChild(button);
    });
    choices.hidden = list.length === 0;
    $("input-form").hidden = !!turn.finale;
    $("finale-row").hidden = !turn.finale;
    $("skip").hidden = !!turn.finale;

    if (window.Fx && window.Fx.play) window.Fx.play(turn.fx || [], { narration: turn.narration || "" });

    if (turn.finale) $("finale-button").focus();
    else $("input").focus();
  }

  function setBusy(busy) {
    state.busy = busy;
    ["input", "send", "skip", "finale-button", "retry"].forEach(function (id) { $(id).disabled = busy; });
    Array.prototype.forEach.call(document.querySelectorAll(".choice"), function (b) { b.disabled = busy; });
  }

  function showWaiting() {
    stopTyping();
    var el = $("say");
    el.classList.remove("is-fallback");
    el.classList.add("is-waiting");
    el.textContent = "…";
  }

  function showPlayError(message, retry, label) {
    $("play-error").textContent = message;
    $("retry").textContent = label || "다시 보내기";
    $("retry").hidden = !retry;
    $("play-error-row").hidden = false;
    state.retry = retry;
  }

  function clearPlayError() {
    $("play-error-row").hidden = true;
    state.retry = null;
  }

  /* ---------- 한 판의 흐름 ---------- */

  function accentInk(hex) {
    var m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
    if (!m) return WHITE;
    var n = parseInt(m[1], 16);
    var light = 0.2126 * (n >> 16) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
    return light > 150 ? INK : WHITE;
  }

  function startSession(character) {
    var run = ++state.runId;
    state.character = character;
    state.sessionId = null;
    state.scores = [START_SCORE];
    state.masked = false;
    state.hasArt = false;

    var stage = $("stage");
    stage.style.setProperty("--accent", character.color || INK);
    stage.style.setProperty("--accent-ink", accentInk(character.color));
    $("name-plate").textContent = character.name;
    $("progress").textContent = "등장";
    $("score").textContent = START_SCORE;
    drawCurve($("curve"), state.scores);
    $("portrait").textContent = "";
    $("portrait").appendChild(pixelFace(character.color, "neutral"));
    ["narration", "heard", "inner"].forEach(function (id) { setText(id, ""); });
    $("popup").hidden = true;
    $("choices").hidden = true;
    $("input").value = "";
    $("input-form").hidden = false;
    $("finale-row").hidden = true;
    $("skip").hidden = false;
    clearPlayError();
    show("play");
    showWaiting();
    setBusy(true);

    Promise.all([
      api("POST", "/api/session", { character: character.id }),
      probeArt(character.id)
    ]).then(function (both) {
      if (run !== state.runId) return;
      state.sessionId = both[0].session_id;
      state.hasArt = both[1];
      setBusy(false);
      renderTurn(both[0].turn);
    }).catch(function (err) {
      if (run !== state.runId) return;
      setBusy(false);
      $("say").classList.remove("is-waiting");
      $("say").textContent = "";
      showPlayError(err.message, function () { startSession(character); }, "다시 시작하기");
    });
  }

  function send(text) {
    text = (text || "").trim();
    if (state.busy || !text || !state.sessionId) return;
    var run = state.runId;
    finishTyping();
    clearPlayError();
    $("input").value = "";
    showWaiting();
    setBusy(true);
    api("POST", "/api/session/" + state.sessionId + "/reply", { text: text }).then(function (turn) {
      if (run !== state.runId) return;
      setBusy(false);
      renderTurn(turn);
    }).catch(function (err) {
      if (run !== state.runId) return;
      setBusy(false);
      $("say").classList.remove("is-waiting");
      $("say").textContent = "";
      if (err.status === 409) { finish(); return; }
      if (err.status === 404) {
        showPlayError("이 판을 찾을 수 없습니다. 처음부터 다시 시작해 주세요.", showSelect, "처음으로");
        return;
      }
      if (err.status === 400) {
        showPlayError(err.message, null);
        $("input").value = text;
        $("input").focus();
        return;
      }
      showPlayError(err.message, function () { send(text); });
    });
  }

  function finish() {
    if (state.busy || !state.sessionId) return;
    var run = state.runId;
    finishTyping();
    clearPlayError();
    setBusy(true);
    api("POST", "/api/session/" + state.sessionId + "/finish").then(function (data) {
      if (run !== state.runId) return;
      setBusy(false);
      renderEnding(data.ending);
    }).catch(function (err) {
      if (run !== state.runId) return;
      setBusy(false);
      if (err.status === 404) {
        showPlayError("이 판을 찾을 수 없습니다. 처음부터 다시 시작해 주세요.", showSelect, "처음으로");
        return;
      }
      showPlayError(err.message, finish, "엔딩 다시 불러오기");
    });
  }

  function renderEnding(ending) {
    $("end-name").textContent = ending.character_name || "";
    $("end-band").textContent = ending.band_name || "";
    $("end-title").textContent = ending.title || "";
    setText("end-epilogue", ending.epilogue);
    $("end-nickname").textContent = ending.nickname || "";
    $("end-nickname-row").hidden = !ending.nickname;
    $("end-score").textContent = ending.score;
    $("end-best").textContent = ending.best_line || "";
    $("end-best-row").hidden = !ending.best_line;
    drawCurve($("end-curve"), state.scores);

    var list = $("end-inners");
    list.textContent = "";
    var inners = state.masked && Array.isArray(ending.inners)
      ? ending.inners.filter(function (s) { return typeof s === "string" && s; })
      : [];
    inners.forEach(function (text, i) {
      var li = document.createElement("li");
      li.textContent = (i + 1) + ". " + text;
      list.appendChild(li);
    });
    $("end-inners-box").hidden = inners.length === 0;

    show("ending");
    $("again").focus();
  }

  /* ---------- 고르기 화면 ---------- */

  function renderCast() {
    var cast = $("cast");
    cast.textContent = "";
    state.characters.forEach(function (c) {
      var li = document.createElement("li");
      var card = document.createElement("button");
      card.type = "button";
      card.className = "card";

      var top = document.createElement("span");
      top.className = "card-top";
      var face = document.createElement("span");
      face.className = "card-face";
      face.appendChild(pixelFace(c.color, "smile"));
      var who = document.createElement("span");
      var name = document.createElement("span");
      name.className = "card-name";
      name.textContent = c.name;
      var motif = document.createElement("span");
      motif.className = "card-motif";
      motif.textContent = c.motif;
      who.appendChild(name);
      who.appendChild(motif);
      top.appendChild(face);
      top.appendChild(who);

      var attribute = document.createElement("span");
      attribute.className = "card-attribute";
      attribute.textContent = c.attribute;
      var intro = document.createElement("span");
      intro.className = "card-intro";
      intro.textContent = c.intro;

      card.appendChild(top);
      card.appendChild(attribute);
      card.appendChild(intro);
      card.addEventListener("click", function () { startSession(c); });
      li.appendChild(card);
      cast.appendChild(li);
    });
  }

  function showSelect() {
    state.runId += 1;
    state.sessionId = null;
    setBusy(false);
    show("select");
  }

  function loadCharacters() {
    $("select-error").hidden = true;
    $("select-retry").hidden = true;
    return api("GET", "/api/characters").then(function (list) {
      state.characters = Array.isArray(list) ? list : [];
      renderCast();
    }).catch(function () {
      $("select-error").textContent = "서버에 연결할 수 없습니다. 서버를 켠 터미널을 확인하세요.";
      $("select-error").hidden = false;
      $("select-retry").hidden = false;
    });
  }

  /* ---------- 입력 받기 ---------- */

  $("input-form").addEventListener("submit", function (event) {
    event.preventDefault();
    var text = $("input").value;
    if (!text.trim()) {
      finishTyping();       // 빈 채로 Enter를 누르면 대사를 한 번에 다 보여 준다
      return;
    }
    send(text);
  });

  $("say-box").addEventListener("click", finishTyping);
  $("skip").addEventListener("click", finish);
  $("finale-button").addEventListener("click", finish);
  $("retry").addEventListener("click", function () {
    var retry = state.retry;
    clearPlayError();
    if (retry) retry();
  });
  $("again").addEventListener("click", function () {
    if (state.character) startSession(state.character);
  });
  $("other").addEventListener("click", showSelect);
  $("select-retry").addEventListener("click", loadCharacters);

  document.addEventListener("keydown", function (event) {
    resetIdle();
    if (state.screen !== "play" || state.busy || event.isComposing) return;
    // 입력창이 비어 있을 때 숫자 키 1, 2, 3으로 선택지를 고른다
    if (["1", "2", "3"].indexOf(event.key) !== -1 && $("input").value === "" &&
        !event.ctrlKey && !event.metaKey && !event.altKey) {
      var buttons = document.querySelectorAll(".choice");
      var button = buttons[Number(event.key) - 1];
      if (button && !$("choices").hidden) {
        event.preventDefault();
        button.click();
      }
    }
  });
  document.addEventListener("pointerdown", resetIdle);

  /* ---------- 시작 ---------- */

  loadCharacters().then(function () {
    var wanted = new URLSearchParams(window.location.search).get("character");
    var found = state.characters.filter(function (c) { return c.id === wanted; })[0];
    if (found) startSession(found);
    else showSelect();
  });
})();

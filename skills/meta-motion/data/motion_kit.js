/* motion_kit.js — Claude Motion 장면 모듈(kit.scene(id, {init, render(t)}))을 Motion 플레이어 밖에서 돌리는 kit 부분집합.
 *
 * 쓰는 곳 두 가지(둘 다 결정적 — 화면은 t 의 순수 함수):
 *   1) HyperFrames 하위 컴포지션: MotionKit.hyperframes('scene-id', {compId:'scene-1', duration:4.5})
 *      — paused GSAP 타임라인의 onUpdate 가 render(tl.time()) 을 부른다(0.8.162 render 가 seek 때 onUpdate 를 호출하는 것 2026-10-18 실측).
 *   2) Playwright render(t) 호스트(릴스 reel.html 식): window.render = t => MotionKit.render('scene-id', t)
 *
 * 포함: 시간·이징(seg lerp clamp clamp01 smoothstep eo ei eio eoq eox eob spring step pulse rng vnoise breathe) ·
 *       DOM(el h esc css svgLayer) · 글자(typist streamed TextFx.fadeFromRight/fadeOutLeft) · module/json · assets.url · video · fonts 스택.
 * 없음(쓰면 명확한 오류): Camera · Marks · cursor · chip · spotlight · raster · fx 캔버스 · score — 그런 장면은 Motion 안에서만 돌거나 손으로 옮긴다.
 * 출처: Motion 타입 film-api.md §3 의 이름·의미를 따랐고 구현은 독자 작성(의존성 없음).
 */
(function (root) {
  'use strict';
  var clamp = function (x, a, b) { return Math.min(b, Math.max(a, x)); };
  var clamp01 = function (x) { return clamp(x, 0, 1); };
  var seg = function (t, a, b) { return b === a ? (t >= b ? 1 : 0) : clamp01((t - a) / (b - a)); };
  var lerp = function (a, b, p) { return a + (b - a) * p; };
  var smoothstep = function (a, b, x) { var p = seg(x, a, b); return p * p * (3 - 2 * p); };
  var eo = function (x) { return 1 - Math.pow(1 - clamp01(x), 3); };
  var ei = function (x) { x = clamp01(x); return x * x * x; };
  var eio = function (x) { x = clamp01(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  var eoq = function (x) { return 1 - Math.pow(1 - clamp01(x), 4); };
  var eox = function (x) { x = clamp01(x); return x === 1 ? 1 : 1 - Math.pow(2, -10 * x); };
  var eob = function (x, o) { x = clamp01(x); var k = o == null ? 1.4 : o; return 1 + (k + 1) * Math.pow(x - 1, 3) + k * Math.pow(x - 1, 2); };
  var spring = function (x) { x = clamp01(x); return 1 - Math.exp(-6 * x) * Math.cos(12 * x); };
  var step = function (t, a) { return t >= a ? 1 : 0; };
  var pulse = function (t, a, b) { return t >= a && t < b ? 1 : 0; };
  var rng = function (seed) { var s = (seed >>> 0) || 1; return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; };
  var vnoise = function (seed) { var r = rng(seed), g = []; for (var i = 0; i < 256; i++) g.push(r() * 2 - 1);
    return function (x) { var i0 = Math.floor(x), f = x - i0, a = g[i0 & 255], b = g[(i0 + 1) & 255], p = f * f * (3 - 2 * f); return a + (b - a) * p; }; };
  var breathe = function (t, amt, period) { return 1 + (amt == null ? 0.012 : amt) * Math.sin(2 * Math.PI * t / (period == null ? 3.2 : period)); };

  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  function el(tag, o, kids) {
    var d = root.document, e = d.createElement(tag); o = o || {};
    if (o['class']) e.className = o['class'];
    if (o.style) e.style.cssText = o.style;
    if (o.text != null) e.textContent = o.text;
    if (o.html != null) e.innerHTML = o.html;
    if (o.attrs) for (var k in o.attrs) e.setAttribute(k, o.attrs[k]);
    (kids || []).forEach(function (c) { e.appendChild(c); });
    return e;
  }
  function h(html) { var t = root.document.createElement('template'); t.innerHTML = String(html).trim(); return t.content.firstElementChild; }

  // 글자: typist(text, t0, cps) — 글자별 시각, at(t) 가 친 만큼의 앞부분
  function typist(text, t0, cps, seed) {
    var r = rng(seed == null ? 7 : seed), times = [], t = t0, s = String(text);
    for (var i = 0; i < s.length; i++) { t += (1 / (cps || 24)) * (0.7 + 0.6 * r()); times.push(t); }
    var end = times.length ? times[times.length - 1] : t0;
    var count = function (tt) { var n = 0; while (n < times.length && times[n] <= tt) n++; return n; };
    return { times: times, end: end, count: count, at: function (tt) { return s.slice(0, count(tt)); } };
  }
  function streamed(text, t, t0, cps, chunk) {
    var s = String(text), n = Math.floor(Math.max(0, t - t0) * (cps || 95)); if (n <= 0) return '';
    if (n >= s.length) return s;
    var c = chunk || 7, cut = Math.floor(n / c) * c, sp = s.lastIndexOf(' ', cut); return s.slice(0, sp > cut - c ? sp : cut);
  }
  var TextFx = {
    // 단어별로 한 번 쪼개고(원문은 한 요소 안 한 문자열), 단어마다 불투명도·오른쪽 밀림을 t 로 둔다 → 끝나는 시각
    fadeFromRight: function (e, t, t0, o) {
      o = o || {}; var st = o.stagger == null ? 0.11 : o.stagger, dur = o.dur == null ? 0.5 : o.dur, dx = o.dx == null ? 26 : o.dx;
      if (!e.__words) { var ws = (e.textContent || '').split(' '); e.textContent = '';
        e.__words = ws.map(function (w, i) { var s = root.document.createElement('span'); s.style.display = 'inline-block'; s.textContent = w + (i < ws.length - 1 ? ' ' : ''); e.appendChild(s); return s; }); }
      e.__words.forEach(function (s, i) { var p = eo(seg(t, t0 + i * st, t0 + i * st + dur)); s.style.opacity = p; s.style.transform = 'translateX(' + (dx * (1 - p)) + 'px)'; });
      return t0 + (e.__words.length - 1) * st + dur;
    },
    fadeOutLeft: function (e, t, t0, o) {
      o = o || {}; var st = o.stagger == null ? 0.07 : o.stagger, dur = o.dur == null ? 0.35 : o.dur, dx = o.dx == null ? 26 : o.dx;
      if (!e.__words) TextFx.fadeFromRight(e, Infinity, 0);
      e.__words.forEach(function (s, i) { var p = ei(seg(t, t0 + i * st, t0 + i * st + dur)); s.style.opacity = 1 - p; s.style.transform = 'translateX(' + (-dx * p) + 'px)'; });
      return t0 + (e.__words.length - 1) * st + dur;
    }
  };

  var SCENES = {}, STATE = {};
  function makeKit(stage, o) {
    o = o || {};
    var mods = o.modules || {}, assets = o.assets || {};
    var kit = {
      W: o.width || 1080, H: o.height || 1920, stage: stage, dur: o.duration || 0, start: o.start || 0,
      seg: seg, lerp: lerp, clamp: clamp, clamp01: clamp01, smoothstep: smoothstep, eo: eo, ei: ei, eio: eio, eoq: eoq, eox: eox, eob: eob,
      spring: spring, step: step, pulse: pulse, rng: rng, vnoise: vnoise, breathe: breathe, typist: typist, streamed: streamed, TextFx: TextFx,
      el: el, h: h, esc: esc, typing: { times: [] },
      css: function (text) { var s = root.document.createElement('style'); s.textContent = text; stage.appendChild(s); return s; },
      svgLayer: function () { var s = root.document.createElementNS('http://www.w3.org/2000/svg', 'svg'); s.setAttribute('viewBox', '0 0 ' + kit.W + ' ' + kit.H);
        s.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none'; stage.appendChild(s); return s; },
      module: function (n) { return n in mods ? mods[n] : null; }, modules: function () { return Object.keys(mods); },
      json: function (n) { var m = mods[n]; return m == null ? null : (typeof m === 'string' ? JSON.parse(m) : m); },
      assets: { url: function (n) { return assets[n] || null; }, has: function (n) { return n in assets; }, list: function () { return Object.keys(assets); } },
      // 무음 클립 — HyperFrames 안에서는 data-start 를 그대로 쓰고(런타임이 seek), Playwright 호스트는 render 에서 currentTime 을 맞춘다
      video: function (n, vo) { vo = vo || {}; var v = root.document.createElement('video'); v.src = assets[n] || n; v.muted = true; v.playsInline = true; v.preload = 'auto';
        v.setAttribute('data-start', String(vo.start || 0)); if (vo.loop) v.loop = true; if (vo['class']) v.className = vo['class']; if (vo.style) v.style.cssText = vo.style;
        v.__start = vo.start || 0; (kit.__videos = kit.__videos || []).push(v); return v; },
      seek: function (v, s) { if (Math.abs(v.currentTime - s) > 1 / 120) v.currentTime = Math.max(0, s); },
      fonts: { sans: o.sans || 'system-ui, sans-serif', serif: o.serif || 'Georgia, serif', mono: o.mono || 'ui-monospace, monospace', display: o.display || null },
      scene: function (id, def) { SCENES[id] = def; }
    };
    return kit;
  }
  var missing = ['Camera', 'Marks', 'cursor', 'chip', 'spotlight', 'raster', 'show', 'cutPaper', 'polyLerp', 'polyStr', 'phraseRect', 'srect', 'camrect', 'center'];

  var MotionKit = {
    seg: seg, lerp: lerp, clamp: clamp, clamp01: clamp01, smoothstep: smoothstep, eo: eo, ei: ei, eio: eio, eoq: eoq, eox: eox, eob: eob, spring: spring,
    step: step, pulse: pulse, rng: rng, vnoise: vnoise, breathe: breathe, typist: typist, streamed: streamed, TextFx: TextFx, esc: esc, scenes: SCENES,
    /** 장면 모듈을 등록할 kit — 모듈 소스를 `new Function('kit', src)(kit)` 로 돌리면 그 안의 kit.scene(...) 이 SCENES 에 들어간다 */
    kit: function (stage, o) { var k = makeKit(stage, o); missing.forEach(function (n) { Object.defineProperty(k, n, { get: function () { throw new Error('motion_kit: kit.' + n + ' 은 이 셰임에 없다 — 장면을 Motion 안에서 돌리거나 손으로 옮긴다'); } }); }); return k; },
    /** 등록된 장면을 한 번 init 하고(동기 init 만 지원 — 비동기면 ready 를 기다린다) 시각 t 로 그린다 */
    mount: function (id, stage, o) {
      var def = SCENES[id]; if (!def) throw new Error('motion_kit: 등록 안 된 장면 ' + id);
      var k = makeKit(stage, o), st = STATE[id] = { kit: k, def: def, ready: true };
      if (def.init) { var r = def.init.call(def, k); if (r && typeof r.then === 'function') { st.ready = false; st.promise = r.then(function () { st.ready = true; }); } }
      return st;
    },
    render: function (id, t) {
      var st = STATE[id]; if (!st) throw new Error('motion_kit: mount 안 된 장면 ' + id);
      if (!st.ready) return false;
      st.def.render.call(st.def, t, st.kit);
      (st.kit.__videos || []).forEach(function (v) { if (!v.__hf) st.kit.seek(v, t - v.__start); });
      return true;
    },
    /** HyperFrames 하위 컴포지션 호스트: paused 타임라인 + onUpdate → render(tl.time()) · window.__timelines[compId] 등록 */
    hyperframes: function (id, o) {
      o = o || {}; var g = root.gsap; if (!g) throw new Error('motion_kit: gsap 이 먼저 로드돼야 한다');
      var stage = o.stage || root.document.getElementById(o.compId || id);
      var st = MotionKit.mount(id, stage, o); (st.kit.__videos || []).forEach(function (v) { v.__hf = true; });
      var tl = g.timeline({ paused: true }), proxy = { p: 0 };
      tl.to(proxy, { p: 1, duration: o.duration || st.kit.dur || 1, ease: 'none', onUpdate: function () { MotionKit.render(id, tl.time()); } }, 0);
      root.__timelines = root.__timelines || {}; root.__timelines[o.compId || id] = tl;
      if (st.ready) MotionKit.render(id, 0); else st.promise.then(function () { MotionKit.render(id, tl.time()); });
      return tl;
    }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = MotionKit;
  root.MotionKit = MotionKit;
})(typeof window !== 'undefined' ? window : globalThis);

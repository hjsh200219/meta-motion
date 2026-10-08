// 요청 문장 조립 한 곳 — build.mjs(빌드 때 기본 문장을 정적으로 새김)와 previews.js(입력하면 다시 조립)가 함께 쓴다.
//   {칸} → 입력값 / 비었을 때: 필수 칸은 점선 예시, 선택 칸(키 끝 ?)이 든 [[…]] 구절은 통째로 빠짐.
//   {file}·{ratio}·{color}는 공통 칸(공통 설정).
//   📋 간단 = 카드 tpl + 꼬리(비율·색) · 🔍 자세히 = 간단 본문 + [길이·크기][장면 순서][볼거리 한 번][모양][움직임][하지 말 것]
//   자세히의 재료는 motion.json 항목의 dx(장면 순서 = 미리보기 코드의 실제 타이밍, 기준 base초 → 사용자가 정한 길이에 맞춰 비율로 늘림).
//   공식 근거: hyperframes.heygen.com/prompting — 6부분 뼈대(anatomy) · 공통 움직임 머리말(examples) · 8규칙(motion).

export const TAIL = '[[ 화면 비율: {ratio}.]][[ 색·분위기: {color}.]]';

export const parseFields = (it) => (it.fields || []).map(([k, label, ex]) => ({ k: String(k).replace(/\?$/, ''), opt: /\?$/.test(String(k)), label, ex }));

// fields: [{k,opt,ex}] · vals: 사용자가 적은 칸 값 · g: 공통 설정 {ratio,color,file} · opts.noFile: 주문서(영상은 맨 위에 한 번만)
export function makeResolve(fields, vals, g, opts = {}) {
  const fm = Object.fromEntries(fields.map((f) => [f.k, f]));
  return (k) => {
    if (k === 'file' && opts.noFile) return { has: false };
    if (k in g) { const v = String(g[k] || '').trim(); return v ? { has: true, val: v, kind: 'v' } : { has: false }; }
    const f = fm[k]; if (!f) return { has: false };
    const v = String((vals || {})[k] || '').trim();
    if (v) return { has: true, val: v, kind: 'v' };
    return f.opt ? { has: false } : { has: true, val: f.ex, kind: 'ex' };
  };
}

export function composeParts(tpl, resolve) {
  const str = String(tpl || '').replace(/\[\[([\s\S]*?)\]\]/g, (m, seg) => {
    const ks = [...seg.matchAll(/\{(\w+)\}/g)].map((x) => x[1]);
    return ks.every((k) => resolve(k).has) ? seg : '';
  });
  const out = []; const re = /\{(\w+)\}/g; let last = 0, m;
  while ((m = re.exec(str))) {
    if (m.index > last) out.push({ s: str.slice(last, m.index), k: 't' });
    const r = resolve(m[1]); out.push({ s: r.has ? r.val : '', k: r.kind || 't' });
    last = re.lastIndex;
  }
  if (last < str.length) out.push({ s: str.slice(last), k: 't' });
  return out;
}

export function simpleParts(pre, tpl, resolve) {
  return [{ s: pre, k: 'tool' }, { s: ' ', k: 't' }, ...composeParts(tpl, resolve), ...composeParts(TAIL, resolve)];
}

// ---------- 🔍 자세히 ----------
const RES = { '가로 16:9': '1920x1080', '세로 9:16': '1080x1920', '정사각 1:1': '1080x1080' };
// 공통 움직임 머리말 — 공식 «shared preamble»(밀도·3겹 깊이·멈추지 않는 카메라·엇갈린 등장·반동은 모양에만·끝은 은은하게)을 우리말로.
//   카드 종류마다 맞는 것만: 영상 위 카드는 배경·카메라를 비우고, 전환은 가운데가 가장 강하게, 반복 배경은 처음=끝.
export const MOVE = {
  scene: '주인공은 크게 · 나머지는 한꺼번에 말고 조금씩 엇갈려 등장(앞 요소가 자리 잡기 전에 다음 시작) · 뒤·가운데·앞 3겹 깊이, 카메라는 내내 아주 천천히 · 튕기는 반동은 모양에만(숫자는 목표값을 넘지 않게) · 끝은 멈춘 화면 말고 숨 쉬듯 은은하게.',
  overlay: '배경은 비워 아래 영상이 보이게(카메라 이동 없음) · 요소는 조금씩 엇갈려 등장 · 튕기는 반동은 모양에만(숫자는 목표값을 넘지 않게) · 끝은 뚝 끊지 말고 부드럽게.',
  transition: '전환 한가운데가 가장 강하게 · 시작은 부드럽게 빨라지고 끝은 부드럽게 느려지게 · 앞·뒤 장면 영상 자체는 그대로.',
  loop: '마지막 장면이 첫 장면과 똑같이 이어져 반복해도 끊긴 자리가 안 보이게 · 모든 움직임은 한 바퀴 길이에 맞춰 돌고 멈추는 순간 없이.',
};
export const AVOID = '내레이션·음악·효과음 없음 · 「」 안 글자·숫자는 적은 그대로 · 글자가 화면 밖으로 잘리지 않게';

// «8초»·«1분 30초»·«90초»·«1:30» → 초. 못 읽으면 null
export function secs(txt) {
  const s = String(txt || '');
  let m = /(\d+)\s*:\s*(\d{1,2})(?!\d)/.exec(s); if (m) return +m[1] * 60 + +m[2];
  let t = 0, hit = false;
  m = /(\d+(?:\.\d+)?)\s*분/.exec(s); if (m) { t += parseFloat(m[1]) * 60; hit = true; }
  m = /(\d+(?:\.\d+)?)\s*초/.exec(s); if (m) { t += parseFloat(m[1]); hit = true; }
  return hit && t > 0 ? t : null;
}
const r1 = (x) => Math.round(x * 10) / 10;
const mmss = (x) => { const v = Math.round(x); return `${Math.floor(v / 60)}:${String(v % 60).padStart(2, '0')}`; };
function span(a, b) { return b >= 60 ? `${mmss(a)}~${mmss(b)}` : `${r1(a)}~${r1(b)}초`; }

// it = { tpl, len, dx } · fields = [{k,opt,ex}] · vals·g = makeResolve와 같음
export function detailParts(pre, it, fields, vals, g) {
  const dx = it.dx; if (!dx) return null;
  const r = makeResolve(fields, vals, g);
  const out = [{ s: pre, k: 'tool' }, { s: ' ', k: 't' }, ...composeParts(it.tpl, r)];
  const head = (label, sp = ' ') => out.push({ s: `\n[${label}]${sp}`, k: 'h' });
  const T = (s) => out.push({ s, k: 't' });

  // [길이·크기] — 지속 시간 칸(dur)이 있으면 그 값(비면 예시 길이), 없으면 dx.lenText 또는 카드의 길이
  head('길이·크기');
  const dF = fields.find((f) => f.k === 'dur');
  let D = null;
  if (dF) {
    const v = String((vals || {}).dur || '').trim();
    if (v) { out.push({ s: '전체 ', k: 't' }, { s: v, k: 'v' }); D = secs(v); }
    else { T(`전체 약 ${dF.ex}`); D = secs(dF.ex); }
  } else {
    T('전체 '); out.push(...composeParts(dx.lenText || it.len || '', r));
  }
  const ratio = String(g.ratio || '').trim();
  if (ratio) T(` · ${RES[ratio] ? `${RES[ratio]}(${ratio})` : ratio}`);
  if (dx.kind === 'overlay') T(' · 배경 투명 — 넣을 영상 위에 합성(영상이 없으면 투명 배경 webm으로)');
  T('.');

  // [장면 순서] — 시각이 있는 줄은 base초 기준 → 전체 길이 D에 맞춤.
  //   길게 늘릴 때(D > base) «머무는 줄»(hold)이 있으면 그 줄만 늘리고 뒤 줄은 그만큼 밀기(등장 속도는 그대로),
  //   없거나 줄일 때는 전체를 비율대로.
  head('장면 순서', '');
  let tf = (t) => t;
  if (dx.base > 0 && D) {
    const H = (dx.beats || []).find((b) => b.hold && !b.label);
    if (H && D > dx.base) { const ex = D - dx.base, h1 = H.t1; tf = (t) => (t >= h1 - 1e-9 ? t + ex : t); }
    else { const f = D / dx.base; tf = (t) => t * f; }
  }
  if (dx.base > 0 && !D) T(`(미리보기 ${dx.base}초 기준 — 전체 길이에 맞춰 비율대로)`);
  for (const b of dx.beats || []) {
    T('\n· ');
    if (b.label) out.push(...composeParts(b.label, r));
    else T(span(tf(b.t0), tf(b.t1)));
    T(': '); out.push(...composeParts(b.s, r));
  }
  if (dx.wow) { head('볼거리 한 번'); out.push(...composeParts(dx.wow, r)); }
  if (dx.look) { const lk = String(dx.look).trim(); head('모양'); out.push(...composeParts(/[.!?]$/.test(lk) ? lk : lk + '.', r), ...composeParts('[[ 색·분위기는 「{color}」 우선.]]', r)); }
  else if (String(g.color || '').trim()) { head('모양'); out.push(...composeParts('색·분위기: {color}.', r)); }
  head('움직임'); T(MOVE[dx.kind] || MOVE.scene);
  head('하지 말 것'); T(AVOID); if (dx.avoid) { T(' · '); out.push(...composeParts(dx.avoid, r)); }
  return out;
}

export const partsText = (parts) => parts.map((p) => p.s).join('');
export function partsHtml(parts, esc) {
  return parts.map((p) => p.k === 'tool' ? `<span class="tool">${esc(p.s)}</span>`
    : p.k === 'v' ? `<mark class="v">${esc(p.s)}</mark>`
    : p.k === 'ex' ? `<mark class="ex">${esc(p.s)}</mark>`
    : p.k === 'h' ? `<b class="h">${esc(p.s)}</b>`
    : esc(p.s)).join('');
}

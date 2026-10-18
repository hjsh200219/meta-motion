// motion_kit.js 검사 — node --test 없이 바로 실행: node test_motion_kit.mjs
// ① 이징·seg 수치 ② 가짜 DOM 위에서 장면 등록·mount·render 가 같은 t 에 같은 화면(결정성) ③ 없는 kit 멤버는 명확한 오류
import { createRequire } from 'node:module';
import { strict as assert } from 'node:assert';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

// 최소 가짜 DOM — 스타일·텍스트·자식만 흉내낸다
function fakeEl(tag) {
  const e = { tag, style: {}, children: [], attrs: {}, textContent: '', className: '',
    appendChild(c) { this.children.push(c); return c; }, append(...cs) { cs.forEach((c) => this.children.push(c)); },
    setAttribute(k, v) { this.attrs[k] = v; }, querySelector() { return null; } };
  Object.defineProperty(e.style, 'cssText', { set(v) { this._css = v; }, get() { return this._css; } });
  return e;
}
globalThis.document = { createElement: fakeEl, createElementNS: (_ns, tag) => fakeEl(tag),
  getElementById: () => fakeEl('div') };
const MotionKit = createRequire(import.meta.url)(join(here, 'data', 'motion_kit.js'));

// ① 수치
assert.equal(MotionKit.seg(1, 0, 2), 0.5);
assert.equal(MotionKit.seg(-1, 0, 2), 0);
assert.equal(MotionKit.seg(5, 0, 2), 1);
assert.equal(MotionKit.eo(1), 1); assert.equal(MotionKit.eo(0), 0);
assert.ok(Math.abs(MotionKit.eio(0.5) - 0.5) < 1e-9);
assert.ok(MotionKit.eob(0.7) > 1, 'back-out 은 도중에 1 을 넘는다');
assert.equal(MotionKit.eob(1), 1);
assert.equal(MotionKit.lerp(10, 20, 0.25), 12.5);
const r1 = MotionKit.rng(7), r2 = MotionKit.rng(7);
assert.equal(r1(), r2(), '같은 씨앗은 같은 수열');
const n = MotionKit.vnoise(3); assert.ok(Math.abs(n(1.3)) <= 1 && n(1.3) === n(1.3));
const ty = MotionKit.typist('안녕하세요', 0.5, 20);
assert.equal(ty.times.length, 5); assert.equal(ty.at(0.4), ''); assert.equal(ty.at(99), '안녕하세요');
assert.equal(MotionKit.streamed('one two three four', 10, 0), 'one two three four');

// ② 장면 모듈 — Motion 의 rough-cut.md 꼴 그대로(kit.scene(id, {init, render}))
const SRC = `const { seg, eo, lerp } = kit;
kit.scene('pour', {
  init(kit) { this.box = kit.el('div', { class: 'pour-ladle' }); kit.stage.append(this.box); this.line = kit.el('h2', { text: 'Eleven hundred degrees' }); kit.stage.append(this.line); },
  render(t, kit) { this.box.style.transform = 'rotate(' + lerp(4, -24, eo(seg(t, 0.3, 1.2))) + 'deg)'; kit.TextFx.fadeFromRight(this.line, t, 0.2); },
});`;
const stage = fakeEl('div');
const kit = MotionKit.kit(stage, { width: 1080, height: 1920, duration: 3 });
new Function('kit', SRC)(kit);  // 장면 소스는 이 repo 의 것(테스트 상수) — 외부 입력이 아니다
assert.ok(MotionKit.scenes.pour, '장면이 등록된다');
const st = MotionKit.mount('pour', stage, { width: 1080, height: 1920, duration: 3 });
assert.equal(st.ready, true);
MotionKit.render('pour', 0.75);
const a = st.def.box.style.transform, w = st.def.line.children.map((s) => s.style.opacity);
MotionKit.render('pour', 2.0); MotionKit.render('pour', 0.75);
assert.equal(st.def.box.style.transform, a, '같은 t 는 같은 화면(앞뒤로 긁어도)');
assert.deepEqual(st.def.line.children.map((s) => s.style.opacity), w);
assert.equal(st.def.line.children.length, 3, '단어 3개로 쪼갠다');
assert.ok(a.startsWith('rotate('));

// ③ 셰임에 없는 kit 멤버는 쓰는 순간 오류
assert.throws(() => kit.Camera, /motion_kit: kit\.Camera/);
assert.throws(() => MotionKit.render('nope', 0), /mount 안 된 장면/);

console.log('ok');

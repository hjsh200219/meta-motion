// 요청 카드 샘플(data/anim) 검사 + 목록용 미리보기 그림 — build_card_anim.py 뒤에 돌린다.
// 사용: Chrome 을 --headless=new --allow-file-access-from-files --remote-debugging-port=<port> 로 띄운 뒤
//   node check_card_anim.mjs <port> <list.json [{code,file,len}]> <outdir> [thumbdir]
// 카드마다 5시점 × 2비율(가로 640x360·세로 360x640) 스크린샷과 검사(애니메이션 수·오류·변화·빈 화면)를 outdir/qa.json 에,
// thumbdir 를 주면 가로 50% 시점을 480px JPEG(<코드>.jpg)로 쓴다 — preview.html 목록 그림.
import fs from 'fs'; import crypto from 'crypto';
const [port, listf, out, thumbs] = process.argv.slice(2);
const list = JSON.parse(fs.readFileSync(listf, 'utf8'));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let tabs; for (let i = 0; i < 30; i++) { try { tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); break; } catch { await sleep(300); } }
const ws = new WebSocket(tabs.find((x) => x.type === 'page').webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
let id = 0; const pend = {}; let errs = [];
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend[d.id]) { pend[d.id](d.result); delete pend[d.id]; } if (d.method === 'Runtime.exceptionThrown') errs.push(String(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text).slice(0, 160)); if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errs.push('console: ' + JSON.stringify(d.params.args.map((a) => a.value)).slice(0, 160)); };
const send = (method, params = {}) => new Promise((r) => { pend[++id] = r; ws.send(JSON.stringify({ id, method, params })); });
const ev = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true })).result?.value;
await send('Runtime.enable'); await send('Log.enable');
const res = [];
for (const it of list) {
  errs = []; const r = { code: it.code, shots: [] };
  for (const [w, h, tag] of [[640, 360, 'w'], [360, 640, 't']]) {
    await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
    await send('Page.navigate', { url: 'file://' + it.file }); await sleep(700);
    r.anims = await ev('document.getAnimations().length');
    const hashes = [];
    for (const f of [0.02, 0.25, 0.5, 0.75, 0.98]) {
      await ev(`for (const a of document.getAnimations()) a.currentTime = ${f * it.len * 1000}`); await sleep(120);
      const shot = await send('Page.captureScreenshot', { format: 'png' });
      const buf = Buffer.from(shot.data, 'base64'); const name = `${out}/${it.code}-${tag}-${Math.round(f * 100)}.png`;
      if (thumbs && tag === 'w' && f === 0.5) { const j = await send('Page.captureScreenshot', { format: 'jpeg', quality: 70, clip: { x: 0, y: 0, width: w, height: h, scale: 0.75 } }); fs.writeFileSync(`${thumbs}/${it.code}.jpg`, Buffer.from(j.data, 'base64')); }
      fs.writeFileSync(name, buf); hashes.push(crypto.createHash('md5').update(buf).digest('hex')); r.shots.push({ name, kb: Math.round(buf.length / 1024) });
    }
    r[`distinct_${tag}`] = new Set(hashes).size;
    r[`overflow_${tag}`] = await ev('document.documentElement.scrollWidth > innerWidth + 1 || document.documentElement.scrollHeight > innerHeight + 1');
  }
  r.errors = [...new Set(errs)]; r.minKB = Math.min(...r.shots.map((s) => s.kb));
  r.ok = r.anims > 0 && r.errors.length === 0 && r.distinct_w >= 2 && r.distinct_t >= 2 && r.minKB >= 3;
  res.push(r); console.error(r.code, r.ok ? 'ok' : 'NG', `anims=${r.anims} distinct=${r.distinct_w}/${r.distinct_t} minKB=${r.minKB} err=${r.errors.length}`);
}
fs.writeFileSync(`${out}/qa.json`, JSON.stringify(res, null, 1)); ws.close(); process.exit(0);

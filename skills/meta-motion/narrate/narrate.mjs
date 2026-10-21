#!/usr/bin/env node
/**
 * 장면별 내레이션 — 대본(빈 줄로 나눈 문단 = 장면, recommend 와 같은 규칙) → Fish Audio 기본 보이스 mp3(캐시)
 * → 장면마다 WAV → 한 트랙 track.wav + segments.json(장면 길이). film·HyperFrames 의 장면 길이로 그대로 쓴다.
 *
 * 보이스·배속·쉼은 shconsulting scripts/youtube/tts.mjs 기본값과 같다(SKILL 기본값 2번):
 *   Fish `s2.1-pro` · 「20대 여자_나긋나긋 쇼츠」 · prosody.speed 1.0 · atempo 1.21 · 리드인 0.8s · 장면 사이 0.6s · 문장 사이 0.35s
 * mp3 는 이어 붙이면 인코더 지연이 쌓여 어긋나므로 WAV 로 디코드한 뒤 잇는다(tts.mjs 와 같은 이유).
 *
 * 키: 환경변수 FISH_AUDIO_API_KEY — `python3 motion.py narrate` 가 setup 저장소에서 꺼내 넣어 준다(직접 부를 때만 env 필요).
 * 필요: Node 18+(fetch), ffmpeg·ffprobe.
 *
 *   node narrate.mjs <대본.txt> --out <폴더> [--dry-run] [--force] [--tempo 1.21] [--lead 0.8] [--gap 0.6] [--sent-gap 0.35]
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { join, resolve } from "node:path";
import { normalize, NORMALIZER_VERSION } from "./tts-normalize.mjs";

export const VOICE = {
  referenceId: "4e118bfbb83e401c84699c09b5f08257", // 20대 여자_나긋나긋 쇼츠 (ko)
  model: "s2.1-pro",                                // 헤더로 보낸다(body 에 넣으면 무시된다)
  prosody: { speed: 1.0 },
  format: "mp3",
};
const MIN_BYTES = 10 * 1024; // 빈 오디오가 조용히 통과하지 않게

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i === -1 ? dflt : args[i + 1]; };
const flag = (name) => args.includes(name);
const VALUED = ["--out", "--tempo", "--lead", "--gap", "--sent-gap"]; // 값을 받는 옵션 — 그 다음 낱말은 대본 경로가 아니다
const script = args.find((a, i) => !a.startsWith("--") && !VALUED.includes(args[i - 1]));
if (!script || !existsSync(script)) { console.error("사용: node narrate.mjs <대본.txt> --out <폴더> [--dry-run] [--force]"); process.exit(2); }
const OUT = resolve(opt("--out", "narration"));
const TEMPO = Number(opt("--tempo", 1.21)), LEAD = Number(opt("--lead", 0.8)), GAP = Number(opt("--gap", 0.6)), SENT_GAP = Number(opt("--sent-gap", 0.35));
const dryRun = flag("--dry-run"), force = flag("--force");

// recommend.py scenes() 와 같은 규칙 — 빈 줄로 나눈 문단, 빈 줄이 없으면 줄마다 한 장면
const raw = readFileSync(script, "utf8").trim();
let scenes = raw.split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean);
if (scenes.length === 1) scenes = scenes[0].split("\n").map((s) => s.trim()).filter(Boolean);
scenes = scenes.map((s) => s.replace(/\n+/g, " "));
if (!scenes.length) { console.error("장면 0개"); process.exit(1); }
const splitSentences = (t) => t.split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter(Boolean);

const cacheKey = (text) => createHash("sha256").update(JSON.stringify({
  text, v: NORMALIZER_VERSION, provider: "fish", referenceId: VOICE.referenceId, model: VOICE.model, prosody: VOICE.prosody,
})).digest("hex").slice(0, 32);
const probeDur = (f) => Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).toString().trim());

async function synth(text, outMp3) {
  const key = process.env.FISH_AUDIO_API_KEY;
  if (!key) { console.error("FISH_AUDIO_API_KEY 없음 — python3 motion.py setup 으로 Fish Audio 키를 저장하세요"); process.exit(1); }
  const r = await fetch("https://api.fish.audio/v1/tts", {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", model: VOICE.model },
    body: JSON.stringify({ text, reference_id: VOICE.referenceId, format: VOICE.format, prosody: VOICE.prosody }),
  });
  // 402 = API 크레딧 소진(Fish 는 웹 플랫폼 크레딧과 API 크레딧을 따로 관리한다)
  if (!r.ok) throw new Error(`Fish Audio ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const buf = Buffer.from(await r.arrayBuffer());
  if (buf.length < MIN_BYTES) throw new Error(`오디오가 너무 작다 (${buf.length}B) — 빈 응답 의심`);
  writeFileSync(outMp3, buf);
  return buf.length;
}

const cache = join(OUT, "cache");
mkdirSync(cache, { recursive: true });
console.log(`장면 ${scenes.length}개 · fish ${VOICE.model} · prosody ${VOICE.prosody.speed} × atempo ${TEMPO}`);
let billed = 0, hits = 0;
const parts = [];
for (const [i, sc] of scenes.entries()) {
  const { text, changes } = normalize(sc);
  console.log(`[${i + 1}/${scenes.length}] ${sc.length}자 → ${text.length}자 · 읽기 치환 ${changes.length}건`);
  for (const c of changes) console.log(`    ${JSON.stringify(c.from)} → ${JSON.stringify(c.to)}`);
  if (dryRun) { billed += text.length; continue; }
  const mp3s = [];
  for (const sent of splitSentences(text)) {
    const mp3 = join(cache, `${cacheKey(sent)}.mp3`);
    if (!force && existsSync(mp3)) hits++;
    else { await synth(sent, mp3); billed += sent.length; }
    mp3s.push(mp3);
  }
  parts.push({ i, text, mp3s });
}
if (dryRun) { console.log(`[dry-run] 예상 과금 ${billed}자 · 호출 없음`); process.exit(0); }

const wavs = [];
for (const p of parts) {
  const wav = join(OUT, `seg-${String(p.i + 1).padStart(2, "0")}.wav`);
  const n = p.mp3s.length;
  const sents = p.mp3s.map((_, k) => `[${k}:a]aresample=44100,aformat=channel_layouts=mono${TEMPO !== 1 ? `,atempo=${TEMPO}` : ""}${k < n - 1 && SENT_GAP > 0 ? `,apad=pad_dur=${SENT_GAP}` : ""}[s${k}]`);
  const tail = [];
  if (p.i === 0 && LEAD > 0) tail.push(`adelay=${Math.round(LEAD * 1000)}:all=1`);
  if (GAP > 0 && p.i < parts.length - 1) tail.push(`apad=pad_dur=${GAP}`);
  const graph = `${sents.join(";")};${p.mp3s.map((_, k) => `[s${k}]`).join("")}concat=n=${n}:v=0:a=1${tail.length ? "," + tail.join(",") : ""}[out]`;
  execFileSync("ffmpeg", ["-y", ...p.mp3s.flatMap((m) => ["-i", m]), "-filter_complex", graph, "-map", "[out]",
    "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "1", wav], { stdio: "ignore" });
  wavs.push(wav);
}
const durs = wavs.map(probeDur);
const list = join(OUT, "concat.txt");
writeFileSync(list, wavs.map((w) => `file '${w.replace(/\\/g, "/").replace(/'/g, "'\\''")}'`).join("\n") + "\n");
const track = join(OUT, "track.wav");
execFileSync("ffmpeg", ["-y", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", track], { stdio: "ignore" });
const segs = parts.map((p, k) => ({ scene: p.i + 1, text: scenes[p.i], spoken: p.text, file: wavs[k], dur: Number(durs[k].toFixed(3)) }));
writeFileSync(join(OUT, "segments.json"), JSON.stringify({ voice: VOICE, tempo: TEMPO, lead: LEAD, gap: GAP, track, total: probeDur(track), segments: segs }, null, 1));
console.log(`과금 ${billed}자 · 캐시 적중 ${hits} · 트랙 ${track} (${probeDur(track).toFixed(2)}s)`);
console.log(`--durs ${durs.map((d) => d.toFixed(2)).join(",")}`);

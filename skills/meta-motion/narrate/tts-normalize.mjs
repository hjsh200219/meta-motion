#!/usr/bin/env node
// meta-motion 사본 — shconsulting scripts/youtube/tts-normalize.mjs(2026-10-21). import 만 ./ko-read.mjs 로 바꿨다.
/**
 * TTS 정규화 — 내레이션 원문(`.yt.txt`)을 ElevenLabs가 바르게 읽는 문자열로 바꾼다.
 *
 * 규격 정본 = docs/youtube/youtube-channel-plan.md §4-3c (VO-NORM).
 *
 * **왜 필요한가**: `ProjectInsurnace/video`가 같은 문제에 `ttsText` 필드를 뒀지만 실제로는 안 채웠다
 * (`InsurancePremium`의 ttsText가 `"최대 30%까지"`·`"010-3122-5080으로"` 그대로다). 사람이 편마다
 * 손으로 쓰게 두면 안 쓰인다 — 그래서 필드가 아니라 **함수**다.
 *
 * **화면은 안 건드린다.** 카드가 화면을 담당하므로 시청자는 `30%`·`$50`을 정본 표기 그대로 본다.
 * 여기 결과는 오직 TTS 입력으로만 간다.
 *
 * **순서 주의 — 정규화는 게이트 *뒤*에 온다.** VO-STAT-1(정본 미근거 수치 금지)은 사람이 쓴 원문에서
 * 돌아야 한다. 정규화문에서 돌리면 `600,000 → 육십만` 변형이 정본 대조를 깨뜨린다.
 *   원고 → check-narration(게이트) → normalize(여기) → TTS
 *
 * **fail-open**: 단위 사전에 없는 조합은 **치환하지 않고 경고만** 낸다. 잘못 푸는 것이
 * 숫자로 읽히는 것보다 나쁘고, 결과가 교체 불가 mp4에 구워지기 때문이다.
 * (다른 실패 경로는 fail-closed다 — 여기만 방향이 반대이고, 의도적이다.)
 *
 * 사용:
 *   node tts-normalize.mjs "원문 문자열"     # 변환 결과 + diff 출력
 *   node tts-normalize.mjs --self-test       # N-1~N-14 픽스처 (AC24·AC27·AC28)
 *   import { normalize } from "./tts-normalize.mjs"
 */
import { readWithCounter, sinoRead, COUNTER_SYSTEM, KO_PARTICLE } from "./ko-read.mjs";

/**
 * 규칙을 고치면 **반드시 올린다.** TTS 캐시 키에 들어가므로, 안 올리면 규칙을 바꿔도
 * 낡은 오디오가 그대로 재사용된다(계획서 §4-3c 제약 2).
 */
export const NORMALIZER_VERSION = 2;

/** 영문 약어 — **화이트리스트만**. 코퍼스에 2,671건이라 일반 규칙으로 덮으면 오히려 망가진다. */
const ABBR = {
  MCP: "엠씨피", RAG: "랙", SDK: "에스디케이", SaaS: "사스",
  B2B: "비투비", B2C: "비투씨", SEO: "에스이오", LLM: "엘엘엠",
  CLI: "씨엘아이", IDE: "아이디이", KST: "케이에스티", RPA: "알피에이",
  GPT: "지피티", API: "에이피아이", UI: "유아이", UX: "유엑스",
};

/**
 * 고유명사 발음 — 영문 철자를 그대로 두면 엔진이 **다른 단어로 읽는다.**
 * 실측(2026-07-27 파일럿): `Claude`가 **"클라우드"(cloud)로 발음**됐다. 철자가 비슷한 흔한 단어로
 * 끌려간 것이라 문맥으로 교정되지 않는다 — 한글로 고정하는 수밖에 없다.
 * 대소문자 구분 없이 매칭하되, **긴 것부터** 친다(ChatGPT가 GPT보다 먼저).
 */
const PRON = {
  ChatGPT: "챗지피티", Claude: "클로드", Anthropic: "앤스로픽", OpenAI: "오픈에이아이",
  Gemini: "제미나이", Copilot: "코파일럿", Cursor: "커서", Vercel: "버셀",
  Supabase: "수파베이스", Notion: "노션", Slack: "슬랙", Figma: "피그마",
};

/**
 * 소수 읽기 — 점 뒤는 **자리마다 읽되 띄우지 않는다**(0.15 → "영 점 일오"). 띄우면 "일 오"가
 * 두 수로 들려 "일 점 일오"와 구분이 안 된다.
 */
const readDecimal = (intPart, fracPart) =>
  sinoRead(Number(intPart)) + " 점 " + [...String(fracPart)].map((d) => sinoRead(Number(d))).join("");

/** 숫자 문자열(쉼표 허용) → 한자어 읽기. 소수면 점 단위로. */
function readNumber(raw) {
  const s = String(raw).replace(/,/g, "");
  const m = s.match(/^(-?\d+)(?:\.(\d+))?$/);
  if (!m) return null;
  return m[2] !== undefined ? readDecimal(m[1], m[2]) : sinoRead(Number(m[1]));
}

/** 단위 결합 읽기. 사전 미등재면 null(원문 보존 + 경고). 소수는 한자어 고정. */
function readQuantity(raw, counter) {
  const s = String(raw).replace(/,/g, "");
  if (/\./.test(s)) {
    return COUNTER_SYSTEM[counter] ? `${readNumber(s)}${counter}` : null;
  }
  return readWithCounter(Number(s), counter);
}

const COUNTERS = Object.keys(COUNTER_SYSTEM).sort((a, b) => b.length - a.length).join("|");
/**
 * 단위 뒤 경계. 조사를 허용하지 않으면 "1.7배로"·"5개와"·"30분에"가 전부 빠진다 —
 * 실문장에서는 조사가 안 붙는 쪽이 오히려 드물다(구현 중 픽스처 4개가 이것 때문에 실패했다).
 */
const CBOUND = `(?:(?![가-힣])|(?=[${KO_PARTICLE}]))`;

/**
 * 규칙 정의. **순서가 의미를 갖는다** — 위에서 아래로 적용된다.
 * 특히 N-5(시각 `09:00`)가 N-4(비율 `16:9`)보다 **먼저** 와야 한다. 뒤집으면 시각이 "구 대 영"이 된다.
 */
function buildRules() {
  const R = [];
  const push = (id, re, fn) => R.push({ id, re, fn });

  // N-3 모델·버전 — **N-11/N-15보다 먼저.** "GPT"가 먼저 "지피티"로 바뀌면 `GPT-5.6` 패턴이 깨져
  // 하이픈이 남고 "지피티-5.6"이 된다(구현 중 실측). 결합 토큰을 항상 먼저 처리한다.
  push("N-3a", /\bv(\d+)\.(\d+)(?:\.(\d+))?\b/gi, (m, a, b, c) =>
    `버전 ${readDecimal(a, b)}${c !== undefined ? " 점 " + sinoRead(Number(c)) : ""}`);
  push("N-3b", /\b([A-Za-z][A-Za-z0-9]*)-(\d+)\.(\d+)\b/g, (m, name, a, b) =>
    `${ABBR[name.toUpperCase()] || PRON[name] || name} ${readDecimal(a, b)}`);

  // N-15 고유명사 발음. **N-11보다 먼저** — "ChatGPT"가 "GPT"로 쪼개지면 "챗지피티"를 못 만든다.
  const pronKeys = Object.keys(PRON).sort((a, b) => b.length - a.length).join("|");
  push("N-15", new RegExp(`\\b(${pronKeys})\\b`, "gi"), (m) => {
    const hit = Object.keys(PRON).find((k) => k.toLowerCase() === m.toLowerCase());
    return hit ? PRON[hit] : m;
  });

  // N-11 영문 약어 (화이트리스트).
  push("N-11", new RegExp(`\\b(${Object.keys(ABBR).join("|")})\\b`, "g"), (m, a) => ABBR[a]);

  // N-5 시각 — N-4보다 먼저. `09:00`→"아홉 시", `3시 30분`은 단위별로 체계가 갈린다(시=고유어·분=한자어).
  push("N-5", /\b(\d{1,2}):(\d{2})\b/g, (m, h, mi) => {
    const hh = readWithCounter(Number(h), "시");
    if (!hh) return m;
    return Number(mi) === 0 ? hh : `${hh} ${sinoRead(Number(mi))}분`;
  });

  // N-4 비율·화면비 `16:9` → "십육 대 구"
  push("N-4", /\b(\d+)\s?:\s?(\d+)\b/g, (m, a, b) => `${sinoRead(Number(a))} 대 ${sinoRead(Number(b))}`);

  // N-1 통화 — **접두 기호라 어순이 뒤집힌다.** 가장 확실히 깨지는 케이스.
  push("N-1", /\$\s?(\d[\d,]*(?:\.\d+)?)/g, (m, n) => `${readNumber(n)}달러`);

  // N-8 큰 수 접미사 `70k` `1.4M` — 한자어. 쉼표 천단위는 아래 N-Q가 흡수한다.
  push("N-8", /\b(\d+(?:\.\d+)?)\s?([kKmMbB])\b/g, (m, n, u) => {
    const mult = { k: 1e3, m: 1e6, b: 1e9 }[u.toLowerCase()];
    const v = Number(n) * mult;
    return Number.isInteger(v) ? sinoRead(v) : m;
  });

  // N-6 범위 `3~5편` — `~`는 묵음이다. 단위가 있으면 양쪽 모두 단위를 붙여 읽는다.
  push("N-6", new RegExp(`(\\d[\\d,]*)\\s?~\\s?(\\d[\\d,]*)\\s?(${COUNTERS})?`, "g"), (m, a, b, c) => {
    if (c) {
      const x = readQuantity(a, c), y = readQuantity(b, c);
      return x && y ? `${x}에서 ${y}` : m;
    }
    return `${readNumber(a)}에서 ${readNumber(b)}`;
  });

  // N-9 수학 기호
  push("N-9a", /±\s?(\d[\d,]*(?:\.\d+)?)/g, (m, n) => `플러스마이너스 ${readNumber(n)}`);
  push("N-9b", /\s?≤\s?/g, () => " 이하 ");
  push("N-9c", /\s?≥\s?/g, () => " 이상 ");
  push("N-9d", /\s?×\s?/g, () => " 곱하기 ");
  push("N-9e", /\s?÷\s?/g, () => " 나누기 ");

  // N-7 화살표 — 무음이라 앞뒤가 붙어 읽힌다. 쉼표로 끊어 준다(문맥 없는 안전한 최소 조치).
  push("N-7", /\s?(?:→|=>|➔)\s?/g, () => ", ");

  // N-10 슬래시 — 묵음이라 두 단어가 붙는다. **한글·한글 사이만** 친다(URL·경로 오탐 방지).
  push("N-10", /([가-힣])\/([가-힣])/g, (m, a, b) => `${a}, ${b}`);

  // N-2 · N-12 · N-13 · N-Q — 수 + 단위. 체계는 사전이 고른다(§4-3c).
  push("N-Q", new RegExp(`(\\d[\\d,]*(?:\\.\\d+)?)\\s?(${COUNTERS})${CBOUND}`, "g"), (m, n, c) => {
    const r = readQuantity(n, c);
    return r === null ? m : r;
  });
  push("N-2", /(\d[\d,]*(?:\.\d+)?)\s?%/g, (m, n) => `${readNumber(n)}퍼센트`);

  return R;
}

const RULES = buildRules();

/** 잔존 검사 — 정규화 후에도 남아 있으면 TTS가 오독한다(VO-NORM 게이트). */
const RESIDUAL = [
  { id: "통화", re: /\$/ },
  { id: "퍼센트", re: /%/ },
  { id: "화살표", re: /→|=>|➔/ },
  { id: "물결범위", re: /\d\s?~\s?\d/ },
  { id: "수학기호", re: /[±≤≥×÷]/ },
  { id: "하이픈숫자", re: /\d-\d|[A-Za-z]-\d/ },
  { id: "콜론숫자", re: /\d\s?:\s?\d/ },
];

/**
 * @param {string} input 내레이션 원문
 * @returns {{text:string, changes:Array<{id:string,from:string,to:string}>, warnings:string[]}}
 */
export function normalize(input) {
  let text = String(input ?? "");
  const changes = [];
  const warnings = [];

  for (const { id, re, fn } of RULES) {
    text = text.replace(re, (...args) => {
      const m = args[0];
      const out = fn(...args);
      if (out !== m) changes.push({ id, from: m, to: out });
      return out;
    });
  }

  // 사전 미등재 단위 — 치환 안 된 채 숫자+한글이 붙어 있으면 알린다(N-14, fail-open).
  for (const m of text.matchAll(/(\d[\d,]*(?:\.\d+)?)\s?([가-힣]{1,4})/g)) {
    if (!COUNTER_SYSTEM[m[2]]) warnings.push(`N-14 단위 사전 미등재 "${m[1]}${m[2]}" — 원문 보존`);
  }
  for (const { id, re } of RESIDUAL) {
    if (re.test(text)) warnings.push(`VO-NORM 잔존 기호(${id}) — TTS 오독 위험`);
  }

  return { text: text.replace(/[ \t]{2,}/g, " ").trim(), changes, warnings };
}

// --- self-test (AC24 · AC27 · AC28) ------------------------------------------
const FIXTURES = [
  ["N-1  통화",        "출력은 $50, 입력은 $10입니다.",   "오십달러"],
  ["N-2  퍼센트",      "최대 30% 인상",                   "삼십퍼센트"],
  ["N-3  버전",        "v21.0 기준",                      "버전 이십일 점 영"],
  ["N-3  모델",        "GPT-5.6과 비교",                  "지피티 오 점 육"],
  ["N-4  비율",        "16:9 세로 영상",                  "십육 대 구"],
  ["N-5  시각",        "09:00에 시작",                    "아홉시"],
  ["N-5  시각+분",     "3시 30분에",                      "세시 삼십분"],
  ["N-6  범위",        "3~5편을 낸다",                    "세편에서 다섯편"],
  ["N-7  화살표",      "초안 → 발행",                     "초안, 발행"],
  ["N-8  K단위",       "70k 토큰",                        "칠만"],
  ["N-8  M단위",       "1.4M 컨텍스트",                   "백사십만"],
  ["N-9  ±",           "오차는 ±0.15초",                  "플러스마이너스 영 점 일오"],
  ["N-10 슬래시",      "입력/출력 단가",                  "입력, 출력"],
  ["N-11 약어",        "MCP 서버와 RAG 파이프라인",       "엠씨피"],
  ["N-12 배수",        "1.7배로 늘었다",                  "일 점 칠배"],
  ["N-13 고유어",      "카드 5개와 3번의 시도",           "다섯개"],
  ["N-Q  천단위",      "600,000자를 쓴다",                "육십만자"],
  // AC27 — 체계 정확성. 한자어/고유어를 바꿔 읽으면 숫자를 둔 것보다 어색하다.
  ["AC27 한자어",      "5% 인상",                         "오퍼센트"],
  ["AC27 고유어",      "5개 항목",                        "다섯개"],
  // N-15 — 파일럿에서 "Claude"가 "클라우드"로 발음됐다. 고유명사는 한글로 고정해야 한다.
  ["N-15 고유명사",    "Claude가 영상을 본다",            "클로드"],
  ["N-15 긴것우선",    "ChatGPT와 GPT-5.6",              "챗지피티"],
];

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split("/").pop())) {
  const args = process.argv.slice(2);
  if (args[0] === "--self-test") {
    let pass = 0;
    for (const [name, src, expect] of FIXTURES) {
      const { text } = normalize(src);
      const ok = text.includes(expect);
      if (ok) pass++;
      console.log(`  ${ok ? "✓" : "✗"} ${name.padEnd(14)} ${src}  →  ${text}${ok ? "" : `   (기대 "${expect}")`}`);
    }
    // AC28 — 사전 미등재 단위는 원문 보존 + 경고, 배치는 계속된다.
    const oh = normalize("한 되는 7홉이다.");
    const openOk = oh.text.includes("7홉") && oh.warnings.some((w) => w.startsWith("N-14"));
    console.log(`  ${openOk ? "✓" : "✗"} AC28 fail-open  "7홉" → ${JSON.stringify(oh.text)} · 경고 ${oh.warnings.length}건`);
    // 오탐 방지 — 정상 한국어가 수사로 오인돼 깨지면 안 된다(계획서 §4-3a 경고).
    const plain = "하지만 일단 열심히 천천히 사실을 확인했다.";
    const plainOk = normalize(plain).text === plain;
    console.log(`  ${plainOk ? "✓" : "✗"} 오탐방지        ${JSON.stringify(normalize(plain).text)}`);
    const total = FIXTURES.length + 2, got = pass + (openOk ? 1 : 0) + (plainOk ? 1 : 0);
    console.log(`\n${got}/${total} 통과`);
    process.exit(got === total ? 0 : 1);
  }
  if (!args.length) { console.error('usage: node tts-normalize.mjs "텍스트" | --self-test'); process.exit(1); }
  const r = normalize(args.join(" "));
  console.log("원문  :", args.join(" "));
  console.log("정규화:", r.text);
  for (const c of r.changes) console.log(`  ${c.id.padEnd(6)} ${JSON.stringify(c.from)} → ${JSON.stringify(c.to)}`);
  for (const w of r.warnings) console.log(`  ! ${w}`);
}

// 한국어 수사 읽기(숫자 → 한글 발음) — shconsulting scripts/instagram/card-rules.mjs 「수사 읽기」 절을 그대로 옮겼다(2026-10-21, 같은 작성자).
// meta-motion narrate 가 tts-normalize.mjs 로 쓴다. 원본을 고치면 여기도 맞춘다.
// --- 수사 읽기 (숫자 → 한글) ---------------------------------------------------
// **두 체계가 있고 세는 단위가 고른다.** 틀리면 숫자를 그냥 둔 것보다 어색하다:
//   5% → "오 퍼센트"(한자어)   ·   5개 → "다섯 개"(고유어)
//   3시 30분 → "세 시 삼십 분" — **한 구절 안에서 갈린다**
// 여기(카드 규칙)에 두는 이유: `KO_NUM`이 반대 방향(한글→숫자)을 이미 담고 있어서다.
// 두 방향이 다른 파일에 있으면 단위 사전이 갈라진다(Principle 3). TTS 정규화기가 import해 쓴다.
const SINO = ["영", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"];
const NATIVE_ATTR = ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉", "열"];
const NATIVE_TENS = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"];
// 고유어 관형형은 20에서 "스무"로 바뀐다(스물 개 ✗ / 스무 개 ✓). 21부터는 다시 "스물한".
const NATIVE_TENS_ATTR = { 2: "스무" };

/** 세는 단위 → 수사 체계. 사전에 없으면 **치환하지 않는다**(fail-open, §4-3c N-14). */
const COUNTER_SYSTEM = {
  // 한자어 — 도량형·화폐·비율·시간 단위
  퍼센트: "sino", 프로: "sino", 달러: "sino", 원: "sino", 엔: "sino", 유로: "sino",
  년: "sino", 개월: "sino", 주: "sino", 분: "sino", 초: "sino", 배: "sino",
  층: "sino", 도: "sino", 회: "sino", 위: "sino", 인분: "sino", 미터: "sino",
  킬로: "sino", 그램: "sino", 퍼센트포인트: "sino", 만: "sino", 억: "sino",
  자: "sino", 토큰: "sino", 페이지: "sino",
  // 고유어 — 낱개를 세는 단위
  개: "native", 명: "native", 번: "native", 장: "native", 살: "native",
  마리: "native", 가지: "native", 대: "native", 권: "native", 벌: "native",
  병: "native", 잔: "native", 그루: "native", 켤레: "native", 채: "native",
  편: "native", 곳: "native", 군데: "native", 사람: "native", 시: "native",
  건: "native", 줄: "native", 쪽: "native", 시간: "native", 달: "native",
};

/**
 * 단위 뒤에 붙는 조사. 정규식 경계에서 이걸 허용하지 않으면 **거의 모든 실문장이 빠진다** —
 * "1.7배로"·"5개와"·"30분에"처럼 조사가 안 붙는 경우가 오히려 드물다(구현 중 실측: 21개 픽스처 중 4개 누락).
 */
const KO_PARTICLE = "을를이가은는에의로으와과도만씩째부터까지라나짜";

/** 한자어 읽기. 만 단위로 끊는다(60만·백사십만). 자릿수 1은 생략하되 "일만"은 살린다. */
function sinoRead(n) {
  if (!Number.isFinite(n)) return "";
  if (n === 0) return "영";
  if (n < 0) return "마이너스 " + sinoRead(-n);
  const under10000 = (x) => {
    let s = "";
    const units = [["천", 1000], ["백", 100], ["십", 10]];
    for (const [u, v] of units) {
      const d = Math.floor(x / v) % 10;
      if (d) s += (d === 1 ? "" : SINO[d]) + u;
    }
    const d1 = x % 10;
    if (d1) s += SINO[d1];
    return s;
  };
  let out = "";
  const groups = [["조", 1e12], ["억", 1e8], ["만", 1e4]];
  let rest = n;
  for (const [g, v] of groups) {
    const q = Math.floor(rest / v);
    if (q) { out += under10000(q) + g; rest -= q * v; }
  }
  if (rest) out += under10000(rest);
  return out;
}

/** 고유어 읽기(1~99). 관형형(단위 앞)이 기본이다 — "다섯 개"의 그 형태. */
function nativeRead(n) {
  if (!Number.isInteger(n) || n < 1 || n > 99) return null;   // 범위 밖은 호출자가 sino로 폴백
  const t = Math.floor(n / 10), o = n % 10;
  if (t === 0) return NATIVE_ATTR[o];
  const tens = (o === 0 && NATIVE_TENS_ATTR[t]) || NATIVE_TENS[t];
  return o === 0 ? tens : tens + NATIVE_ATTR[o];
}

/**
 * 수 + 단위를 체계에 맞게 읽는다. 사전 미등재 단위면 `null`을 돌려 **원문 보존**을 유도한다.
 * 고유어는 99까지만 실용적이라 그 위는 한자어로 넘어간다(백 개 ✓ / 온 개 ✗).
 */
function readWithCounter(n, counter) {
  const sys = COUNTER_SYSTEM[counter];
  if (!sys) return null;
  // **단위를 띄우지 않는다.** 맞춤법은 "이십 분"이지만 TTS는 공백에서 쉬어 "이십⏸분"으로 들린다
  // (2026-07-27 사용자 지적: "이십   분이.." → "이십분이"로 읽혀야 한다). 여기 결과는 귀로만 가므로
  // 표기법이 아니라 발화가 기준이다 — 화면 표기는 카드가 정본 그대로 담당한다.
  const k = sys === "native" ? nativeRead(n) : null;
  return `${k ?? sinoRead(n)}${counter}`;
}

export { readWithCounter, sinoRead, COUNTER_SYSTEM, KO_PARTICLE };

#!/usr/bin/env python3
"""렌더 전 검사 두 가지 — `hyperframes lint`·`check` 가 놓치는 것만 더한다(script-to-motion check.mjs·snapshot.mjs --safezone 에서 착안, MIT).
1) 비결정 코드: HyperFrames 렌더는 프레임마다 시각으로 seek 해서 찍으므로, 시계·난수·타이머에 기댄 코드는 프레임·실행마다 그림이 달라진다.
   lint 0.8.162 는 컴포지션 HTML 안의 Math.random·Date.now·new Date·performance.now·crypto.getRandomValues·gsap.utils.random·
   requestAnimationFrame 은 잡지만(2026-11-11 실측), setTimeout/setInterval·gsap.ticker·gsap.delayedCall·scrambleText(플러그인을 등록해도)는
   놓치고 <script src> 로 부른 외부 JS 파일은 아예 보지 않는다. 그래서 HTML 에는 놓치는 것만, JS 파일에는 전부 알린다.
2) 쇼츠 안전 영역(세로만): 쇼츠·릴스·틱톡 UI 가 덮는 위·아래·오른쪽 띠에 글자가 들어가는지. `hyperframes check --caption-zone` 이
   띠 하나만 받으므로(여러 번 넘기면 마지막만 쓴다 — 실측) 띠마다 한 번씩 돌린다. 루트 아래 클립마다 가운데 시각을 본다(seeks()).
   caption-zone 은 글자를 담은 상자로 걸므로 글자 rect 로 다시 거른다(classify()). 띠 두께는 LIMITS — 늘 가려지는 곳은 오류, 여유 기준은 경고.
   종료 코드 1 = 비결정 코드 오류·안전 영역 오류·검사 실패(--strict 면 경고도).
실행: python3 motion.py check <프로젝트> [--no-zone] [--strict] [--top 240] [--top-error 120] [--bottom 480] [--bottom-error 320] [--right 120] [--json]"""
import json, re, subprocess, sys
from pathlib import Path

HF = 'hyperframes@0.8.162'  # build_hf.py·SKILL.md 의 고정 버전과 같게
SKIP_DIRS = {'node_modules', '.hyperframes', 'out', 'renders', 'dist', 'vendor', '_src', '.git'}
BUNDLE = re.compile(r'\.(min|iife|bundle|umd)\.m?js$')
# (코드, 정규식, 심각도, HTML 에서도 보나, 설명) — HTML 에서 안 보는 것은 lint 가 이미 잡는 것
RULES = [
    ('math_random', r'\bMath\.random\s*\(', 'error', False, 'Math.random() — 시드 고정 난수(예: mulberry32(seed))로'),
    ('date_now', r'\bDate\.now\s*\(', 'error', False, 'Date.now() — 타임라인 시간(tl.time())으로'),
    ('new_date', r'\bnew\s+Date\s*\(\s*\)', 'error', False, 'new Date() — 타임라인 시간으로'),
    ('performance_now', r'\bperformance\.now\s*\(', 'error', False, 'performance.now() — 타임라인 시간으로'),
    ('crypto_random', r'\bcrypto\.getRandomValues\s*\(', 'error', False, 'crypto.getRandomValues() — 시드 고정 난수로'),
    ('gsap_random', r'\bgsap\.utils\.random\s*\(', 'error', False, 'gsap.utils.random() — 시드 고정 난수로'),
    ('raf', r'\brequestAnimationFrame\s*\(', 'error', False, 'requestAnimationFrame — 벽시계로 돈다. 움직임은 일시정지된 GSAP 타임라인에'),
    ('gsap_ticker', r'\bgsap\.ticker\b', 'error', True, 'gsap.ticker — 벽시계로 돈다. seek 하면 상태가 어긋난다'),
    ('scramble_text', r'\bscrambleText\s*:', 'error', True, 'scrambleText — 섞는 글자를 Math.random 으로 고른다. 같은 시각이라도 seek 마다 글자가 다르다(글자 순번·프레임으로 만든 해시로 직접)'),
    ('gsap_delayed_call', r'\bgsap\.delayedCall\s*\(', 'warning', True, 'gsap.delayedCall — 전역 시계로 돈다. 타임라인의 tl.call(f, null, 초) 로'),
    ('timer', r'\bset(?:Timeout|Interval)\s*\(', 'warning', True, 'setTimeout/setInterval — 렌더 seek 와 무관하게 돈다. 서체·이미지 기다리기 같은 준비 코드가 아니면 타임라인으로'),
]
COMPILED = [(c, re.compile(p), s, h, m) for c, p, s, h, m in RULES]


def _code_part(line):
    """줄 주석(//) 뒤는 버린다 — 「Math.random 대신 시드」 같은 설명을 잡지 않게. URL(https://) 의 // 는 남긴다."""
    m = re.search(r'(?<![:\'"])//', line)
    return line[:m.start()] if m else line


def _walk(proj):
    """(파일, 상대 경로, 건너뛰나) — 한 줄이 1000자를 넘는 JS·.min/.iife/.bundle/.umd 이름은 압축된 남의 라이브러리 묶음
    (레지스트리 lib/shaders.iife.js 등)이라 건너뛰되, 장면 모듈에 경로·base64 를 박아 넣은 경우일 수 있어 skipped() 로 따로 알린다."""
    proj = Path(proj)
    for f in sorted(proj.rglob('*')):
        rel = f.relative_to(proj)
        if not f.is_file() or set(rel.parts[:-1]) & SKIP_DIRS or f.suffix.lower() not in ('.html', '.htm', '.js', '.mjs'): continue
        packed = bool(BUNDLE.search(f.name)) or (f.suffix.lower() not in ('.html', '.htm') and
                                                 max(map(len, f.read_text(encoding='utf-8', errors='replace').splitlines() or [''])) > 1000)
        yield f, rel.as_posix(), packed


def files(proj):
    return [(f, rel) for f, rel, packed in _walk(proj) if not packed]


def skipped(proj):
    """긴 줄 때문에 건너뛴 파일만(이름이 .min/.iife 등인 것은 라이브러리가 분명해 알리지 않는다 — gsap.min.js 가 모든 프로젝트에 있다)."""
    return [rel for _, rel, packed in _walk(proj) if packed and not BUNDLE.search(rel)]


def scan(proj):
    proj = Path(proj)
    out = []
    for f, rel in files(proj):
        html = f.suffix.lower() in ('.html', '.htm')
        for n, line in enumerate(f.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            code = _code_part(line)
            for c, rx, sev, in_html, msg in COMPILED:
                if (in_html or not html) and rx.search(code):
                    out.append({'file': rel, 'line': n, 'code': c, 'severity': sev, 'message': msg, 'text': line.strip()[:120]})
    return out


def size(proj):
    idx = Path(proj) / 'index.html'
    m = re.search(r'data-width="(\d+)"[^>]*?data-height="(\d+)"', idx.read_text(encoding='utf-8')) if idx.exists() else None
    return (int(m.group(1)), int(m.group(2))) if m else None


def _f(v):
    return f'{v:.4f}'.rstrip('0').rstrip('.') if v not in (0, 1) else str(int(v))


def seeks(html):
    """caption-zone 의 seek 는 영상 전체 길이에 대한 비율이고 그 시각들만 본다(2026-11-11 실측 — seek=.5 는 73.04초 영상의 36.52초 한 곳뿐).
    그래서 루트 아래 클립(장면·자막·로고 등, 오디오·비디오 제외)마다 가운데 시각을 비율로 모아 넘긴다. 클립이 없으면 가운데 한 번."""
    root = re.search(r'<[^>]*data-composition-id="[^"]+"[^>]*>', html)
    total = float((re.search(r'data-duration="([\d.]+)"', root.group(0)) or [0, 0])[1]) if root else 0
    mids = []
    for tag, attrs in re.findall(r'<(\w+)([^>]*\bdata-start="[\d.]+"[^>]*)>', html):
        if tag.lower() in ('audio', 'video') or (root and attrs in root.group(0)): continue
        st, du = re.search(r'data-start="([\d.]+)"', attrs), re.search(r'data-duration="([\d.]+)"', attrs)
        if du: mids.append(float(st.group(1)) + float(du.group(1)) / 2)
    total = total or max([m * 2 for m in mids] or [0])
    fr = sorted({round(m / total, 4) for m in mids if total and 0 <= m <= total})[:80]  # 80곳 넘으면 앞에서 자른다(검사 시간)
    return ','.join(f'{x:g}' for x in fr) or '0.5'


# 쇼츠·릴스·틱톡 UI 띠(1080x1920 기준 px, 2026-11-11 정함 — 근거 SKILL.md 「렌더 전 검사」):
# 오류 = 일반 게시물에서 늘 가려지는 곳(위 상태바·탭 120 · 아래 계정·설명·음악 320 · 오른쪽 좋아요·댓글·공유 버튼 열 120px×세로 45~83% — Claude Motion 안전 영역 오른쪽 120·TikTok 광고 템플릿 좌우 120 과 같음)
# 경고 = 광고·여유 기준(위 240 — TikTok 광고 템플릿 위 240 · 아래 480 — 광고 CTA·설명이 길어진 경우)
LIMITS = {'top': 240, 'top_error': 120, 'bottom': 480, 'bottom_error': 320, 'right': 120, 'right_y': (0.45, 0.83)}


def zones(w, h, top=None, bottom=None, right=None, seek='0.5'):
    """세로 영상의 띠 → caption-zone 문자열. 위·아래는 경고 두께로 한 번 돌리고 classify() 가 글자 깊이로 오류/경고를 가른다
    (띠당 hyperframes check 한 번 · 약 8초). 0 을 주면 그 띠를 뺀다."""
    if h <= w: return []
    top, bottom, right = (LIMITS[k] if v is None else v for k, v in (('top', top), ('bottom', bottom), ('right', right)))
    y0, y1 = LIMITS['right_y']
    out = []
    if top: out.append(('top', f'x0=0;y0=0;x1=1;y1={_f(top / h)};severity=warning;seek={seek}'))
    if bottom: out.append(('bottom', f'x0=0;y0={_f(1 - bottom / h)};x1=1;y1=1;severity=warning;seek={seek}'))
    if right: out.append(('right', f'x0={_f(1 - right / w)};y0={_f(y0)};x1=1;y1={_f(y1)};severity=warning;seek={seek}'))
    return out


def classify(side, finding, w, h, lim):
    """글자 rect 로 오류·경고·해당 없음(None)을 가른다. caption-zone 은 글자를 담은 상자로 걸어서(폭 100% div 안 가운데 글자도
    오른쪽 띠에 걸림 — 2026-11-11 실측) 그대로 쓰면 오탐이 난다. 스케일 1080x1920 기준 값을 프로젝트 크기에 맞춰 늘린다."""
    r, sx, sy = finding.get('rect') or {}, w / 1080, h / 1920
    if not r: return 'warning'
    if side == 'top':
        if r['top'] >= lim['top'] * sy: return None
        return 'error' if r['top'] < lim['top_error'] * sy else 'warning'
    if side == 'bottom':
        gap = h - r['bottom']
        if gap >= lim['bottom'] * sy: return None
        return 'error' if gap < lim['bottom_error'] * sy else 'warning'
    y0, y1 = lim['right_y']
    inside = r['right'] > w - lim['right'] * sx and r['bottom'] > y0 * h and r['top'] < y1 * h
    return 'error' if inside else None


def run_zone(proj, spec):
    r = subprocess.run(['npx', '--yes', HF, 'check', str(proj), '--json', '--no-contrast', '--caption-zone', spec],
                       capture_output=True, text=True)
    s = r.stdout[r.stdout.find('{'):] if '{' in r.stdout else ''
    try: d = json.loads(s)
    except ValueError: return None, (r.stderr or r.stdout).strip()[-300:]
    if d.get('browserSkipped'): return None, 'lint 오류로 브라우저 검사를 건너뜀 — 먼저 npx --yes ' + HF + ' lint 를 통과시킨다'
    return [f for f in d.get('layout', {}).get('findings', []) if f.get('code') == 'caption_zone_collision'], None


def main(args):
    if not args or args[0].startswith('--'): sys.exit(__doc__.split('실행: ')[1])
    proj = Path(args[0]).resolve()
    keys = ('--top', '--top-error', '--bottom', '--bottom-error', '--right')
    opt = {args[i][2:].replace('-', '_'): args[i + 1] for i in range(1, len(args) - 1) if args[i] in keys}
    res = {'determinism': scan(proj), 'skipped': skipped(proj), 'zones': {}}
    errors = sum(f['severity'] == 'error' for f in res['determinism'])
    wh = size(proj)
    if '--no-zone' not in args and wh:
        seek = seeks((proj / 'index.html').read_text(encoding='utf-8'))
        lim = dict(LIMITS, **{k: int(v) for k, v in opt.items()})
        for name, spec in zones(*wh, seek=seek, **{k: lim[k] for k in ('top', 'bottom', 'right')}):
            found, err = run_zone(proj, spec)
            kept = []
            for f in found or []:
                sev = classify(name, f, *wh, lim)
                if sev: kept.append(dict(f, severity='error' if '--strict' in args else sev))
            res['zones'][name] = {'spec': spec, 'findings': kept, 'boxes_only': len(found or []) - len(kept), 'error': err}
            # 오류 띠(늘 가려지는 곳)만 실패. 경고 띠는 --strict 일 때만
            errors += sum(f['severity'] == 'error' for f in kept) + (1 if err else 0)
    if '--json' in args:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for f in res['determinism']:
            print(f"{f['severity']}\t{f['file']}:{f['line']}\t{f['message']}\n\t\t{f['text']}")
        if res['skipped']: print('건너뜀(압축 라이브러리로 봄 — 장면 코드면 줄을 나눠 다시 검사): ' + ' · '.join(res['skipped']))
        for name, z in res['zones'].items():
            if z['error']: print(f'error\t안전 영역 {name}\t검사 실패: {z["error"]}')
            for f in z['findings'] or []:
                r = f.get('rect') or {}
                where = f"위에서 {r.get('top', 0):.0f}px" if name == 'top' else f"아래에서 {wh[1] - r.get('bottom', 0):.0f}px" if name == 'bottom' else f"오른쪽 끝 x={r.get('right', 0):.0f}"
                print(f"{f['severity']}\t안전 영역 {name}\t{f.get('time', '?')}초 {f.get('selector', '')} 「{f.get('text', '')[:30]}」 {where}")
        zs = ', '.join(f"{n} 오류 {sum(f['severity'] == 'error' for f in z['findings'])}·경고 {sum(f['severity'] == 'warning' for f in z['findings'])}" for n, z in res['zones'].items()) or ('가로라 안 봄' if wh and wh[1] <= wh[0] else '안 봄')
        print(f"\n비결정 코드 {len(res['determinism'])}건(오류 {sum(f['severity'] == 'error' for f in res['determinism'])}) · 안전 영역 {zs} · "
              f"lint·대비·겹침은 npx --yes {HF} check 로 따로", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main(sys.argv[1:])

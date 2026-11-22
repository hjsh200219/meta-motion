#!/usr/bin/env python3
"""herk-edit-kit 스타일 카드 406장(MIT + Herk Edit Kit Use Permission © 2026 Nate Herk) — 원본 두 스타일(종이 콜라주 해설·어두운 글로우)을
meta-motion 색·서체 템플릿으로 바꿔 쓰는 도구. 원본 LICENSE 「Note on brand assets」대로 AIS(AI Automation Society) 브랜드 자산은 쓰지 않는다:
  - 스타일 tokens.css 의 AIS 파랑(#37BDF8 · 55,189,248)과 카드 HTML 에 박힌 같은 색 리터럴 → 템플릿 강조색
  - 서체(Fraunces·Archivo·Caveat·Plus Jakarta Sans·Inter, Google Fonts @import) → 템플릿 한글 서체(@font-face, 프로젝트 fonts/ 로 복사)
  - 칸(data-slot) 글 → 사용자 값(카드 예시값은 한국어로 새로 지은 것 — 원본 자리표시자의 이름·계정·통계는 옮기지 않는다)
  - 칸 밖에 브랜드 문구가 박힌 카드(SKIP)는 싣지 않는다
원본은 싣지 않고 고정 커밋 캐시(~/.cache/meta-motion/herk-edit-kit, style-library 만 받는 부분 클론)에서 읽는다.
실행: python3 build_herk.py sync                        캐시 맞추기(790MB repo 중 style-library·licenses 만)
      python3 build_herk.py list                        카드 목록(registry.json)
      python3 build_herk.py card <코드> --out <폴더> [--template <id>] [k=값 …]   쓸 컴포지션 한 장(토큰·서체·칸 바꾼 HTML + fonts/)"""
import json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = 'https://github.com/nateherkai/herk-edit-kit'
COMMIT = '10511e5af86fc47756ea89803b397422e2d89284'
CACHE = Path.home() / '.cache' / 'meta-motion' / 'herk-edit-kit'
LIB = CACHE / 'style-library'
STYLE = {'vox-explainer': ('paper', 'beige-terracotta'), 'kallaway': ('glow', 'charcoal-orange')}  # 원본 스타일 → 코드 접두·기본 템플릿
PLAIN_DISPLAY = {'kallaway'}  # 글로우 스타일은 제목에 본문 서체 — 굵은 장식 서체(검은고딕 등)에 text-shadow 번짐이 겹치면 한글이 뭉개진다(2026-11-22 표본 렌더)
HAND = 'pastel-pink-mint'  # 손글씨 토큰(--font-hand, 원본 Caveat) 은 이 템플릿의 한글 손글씨 서체(Gaegu)
SKIP = {'kallaway.t2.lower-third.brandbar': 'AIS 워드마크가 칸 밖에 박힌 브랜드 띠', 'kallaway.t2.lower-third.coordbar': '칸 밖에 「AIS Institute」 문구'}
AIS = re.compile(r'#37BDF8\b|\b55\s*,\s*189\s*,\s*248\b', re.I)  # AIS 파랑 → 템플릿 강조색
AIS_DEEP = re.compile(r'#07121C\b|\b7\s*,\s*18\s*,\s*28\b', re.I)  # AIS 짙은 남색(assets/brand-tokens.css) → 템플릿 배경을 어둡게 한 색
SKIP_ATTR = {'data-slot', 'data-composition-id', 'data-start', 'data-width', 'data-height', 'data-duration', 'data-track-index', 'data-composition-src'}


def git(*a, cwd=None):
    return subprocess.run(['git', *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def sync():
    """고정 커밋만 — 못 받거나 HEAD 가 다르면 멈춘다(검토하지 않은 원본이 들어오지 않게)."""
    if not (CACHE / '.git').exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        git('clone', '-q', '--filter=blob:none', '--no-checkout', '--depth', '1', REPO + '.git', str(CACHE))
        git('sparse-checkout', 'set', 'style-library', 'licenses', cwd=CACHE)
    if git('rev-parse', 'HEAD', cwd=CACHE) != COMMIT or not LIB.exists():
        try:
            git('fetch', '-q', '--depth', '1', '--filter=blob:none', 'origin', COMMIT, cwd=CACHE)
        except subprocess.CalledProcessError:
            sys.exit(f'herk-edit-kit 고정 커밋 {COMMIT[:7]} 을 받지 못해 멈춤 — 원본이 바뀌었으면 카드를 다시 검토하고 COMMIT 을 고친다')
        git('checkout', '-q', '--force', COMMIT, cwd=CACHE)
    head = git('rev-parse', 'HEAD', cwd=CACHE)
    if head != COMMIT: sys.exit(f'herk-edit-kit 캐시 HEAD {head[:7]} 가 고정 커밋 {COMMIT[:7]} 과 달라 멈춤')
    return head


def registry():
    return json.loads((LIB / 'registry.json').read_text(encoding='utf-8'))


def code_of(card):
    """원본 id(예: kallaway.t1.section.circle) → hk-glow-t1-section-circle. 실제 크리에이터 이름은 코드·제목에 쓰지 않는다."""
    style, tier, *rest = card['id'].split('.')
    return '-'.join(['hk', STYLE[style][0], tier, *rest]).lower().replace('_', '-')


def cards():
    return [c for s in registry()['styles'] for c in s['cards'] if c['id'] not in SKIP]


def _font_face(f, fam):
    ext = Path(f['file']).suffix.lower()
    fmt = {'.otf': 'opentype', '.ttf': 'truetype', '.woff2': 'woff2', '.woff': 'woff'}.get(ext, 'truetype')
    return f"@font-face{{font-family:'{fam}';src:url('fonts/{Path(f['file']).name}') format('{fmt}');font-display:block}}"


def theme_of(template):
    import fonts
    t = fonts.resolve_theme(template)
    hx = t['tokens']['accent'].lstrip('#')
    return t, '#' + hx.upper(), ', '.join(str(int(hx[i:i + 2], 16)) for i in (0, 2, 4))


def deep_of(template):
    """템플릿 배경을 60% 어둡게 — AIS 짙은 남색 자리에 쓴다."""
    import fonts
    hx = fonts.resolve_theme(template)['tokens']['bg'].lstrip('#')
    rgb = [int(int(hx[i:i + 2], 16) * 0.4) for i in (0, 2, 4)]
    return '#' + ''.join(f'{v:02X}' for v in rgb), ', '.join(map(str, rgb))


def debrand(src, template):
    _, hexv, rgb = theme_of(template); dh, dr = deep_of(template)
    src = AIS.sub(lambda m: hexv if m.group(0).startswith('#') else rgb, src)
    return AIS_DEEP.sub(lambda m: dh if m.group(0).startswith('#') else dr, src)


def knobs(card):
    """카드 스크립트가 읽는 data 속성(숫자 목표값 등) — [(칸 이름, 속성, 몇 번째 또는 None, 원본 값)]. 같은 속성이 여러 요소에 있으면 하나씩 칸으로."""
    from bs4 import BeautifulSoup
    h = (LIB / card['file']).read_text(encoding='utf-8'); s = BeautifulSoup(h, 'html.parser')
    js = ' '.join(x.get_text() for x in s.find_all('script'))
    out = []
    for a in sorted({a for el in s.find_all(True) for a in el.attrs if a.startswith('data-') and a not in SKIP_ATTR}):
        if a not in js and a[5:] not in js: continue
        els = s.find_all(attrs={a: True}); base = 'n_' + re.sub(r'\W', '_', a[5:])
        for i, el in enumerate(els):
            out.append((base if len(els) == 1 else f'{base}_{i + 1}', a, None if len(els) == 1 else i, el.get(a)))
    return out


def font_files(style, template):
    import fonts
    t = fonts.resolve_theme(template)
    return {t['title_font']['file'], t['caption_font']['file'], fonts.resolve_theme(HAND)['title_font']['file']}


def tokens(style, template):
    """원본 스타일 tokens.css 에서 AIS 파랑·서체·@import 만 바꾼 CSS(나머지 크기·이징·질감 토큰은 키트 사용 허락 범위로 그대로)."""
    import fonts
    t, hexv, rgb = theme_of(template)
    hand = fonts.resolve_theme(HAND)['title_font']
    src = (LIB / registry_folder(style) / 'tokens.css').read_text(encoding='utf-8')
    src = re.sub(r'@import\s+url\([^)]*\)\s*;', '', src)
    src = debrand(src, template)
    title, cap = t['title_font']['family'], t['caption_font']['family']
    head = _font_face(t['title_font'], title) + ('' if cap == title else _font_face(t['caption_font'], cap)) + _font_face(hand, hand['family'])
    disp = cap if style in PLAIN_DISPLAY else title
    over = (f":root{{--font-display:'{disp}',sans-serif;--font-label:'{cap}',sans-serif;--font-body:'{cap}',sans-serif;"
            f"--font-hand:'{hand['family']}',cursive;--font-mono:'{cap}',ui-monospace,monospace}}"
            "[data-slot]{word-break:keep-all}")  # 한글이 단어 중간에서 줄이 바뀌지 않게
    return head + '\n' + src + '\n' + over, t


def registry_folder(style):
    return next(s['folder'] for s in registry()['styles'] if s['id'] == style)


SLOT_JS = """<script>/* meta-motion: 칸(data-slot) 글 바꾸기 — 카드 스크립트보다 먼저 돈다. *글* 은 강조(<em>), 줄바꿈은 \\n.
구조 있는 칸은 구조를 살린다: 단어 span(.word) · 줄 div(.line) · 같은 꼴 여러 개(.tag, 쉼표로 나눔) · 짧은 꼬리 장식(: . /5) · 감싼 요소 하나(mark 등) */
(function(){var V=%s;
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function fmt(s){return esc(s).replace(/\\*([^*]+)\\*/g,'<em>$1</em>').replace(/\\n/g,'<br>')}
function fill(el,v){v=String(v);if(v==='')return;  /* 비운 칸은 원본(그림 무늬 등)을 그대로 둔다 */
 if(el.tagName==='IMG'){el.src=v;return}
 if(/\\.(png|jpe?g|webp|gif|svg)$/i.test(v)&&!el.textContent.trim()){el.style.backgroundImage='url("'+v+'")';el.style.backgroundSize='cover';el.style.backgroundPosition='center';return}
var ks=[].slice.call(el.children).filter(function(k){return !/^(EM|BR)$/.test(k.tagName)});
 if(!ks.length){el.innerHTML=fmt(v);return}
 var c0=ks[0].className||'';
 var ids=ks.map(function(k){return k.id});
 function fit(xs){if(ids[0]&&xs.length>ids.length){xs=xs.slice(0,ids.length-1).concat([xs.slice(ids.length-1).join(' ')])}return xs}  /* 카드 타임라인이 id 목록으로 움직이면 원래 개수를 넘지 않게 — 남는 것은 마지막에 합친다 */
 function idOf(i){return ids[i]?' id="'+ids[i]+'"':''}
 function inner(k,h){var c=k&&k.children.length===1&&!/^(EM|BR)$/.test(k.children[0].tagName)?k.children[0]:null;  /* .line>.line-inner 처럼 안쪽 감싸개가 있으면 살린다 */
   return c?'<'+c.tagName.toLowerCase()+(c.className?' class="'+c.className+'"':'')+'>'+h+'</'+c.tagName.toLowerCase()+'>':h}
 if(/\\bword\\b/.test(c0)){el.innerHTML=fit(v.match(/\\*[^*]+\\*\\S*|\\S+/g)||[]).map(function(w,i){var a=/^\\*([^*]+)\\*(.*)$/.exec(w);  /* *두 배*로 → 강조 한 덩어리(조사가 떨어지지 않게) */
   return '<span class="word'+(a?' accent':'')+'"'+idOf(i)+'>'+inner(ks[i],esc(a?a[1]+a[2]:w))+'</span>'}).join(' ');return}
 if(/\\bline\\b/.test(c0)){el.innerHTML=fit(v.split('\\n')).map(function(l,i){var k=ks[Math.min(i,ks.length-1)];return '<'+k.tagName.toLowerCase()+' class="line line-'+(i+1)+'"'+idOf(i)+'>'+inner(k,fmt(l))+'</'+k.tagName.toLowerCase()+'>'}).join('');return}
 if(ks.length>1&&ks.every(function(k){return k.className===c0})){var tp=ks[0];el.innerHTML='';
   v.split(/\\s*[,·]\\s*/).forEach(function(p){var k=tp.cloneNode(false);k.innerHTML=fmt(p);el.appendChild(k)});return}
 if(ks.length===1&&ks[0].textContent.trim().length<=3){var tn=[].slice.call(el.childNodes).filter(function(n){return n.nodeType===3&&n.textContent.trim()})[0];
   if(tn)tn.textContent=v;else el.insertBefore(document.createTextNode(v),el.firstChild);return}
 ks[0].innerHTML=fmt(v);[].slice.call(el.childNodes).forEach(function(n){if(n.nodeType===3)n.textContent=''})}
Object.keys(V).forEach(function(k){if(k[0]!=='@')return;var m=/^@([\\w-]+)(?:#(\\d+))?$/.exec(k);if(!m)return;
 var els=document.querySelectorAll('['+m[1]+']');[].slice.call(els).forEach(function(el,i){if(m[2]==null||+m[2]===i)el.setAttribute(m[1],V[k])})});
document.querySelectorAll('[data-slot]').forEach(function(el){var v=V[el.getAttribute('data-slot')];if(v!=null)fill(el,v)});})();</script>
"""


def prepare(card, vals, template=None):
    """카드 한 장을 쓸 HTML 로 — tokens.css 링크를 바꾼 토큰 <style> 로, AIS 색 리터럴을 강조색으로, 칸 글은 카드 스크립트 앞에서 바꾼다."""
    template = template or STYLE[card['style']][1]
    css, t = tokens(card['style'], template)
    html = (LIB / card['file']).read_text(encoding='utf-8')
    html = re.sub(r'<link[^>]+tokens\.css[^>]*>', lambda m: '<style>' + css + '</style>', html, count=1)
    html = re.sub(r'<link[^>]+fonts\.googleapis\.com[^>]*>', '', html)
    html = debrand(html, template)
    km = {k: (a, i) for k, a, i, _ in knobs(card)}  # 손잡이 칸(n_…)은 data 속성으로
    vals = {(f'@{km[k][0]}' + ('' if km[k][1] is None else f'#{km[k][1]}') if k in km else k): v for k, v in vals.items()}
    js = SLOT_JS % json.dumps(vals, ensure_ascii=False).replace('</', '<\\/')
    i = html.find('window.__timelines')
    j = html.rfind('<script', 0, i) if i >= 0 else -1
    html = html[:j] + js + html[j:] if j >= 0 else html.replace('</body>', js + '</body>', 1)
    return html, t


def write(card, vals, out, template=None, name=None):
    """out 폴더에 compositions/<name>.html 과 fonts/ — host 에 data-composition-src 로 넣는다."""
    out = Path(out); (out / 'compositions').mkdir(parents=True, exist_ok=True); (out / 'fonts').mkdir(exist_ok=True)
    html, t = prepare(card, vals, template)
    import fonts
    for f in font_files(card['style'], template or STYLE[card['style']][1]):
        shutil.copy(Path(fonts.FONT_DIR) / f, out / 'fonts' / Path(f).name)  # 템플릿의 file 은 data/fonts 안 이름
    html = html.replace("url('fonts/", "url('../fonts/")  # compositions/ 안에서 본 경로
    p = out / 'compositions' / f"{name or code_of(card)}.html"
    p.write_text(html, encoding='utf-8')
    return p, re.search(r'data-composition-id="([^"]+)"', html).group(1)


def host(out, clips, w=1920, h=1080):
    """clips: [(파일 상대경로, comp id, 시작, 길이)] — 한 프로젝트에 차례로 이어 붙인 host index.html."""
    total = max(s + d for _, _, s, d in clips)
    divs = ''.join(f'<div id="{cid}" class="clip" data-composition-id="{cid}" data-composition-src="{rel}" data-start="{s}" data-duration="{d}" '
                   f'data-track-index="0" data-width="{w}" data-height="{h}"></div>' for rel, cid, s, d in clips)
    (Path(out) / 'index.html').write_text(
        f'<!doctype html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width={w}, height={h}">'
        f'<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'
        f'<style>html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:#000}}</style></head><body>'
        f'<div id="root" data-composition-id="root" data-width="{w}" data-height="{h}" data-start="0" data-duration="{total}">{divs}</div>'
        f'<script>window.__timelines=window.__timelines||{{}};window.__timelines["root"]=gsap.timeline({{paused:true}});</script></body></html>',
        encoding='utf-8')


PROBE_JS = """(arg) => { const [cid, at, want] = arg; const tl = (window.__timelines || {})[cid];
  if (!tl) return { err: 'no timeline' };
  const dur = tl.duration(); tl.seek(Math.min(at < 0 ? dur : at, dur), false);
  const slots = {}; document.querySelectorAll('[data-slot]').forEach((el) => { const r = el.getBoundingClientRect();
    slots[el.getAttribute('data-slot')] = { text: el.textContent.replace(/\\s+/g, ' ').trim(), over: el.scrollWidth > el.clientWidth + 4 && getComputedStyle(el).overflow !== 'visible',
      out: r.width > 0 && (r.left < -4 || r.right > innerWidth + 4 || r.top < -4 || r.bottom > innerHeight + 4) }; });
  return { dur, slots }; }"""


def probe(items, workers=4):
    """카드마다 브라우저에서 열어 타임라인 길이·콘솔 오류·칸 글(끝 시각)을 잰다. items: [(코드, 값 dict)] → {코드: 결과}.
    값을 준 칸이 끝 프레임에 그 글을 담고 있는지(스크립트가 덮어쓰지 않는지), 칸이 화면 밖으로 나가는지 본다."""
    import tempfile
    from playwright.sync_api import sync_playwright
    by = {code_of(c): c for c in cards()}
    d = Path(tempfile.mkdtemp(prefix='herk-probe-'))
    out = {}
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel='chrome', headless=True)
        pg = br.new_page(viewport={'width': 1920, 'height': 1080})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        for code, vals in items:
            errs.clear()
            p, cid = write(by[code], vals, d, name=code)
            try:
                pg.goto(p.as_uri(), wait_until='load', timeout=30000); pg.wait_for_timeout(300)
                r = pg.evaluate(PROBE_JS, [cid, -1, None])
            except Exception as e:
                r = {'err': str(e)[:200]}
            r['errors'] = sorted(set(errs))[:5]; out[code] = r
        br.close()
    shutil.rmtree(d, ignore_errors=True)
    return out


KIT = {'source': REPO, 'license': 'MIT + Herk Edit Kit Use Permission (licenses/PERMISSION-herk-edit-kit.txt)', 'creator': 'Nate Herk', 'commit': COMMIT, 'cache': True,
       'fetched': '2026-11-22', 'found_via': '쇼츠 «10 GitHub Repos That Level Up HyperFrames Videos»',
       'how': 'python3 build_herk.py card {code} --out <프로젝트> [--template <템플릿 id>] [칸=값 …] → <프로젝트>/compositions/{code}.html 과 fonts/ '
              '(안 준 칸은 카드 예시값, 색·서체는 템플릿 — 원본의 AIS 브랜드 색은 템플릿 색으로 바꿔 넣는다). host 에 data-composition-src 로 넣고 길이는 카드 장면 순서대로'}
OUT_FILES = {'vox-explainer': 'anim_herk_paper.json', 'kallaway': 'anim_herk_glow.json'}
OVERLAY = {'lower-third', 'label'}


def items_all():
    out = {}
    for f in OUT_FILES.values():
        p = HERE / 'data' / f
        if p.exists(): out.update(json.loads(p.read_text(encoding='utf-8'))['items'])
    return out


def vals_of(item, over=None):
    """카드 예시값을 기본으로 사용자 값을 덮는다 — 칸 이름(k)을 data-slot 이름으로(손잡이 n_… 는 그대로). 안 준 칸에 원본 영어가 남지 않게."""
    over = over or {}
    out = {}
    for f in item['fields']:
        v = over.get(f['k'], f.get('ex', ''))
        out[f['k'] if f['k'].startswith('n_') else f.get('slot', f['k'])] = v
    return out


def fixed_text(card):
    """칸 밖에 박힌 영어 글(사본에서 직접 바꿔야 하는 것)."""
    from bs4 import BeautifulSoup, Comment
    s = BeautifulSoup((LIB / card['file']).read_text(encoding='utf-8'), 'html.parser')
    for x in s(['script', 'style', 'template']): x.decompose()
    for x in s.find_all(string=lambda v: isinstance(v, Comment)): x.extract()
    for el in s.select('[data-slot]'):
        if el['data-slot'].strip(): el.decompose()  # 빈 data-slot 은 고정 글자로 남겨 센다
    return [v.strip() for v in s.body.find_all(string=True) if re.search(r'[A-Za-z]{2,}', v)] if s.body else []


def verify(gen):
    """생성 카드를 예시값으로 열어 끝 프레임을 본다 — 칸 글이 그대로 있는지(스크립트가 덮어쓰지 않는지), 원본보다 화면 밖·넘침이 늘었는지, 스크립트 오류. {코드: [문제]}"""
    base = probe([(k, {}) for k in gen])
    got = probe([(k, vals_of(v)) for k, v in gen.items()])
    bad = {}
    for k, v in gen.items():
        r, r0, b = got.get(k, {}), base.get(k, {}), []
        if r.get('err') or r.get('errors'): b.append(f"오류 {r.get('err') or ''} {r.get('errors')}")
        slots = r.get('slots', {})
        for f in v['fields']:
            if f['k'].startswith('n_') or not str(f.get('ex', '')).strip(): continue
            s = slots.get(f.get('slot', f['k']))
            want = re.sub(r'\s+', ' ', str(f['ex']).replace('*', '').replace('\n', ' ')).strip()
            if s is None: b.append(f"칸 없음 {f['k']}"); continue
            num = re.sub(r'\D', '', want)
            if re.sub(r'[\s,·]', '', want) not in re.sub(r'[\s,·]', '', s['text']) and not (num and num in re.sub(r'\D', '', s['text'])):
                b.append(f"칸 글이 바뀜 {f['k']}: «{want}» → «{s['text'][:40]}»")
            o = r0.get('slots', {}).get(f.get('slot', f['k']), {})
            if (s['out'] and not o.get('out')) or (s['over'] and not o.get('over')): b.append(f"화면 밖·넘침 {f['k']}")
        if b: bad[k] = b
    return bad


def tpl_of(g):
    """요청 문장은 다른 카드와 같은 꼴로 기계적으로 — «이름 만들어줘. 칸: 「값」. [[ 선택 칸: 「값」.]]» (생성 모델의 문장은 «만들어줘» 가 겹치고 선택 구절이 어색했다, 2026-11-23).
    *강조* 는 build_herk 가 <em> 으로 바꾸는 표시라 문장에서는 «*…* 는 강조» 를 한 번 알린다. n_ 손잡이는 숫자라 「」 없이."""
    def one(f):
        lab = re.sub(r'\s*\((?:선택|필수)\)\s*$', '', f['label']).strip()
        return f"{lab}: {{{f['k']}}}." if f['k'].startswith('n_') else f"{lab}: 「{{{f['k']}}}」."
    req = [one(f) for f in g['fields'] if not f.get('opt')]
    opt = [f"[[ {one(f)}]]" for f in g['fields'] if f.get('opt')]
    em = ' 「」 안의 *별표* 로 감싼 말은 강조색으로.' if any('*' in str(f.get('ex', '')) for f in g['fields']) else ''
    return f"{g['name']} 만들어줘. " + ' '.join(req) + ''.join(opt) + em


def export(gen, drop=()):
    """검증한 카드를 data/anim_herk_<스타일>.json 두 파일로(꼴은 anim_skills.json 과 같다 — kits + items)."""
    by = {code_of(c): c for c in cards()}
    outs = {f: {'kits': {'herk-edit-kit': KIT}, 'items': {}} for f in OUT_FILES.values()}
    for code, g in sorted(gen.items()):
        if code in drop or not g.get('tpl'): continue
        c = by[code]; ft = fixed_text(c)
        notes = [f"원본 스타일의 색·서체 자리에 템플릿을 넣는다(기본 {STYLE[c['style']][1]} — --template 로 바꾼다). 원본 AIS 브랜드 파랑·남색은 템플릿 강조색·배경으로 바꿔 넣는다(LICENSE 「Note on brand assets」)",
                 '1920x1080 고정 · 원본은 스스로 「렌더 QA 를 다 거치지 않은 초안」이라고 밝힌 키트다 — 쓰기 전에 snapshot 으로 한 번 본다']
        if ft: notes.append('칸 밖에 박힌 영어 글이 있다(사본에서 직접 바꾼다): ' + ' · '.join(dict.fromkeys(ft))[:160])
        kn = [f['k'] for f in g['fields'] if f['k'].startswith('n_')]
        if kn: notes.append(f"n_ 칸({', '.join(kn)})은 화면 글이 아니라 스크립트가 읽는 숫자(채움 비율·목표값 등) — 숫자만 넣는다")
        if c['purpose'] in OVERLAY: notes.append('배경이 비어 있는 얹는 카드 — 영상 위 트랙에 둔다')
        tier, *rest = c['id'].split('.')[1:]
        outs[OUT_FILES[c['style']]]['items'][code] = {
            'kit': 'herk-edit-kit', 'path': 'style-library/' + c['file'], 'size': [1920, 1080], 'thumb': 'render', 'en': ' '.join([tier, *rest]),
            'template': STYLE[c['style']][1], 'cat': g['cat'], 'name': g['name'], 'plain': g['plain'], 'when': g['when'], 'len': g['len'], 'inds': [],
            'fields': g['fields'], 'tpl': tpl_of(g), 'dx': g['dx'], 'notes': notes}
    for f, d in outs.items():
        (HERE / 'data' / f).write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    return {f: len(d['items']) for f, d in outs.items()}


def thumbs(codes=None, per=10, out=None, items=None):
    """목록 그림 data/as_thumb/<코드>.jpg — 같은 스타일 카드 per 장을 한 프로젝트에 이어 붙여 snapshot 한 번(끝나기 0.4초 전), 480 폭으로 줄인다.
    snapshot 은 Gemini 키가 환경에 있으면 프레임을 Gemini 로 보내므로 그 변수를 빼고 부른다."""
    import os, tempfile
    by = {code_of(c): c for c in cards()}
    items = items or items_all()
    todo = [k for k in (codes or items) if k in items]
    out = Path(out or HERE / 'data' / 'as_thumb'); out.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('GEMINI_')}
    for style in OUT_FILES:  # 스타일을 섞지 않는다(:root 토큰이 서로 덮지 않게)
        ks = [k for k in todo if by[k]['style'] == style]
        for i in range(0, len(ks), per):
            grp = ks[i:i + per]; d = Path(tempfile.mkdtemp(prefix='herk-thumb-'))
            try:
                clips, t, ats = [], 0.0, []
                for k in grp:
                    p, cid = write(by[k], vals_of(items[k]), d, name=k); b = float(items[k]['dx']['base'])
                    clips.append((f'compositions/{p.name}', cid, t, b)); ats.append(round(t + max(0.1, b - 0.4), 2)); t += b
                host(d, clips)
                subprocess.run(['npx', '-y', 'hyperframes@0.8.162', 'snapshot', str(d), '--at', ','.join(map(str, ats)), '--no-end', '-o', str(d / 'snap')],
                               check=True, capture_output=True, env=env, timeout=900)
                pngs = sorted((d / 'snap').glob('frame-*.png'))
                for k, png in zip(grp, pngs):
                    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(png), '-vf', 'scale=480:-2', '-q:v', '4', str(out / f'{k}.jpg')], check=True)
                print(f'{style} {i + len(grp)}/{len(ks)}', flush=True)
            finally:
                shutil.rmtree(d, ignore_errors=True)


def main(a):
    cmd = a[0] if a else ''
    if cmd == 'sync': return print(sync())
    if cmd == 'thumbs': return thumbs(a[1:] or None)
    if cmd == 'list':
        for c in cards(): print(code_of(c), c['purpose'], c['tier'], ','.join(c['slots']), sep='\t')
        return
    if cmd == 'card' and len(a) > 1:
        by = {code_of(c): c for c in cards()}
        if a[1] not in by: sys.exit(f'없는 카드: {a[1]}')
        opt = {a[i][2:]: a[i + 1] for i in range(2, len(a) - 1) if a[i].startswith('--')}
        vals = dict(x.split('=', 1) for x in a[2:] if '=' in x and not x.startswith('--'))
        if 'out' not in opt: sys.exit('--out <폴더> 가 필요하다')
        it = items_all().get(a[1])
        if it: vals = vals_of(it, vals)  # 안 준 칸은 카드 예시값(원본 영어 자리표시자가 남지 않게)
        p, cid = write(by[a[1]], vals, opt['out'], opt.get('template'))
        return print(f'{p}\n host 에: <div id="{cid}" class="clip" data-composition-id="{cid}" data-composition-src="compositions/{p.name}" '
                     f'data-start="0" data-duration="<초>" data-track-index="0" data-width="1920" data-height="1080"></div>')
    sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])

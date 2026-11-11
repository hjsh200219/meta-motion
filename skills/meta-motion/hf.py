#!/usr/bin/env python3
"""HyperFrames 공식 레지스트리(블록·컴포넌트 444개, Apache-2.0) 찾기·넣기.
search 는 저장해 둔 목록(data/hf_registry.json, build_hf.py)만 읽고, add 는 `npx hyperframes add` 로 항목을 받은 뒤
연결 조각(host div)을 lint 를 통과하는 꼴로 만들어 주고, 프로젝트 비율·서체와 어긋나는 곳을 짚어 준다(자동으로 고치지는 않는다).
실행: python3 motion.py registry <단어…(영어·한국어)> [--type block|component] [--portrait]
      python3 motion.py registry-add <이름> --dir <HyperFrames 프로젝트> [--start 0] [--track 1]"""
import json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REG = json.loads((HERE / 'data' / 'hf_registry.json').read_text(encoding='utf-8'))
ITEMS = {it['name']: it for it in REG['items']}
_KO = HERE / 'data' / 'hf_registry_ko.json'  # 분류(Jev)·한국어 카드(build_hf_ko.py) — 있으면 한국어로도 찾고 이름·분류를 같이 보여 준다
KO = json.loads(_KO.read_text(encoding='utf-8')) if _KO.exists() else {}
# 남의 제품 화면·브랜드를 흉내 낸 항목 — 그 회사 영상이 아니면 쓰지 않는다(상표·오인 위험)
BRAND = {'instagram', 'tiktok', 'spotify', 'slack', 'heygen', 'chatgpt', 'claude', 'youtube', 'apple', 'google', 'figma', 'github', 'x', 'twitter', 'linkedin'}
SIZE = re.compile(r'data-width="(\d+)"[^>]*?data-height="(\d+)"')


def is_brand(it):
    # 이름에 브랜드가 든 항목·@계정을 쓴 항목만 — 태그 youtube·tiktok 은 「그 플랫폼용·그 스타일」이라 표시하지 않는다
    return bool(BRAND & set(it['name'].split('-'))) or bool(re.search(r'@\w', it['description']))


def license_of(name):
    """항목 라이선스 — 저장소는 Apache-2.0 이지만 항목마다 다를 수 있다(MIT AND OFL-1.1·OFL-1.1 등 39개). 항목 값이 우선."""
    return (ITEMS.get(name) or {}).get('license') or REG['license']


def brand_of(name):
    return bool(ITEMS.get(name)) and is_brand(ITEMS[name])


def dims(it):
    d = it.get('dimensions') or {}
    return f"{d['width']}x{d['height']}" if d else '크기 미표기'  # 컴포넌트는 목록에 크기가 없다 — 장면 컴포지션인지 조각인지는 add 가 파일을 보고 알려 준다


def search(args):
    kind = args[args.index('--type') + 1] if '--type' in args else ''
    portrait = '--portrait' in args
    qs = [a.lower() for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] != '--type')]
    hit = [it for it in REG['items'] if (not kind or it['type'] == kind)
           and (not portrait or (it.get('dimensions') or {}).get('height', 0) > (it.get('dimensions') or {}).get('width', 0))
           and all(q in ' '.join([it['name'], it['title'], it['description'], *it['tags'], *[str(KO.get(it['name'], {}).get(k, '')) for k in ('name', 'plain', 'cat')]]).lower() for q in qs)]
    for it in hit:
        dur = f"{it['duration']}초" if it.get('duration') else ''
        brand = '⚠브랜드 흉내\t' if is_brand(it) else ''
        ko = KO.get(it['name'], {})
        print(f"{brand}{it['name']}\t{ko.get('name', it['title'])}\t{ko.get('cat', '')}\t{it['type']}\t{dims(it)}\t{dur}\t{','.join(it['tags'][:6])}\t{it['description'][:90]}")
    if not hit: print('찾은 항목 없음 — 한국어 이름·분류나 영어 태그로 찾기: ' + ' '.join(sorted({t for it in REG['items'] for t in it['tags']})[:80]))
    print(f"\n({len(hit)}/{len(REG['items'])}개 · 목록 {REG['fetched']} · {REG['license']} · 넣기: python3 motion.py registry-add <이름> --dir <프로젝트>)", file=sys.stderr)


def project_size(proj):
    m = SIZE.search((proj / 'index.html').read_text(encoding='utf-8')) if (proj / 'index.html').exists() else None
    return (int(m.group(1)), int(m.group(2))) if m else None


def host(snippet, comp_id, rel, size, dur, start, track):
    """CLI 조각에 id·class·data-start·data-track-index 를 채운다 — 없으면 lint 가 host_missing_composition_id·studio_missing_editable_id 로 막는다."""
    attrs = {'id': comp_id, 'class': 'clip', 'data-composition-id': comp_id, 'data-composition-src': rel,
             'data-start': str(start), 'data-duration': dur, 'data-track-index': str(track)}
    if size: attrs.update({'data-width': size[0], 'data-height': size[1]})
    for k, v in re.findall(r'([\w-]+)="([^"]*)"', snippet if snippet.lstrip().startswith('<div') else ''):
        if k not in ('id', 'class', 'data-start', 'data-track-index'): attrs[k] = v
    return '<div ' + ' '.join(f'{k}="{v}"' for k, v in attrs.items()) + '></div>'


def checks(text, size, proj_size):
    out = []
    if size and proj_size and tuple(map(int, size)) != proj_size:
        w, h = proj_size
        big = sorted({int(n) for n in re.findall(r'\b(\d{4})(?:px)?\b', text) if 1000 <= int(n) <= 4000})
        out.append(f"비율 다름: 항목 {size[0]}x{size[1]} → 프로젝트 {w}x{h}. 고칠 곳 — viewport meta · html/body 크기 · 루트 data-width/height · "
                   f"폭을 정한 CSS·스크립트 상수(이 파일의 1000 넘는 수: {', '.join(map(str, big)) or '없음'}) · 아래 여백(세로는 화면 아래 20% 위로). 고친 뒤 위 host 의 data-width/height 도 {w}/{h} 로.")
    fams = sorted({f.replace('+', ' ') for f in re.findall(r'fonts\.googleapis\.com/css2\?family=([A-Za-z+]+)', text)})
    if fams: out.append(f"영문 서체({', '.join(fams)}) — 한글은 기본 글꼴로 떨어진다. fonts.py pick 결과 서체로 @font-face·font-family·캔버스 측정용 FONT_FAMILY 를 함께 바꾼다.")
    if re.search(r'#a6a6a6|#A6A6A6', text): out.append('흐린 글자색 #A6A6A6 은 밝은 띠 위 대비 1.94:1 로 check 경고 — #838383 이하로.')
    return out


def add(args):
    name = next((a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or not args[i - 1].startswith('--'))), '')
    opt = {args[i][2:]: args[i + 1] for i in range(len(args) - 1) if args[i].startswith('--')}
    if not name: sys.exit('사용법: registry-add <이름> --dir <프로젝트> [--start 0] [--track 1]')
    if name in REG['excluded']: sys.exit(f"{name} 은 쓰지 않는다 — {REG['excluded'][name]}")
    if name not in ITEMS: print(f'주의: {name} 은 저장된 목록({REG["fetched"]})에 없다 — 새 항목이면 build_hf.py 로 목록을 갱신', file=sys.stderr)
    proj = Path(opt.get('dir', '.')).resolve()
    r = subprocess.run(['npx', '--yes', REG['cli'], 'add', name, '--dir', str(proj), '--json', '--no-clipboard'], capture_output=True, text=True)
    out = r.stdout[r.stdout.find('{'):] if '{' in r.stdout else ''
    res = json.loads(out) if out else {}
    if r.returncode or not res.get('ok'): sys.exit(f'add 실패: {(r.stderr or r.stdout).strip()[-400:]}')
    proj_size = project_size(proj)
    written = list(map(Path, res['written']))
    assets = [f for f in written if f.suffix.lower() != '.html']
    for f in [f for f in written if f.suffix.lower() == '.html']:
        text, rel = f.read_text(encoding='utf-8'), f.relative_to(proj).as_posix()
        cid = re.search(r'data-composition-id="([^"]+)"', text)
        size = SIZE.search(text)
        size = size.groups() if size else None
        print(f'# {rel}')
        if cid:
            dur = (re.search(r'data-duration="([^"]+)"', text) or [None, '5'])[1]
            print('장면 컴포지션 — 루트 컴포지션에 아래 host 를 넣는다(data-start·data-track-index 는 장면에 맞게):')
            print('  ' + host(res.get('snippet', ''), cid.group(1), rel, size, dur, opt.get('start', 0), opt.get('track', 1)))
        else:
            print('붙여 넣는 조각 — 마크업·CSS 를 장면 하위 컴포지션 안에 옮기고, 움직임은 그 장면의 일시정지된 GSAP 타임라인(window.__timelines)에 건다.')
        for c in checks(text, size, proj_size): print('- ' + c)
    pics = [f for f in assets if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.gif')]
    if pics:  # 캐러셀 25종 등은 실제 가수·앨범 사진을 견본으로 받아 온다(2026-10-17 실측) — 그대로 내보내지 않는다
        print(f"- 견본 그림 {len(pics)}개({pics[0].relative_to(proj).parent.as_posix()}/…) — 원본 저장소의 예시(실제 인물·앨범 사진 포함)다. 영상에는 우리 사진으로 바꿔 넣는다.")
    print(f"출처: {REG['source']}/{name} ({license_of(name)}) · 넣은 뒤 npx --yes {REG['cli']} check")
    if brand_of(name): print('⚠브랜드 흉내 — 남의 제품 화면·로고·실제 @계정을 흉내 낸 항목이다. 그 회사·그 사람 영상이 아니면 쓰지 않는다')


def main(args):
    (add if args[:1] == ['add'] else search)(args[1:] if args[:1] in (['add'], ['search']) else args)


if __name__ == '__main__':
    main(sys.argv[1:])

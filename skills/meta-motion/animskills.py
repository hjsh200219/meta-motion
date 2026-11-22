#!/usr/bin/env python3
"""애니메이션 스킬 — GitHub 모션 키트 여러 곳의 모션을 한국어 카드로 한 카탈로그에 싣는다(data/anim_skills.json · kits + items).
- claude-animation-skills(MIT © 2026 Artem Novitckii) 6개(2026-11-13): 빠른 4개는 JSON 사양 → 원본 template.html → 1080x1920 영상 한 개,
  엔진 2개(막대 인간·3D 만화)는 음성이 붙는 릴스 한 편짜리 작업.
- 쇼츠 «10 GitHub Repos That Level Up HyperFrames Videos» 의 키트들(2026-11-22): reelforge 조각 · hyperframes-motion-library 템플릿 ·
  tegaki 손글씨 · animated-diagrams-skill 다이어그램 · saas-motion-kit 전환 · huashu-design 카메라 리그 · product-launch-motion.
카드는 손으로 쓴 한국어 사양이고, 원본 파일은 싣지 않고 쓸 때 고정 커밋 캐시 클론(~/.cache/meta-motion/<키트>)에서 읽는다 — 검토한 판만 쓰도록 커밋을 고정한다.
항목: kit(출처 이름) · path(원본 repo 안 경로) · size([가로, 세로] 고정 또는 null 가변) · thumb(목록 그림 원천, null 이면 그림 없음) · notes(실측 주의).
실행: python3 animskills.py sync [<키트>]   고정 커밋 캐시를 맞춘다(키트 생략 = 캐시를 쓰는 키트 전부)
      python3 animskills.py thumbs [<코드>…]  목록 그림 data/as_thumb/<코드>.jpg 를 원본 그림·영상에서 다시 만든다(ffmpeg)"""
import functools, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data' / 'anim_skills.json'
CACHE_ROOT = Path.home() / '.cache' / 'meta-motion'
ORDER = ['as-3d-cartoon', 'as-stick-figure', 'as-line-art', 'as-map-route', 'as-breakdown', 'as-graph']  # docs/skills.jpg 왼쪽부터
TAIL = '\n⛔ 원본 예시의 문구·장면을 그대로 쓰지 않는다 · 코드를 거의 그대로 옮기면 원본 라이선스 고지를 함께 둔다'


HERK = [HERE / 'data' / f for f in ('anim_herk_paper.json', 'anim_herk_glow.json')]  # herk-edit-kit 스타일 카드(build_herk.py) — 스타일별 두 파일(KB 리뷰 파일당 48만 자 상한). 꼴은 같다(kits + items)


@functools.lru_cache(maxsize=1)
def load():
    idx = json.loads(DATA.read_text(encoding='utf-8'))
    for f in HERK:
        if f.exists():
            h = json.loads(f.read_text(encoding='utf-8'))
            idx['kits'].update(h['kits']); idx['items'].update(h['items'])
    return idx


def kit_of(code):
    idx = load(); return idx['kits'][idx['items'][code]['kit']]


def cache(kit):
    return CACHE_ROOT / kit


def url(code):
    """원본 주소(고정 커밋) — 폴더는 tree, 파일은 blob, 줄 앵커(#L12)는 남긴다(preview.html asUrl 과 같은 규칙)."""
    import re
    c, k = load()['items'][code], kit_of(code)
    path, _, a = c['path'].partition('#')
    tree = c['kit'] == 'claude-animation-skills' or not re.search(r'\.[A-Za-z0-9]+$', path)  # 폴더(tegaki 서체 폴더 등)는 tree
    return f"{k['source']}/{'tree' if tree else 'blob'}/{k['commit'][:7]}/{path}{'#' + a if re.fullmatch(r'L\d+', a) else ''}"


def sync(kit=None):
    """고정 커밋 캐시 — 못 받거나 HEAD 가 다르면 멈춘다(build_cokac.sync_repo 와 같은 규칙)."""
    import build_cokac
    kits = load()['kits']
    names = [kit] if kit else [n for n, k in kits.items() if k.get('cache')]
    return {n: build_cokac.sync_repo(kits[n]['commit'], cache=cache(n), repo=kits[n]['source'] + '.git') for n in names}


def size_text(c):
    return f"{c['size'][0]}x{c['size'][1]} 고정" if c.get('size') else '크기 가변'


def credit(code):
    idx = load(); c = idx['items'][code]; k = idx['kits'][c['kit']]
    notes = ''.join(f"\n주의: {n}" for n in c.get('notes', []))
    if c['kit'] == 'claude-animation-skills':
        d = cache(c['kit']) / 'skills' / c['skill']
        head = f"\n[원본 스킬] {c['skill']} — {url(code)} ({k['license']}, 커밋 {k['commit'][:7]}) · 렌더 {c['render']} · 1080x1920"
        if c['engine']:
            how = (f"\n[만드는 법] 원본 절차 {d}/SKILL.md 를 따른다 — 엔진 {d}/engine 을 새 폴더로 복사해 대본·음성·장면 코드를 새로 쓴다"
                   f"\n  처음 한 번: bash {cache(c['kit'])}/kit/setup.sh --voice (Node 패키지·Chromium·음성 모델 약 1GB) · 캐시가 없으면 python3 animskills.py sync")
        else:
            how = (f"\n[만드는 법] 사양 JSON(<이름>.json)을 쓰고 python3 {d}/build.py <이름>.json → <이름>.mp4 + 안전 영역 표시 미리보기 시트 <이름>.sheet.jpg"
                   f"\n  처음 한 번: bash {cache(c['kit'])}/kit/setup.sh (three.js·Playwright·GSAP·HyperFrames) · 캐시가 없으면 python3 animskills.py sync"
                   f"\n  사양 예: {json.dumps(c['spec'], ensure_ascii=False)}")
        return head + how + notes + TAIL
    root = cache(c['kit'])
    where = f"{root}/{c['path']}" if k.get('cache') else url(code)
    how = k['how'].format(file=where, cache=root, url=url(code), code=code)
    if k.get('cache'): how += f" · 캐시가 없으면 python3 animskills.py sync {c['kit']}"
    head = f"\n[원본] {c['kit']} {c['en']} — {url(code)} ({k['license']}, 커밋 {k['commit'][:7]}) · {size_text(c)}"
    return head + f"\n[만드는 법] {how}" + notes + TAIL


def _thumb(src, out, size):
    """원천 하나에서 목록 그림 한 장 — 영상·GIF 는 60% 시각 프레임, 그림은 그대로. 가로는 480 폭, 세로·정사각은 360 폭."""
    src = Path(src)
    w = 480 if size and size[0] > size[1] else 360
    pre = []
    if src.suffix.lower() in ('.mp4', '.webm', '.mov', '.gif'):
        dur = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(src)], capture_output=True, text=True).stdout.strip()
        pre = ['-ss', f"{float(dur or 1) * 0.6:.2f}"]
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *pre, '-i', str(src), '-frames:v', '1', '-vf', f'scale={w}:-2', '-q:v', '4', str(out)], check=True)


def render_thumb(code, out):
    """reelforge 조각은 미리보기가 없어 직접 찍는다 — 조각을 임시 host 에 sub-composition 으로 넣고 칸(data-slot)을 카드 예시값(한국어)으로 바꿔
    hyperframes snapshot 한 장(움직임이 다 끝나기 직전 base-0.35초). GEMINI_API_KEY 를 빼고 부른다(snapshot 이 키가 있으면 프레임을 Gemini 로 보낸다)."""
    import os, re, shutil, tempfile
    c = load()['items'][code]; w, h = c['size']; dur = c['dx']['base']
    src = (cache(c['kit']) / c['path']).read_text(encoding='utf-8')
    for f in c['fields']:
        src = re.sub(r'(data-slot="%s"[^>]*>)([^<]*)' % re.escape(f['k'].replace('_', '-')), lambda m: m.group(1) + f['ex'], src, count=1)
    cid = re.search(r'data-composition-id="([^"]+)"', src).group(1)
    d = Path(tempfile.mkdtemp(prefix='as-thumb-'))
    try:
        (d / 'compositions').mkdir(); (d / 'compositions' / 'frag.html').write_text(src, encoding='utf-8')
        (d / 'index.html').write_text(
            f'<!doctype html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width={w}, height={h}">'
            f'<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'
            f'<style>html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:#000}}</style></head><body>'
            f'<div id="root" data-composition-id="root" data-width="{w}" data-height="{h}" data-start="0" data-duration="{dur}">'
            f'<div id="{cid}" class="clip" data-composition-id="{cid}" data-composition-src="compositions/frag.html" data-start="0" '
            f'data-duration="{dur}" data-track-index="0" data-width="{w}" data-height="{h}"></div></div>'
            f'<script>window.__timelines=window.__timelines||{{}};window.__timelines["root"]=gsap.timeline({{paused:true}});</script></body></html>', encoding='utf-8')
        env = {k: v for k, v in os.environ.items() if k != 'GEMINI_API_KEY'}
        subprocess.run(['npx', '-y', 'hyperframes@0.8.162', 'snapshot', str(d), '--at', f'{max(0.1, dur - 0.35):.2f}', '--no-end', '-o', str(d / 'snap')],
                       check=True, capture_output=True, env=env, timeout=300)
        png = next((d / 'snap').glob('*.png'))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(png), '-vf', 'scale=480:-2', '-q:v', '4', str(out)], check=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def thumbs(codes=()):
    """목록 그림. 원래 6개는 docs/skills.jpg(2272x728, 6칸 · 칸 360x640, x=16+376i, y=16)를 칸마다 자르고,
    나머지는 thumb 원천(원본 repo 의 미리보기 영상·그림 — 그 repo 라이선스가 덮는 것만)에서 한 장씩. thumb 이 「render」면 렌더한 그림(reelforge)을 쓴다."""
    idx = load(); out = HERE / 'data' / 'as_thumb'; out.mkdir(exist_ok=True)
    todo = [k for k in (codes or idx['items']) if idx['items'][k].get('thumb')]
    if any(idx['items'][k]['kit'] == 'claude-animation-skills' for k in todo):
        sync('claude-animation-skills')
        for i, code in enumerate(ORDER):
            if code in todo:
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(cache('claude-animation-skills') / 'docs' / 'skills.jpg'),
                                '-vf', f'crop=360:640:{16 + 376 * i}:16', '-q:v', '4', str(out / f'{code}.jpg')], check=True)
    for code in todo:
        c = idx['items'][code]
        if c['kit'] == 'claude-animation-skills': continue
        if c['thumb'] == 'render' and c['kit'] != 'reelforge': continue  # tegaki — 2026-11-22 한글 시험 렌더에서 뽑은 그림을 그대로 둔다
        root = cache(c['kit'])
        if not (root / '.git').exists(): sync(c['kit'])  # 캐시를 안 쓰는 키트(tegaki)도 그림 원천은 고정 커밋에서
        if c['thumb'] == 'render': render_thumb(code, out / f'{code}.jpg'); print(code, flush=True)
        else: _thumb(root / c['thumb'], out / f'{code}.jpg', c.get('size'))
    print(f'{len(todo)}장 → {out}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'thumbs': thumbs(sys.argv[2:])
    elif cmd == 'sync': print(sync(sys.argv[2] if len(sys.argv) > 2 else None))
    else: sys.exit(__doc__)

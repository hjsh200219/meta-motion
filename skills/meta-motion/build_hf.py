#!/usr/bin/env python3
"""HyperFrames 공식 레지스트리(블록·컴포넌트) 목록을 받아 data/hf_registry.json 을 다시 만든다.
목록(catalog --json)에 repo 의 registry-item.json(미리보기 주소·변수·싱크 지점)과 항목 HTML 에서 읽은 크기·길이를 더한다.
항목 HTML 은 repo 에 싣지 않는다 — 쓸 때 `hf.py add` 가 `npx hyperframes add` 로 받고, 카드·썸네일을 만들 때는 캐시 클론을 읽는다.
출처: https://github.com/heygen-com/hyperframes (registry/, Apache-2.0) · 카탈로그 https://hyperframes.heygen.com/catalog
실행: python3 build_hf.py  (npx·git·네트워크 필요 · 클론 캐시 ~/.cache/meta-motion/hyperframes)"""
import datetime, json, re, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HF = 'hyperframes@0.8.162'  # SKILL.md 렌더 고정 버전과 같게
REPO = 'https://github.com/heygen-com/hyperframes.git'
CACHE = Path.home() / '.cache' / 'meta-motion' / 'hyperframes'
OUT = Path(__file__).resolve().parent / 'data' / 'hf_registry.json'
FLOOR = 400                 # 2026-10-17 실측 447 — 이보다 적으면 CLI 출력이 바뀐 것으로 보고 중단
# repo CREDITS.md 가 「Origin to be confirmed with the author」로 적은 자산이 든 항목 — 출처가 확인될 때까지 쓰지 않는다
EXCLUDE = {
    'canopy-part-title': 'leaf-surface-color/normal.webp 출처 미확인(CREDITS.md)',
    'glass-shard-title': 'matcap-1.png 출처 미확인(CREDITS.md)',
    'frost-sequence-camera-orbit': 'shards-atlas.png 등 텍스처 출처 미확인(CREDITS.md)',
}
SIZE = re.compile(r'data-width="(\d+)"[^>]*?data-height="(\d+)"')


def git(*a, cwd=None):
    return subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def sync_repo():
    """registry/ 만 얕게 받아 둔 캐시 클론을 최신 main 으로 맞추고 커밋 SHA 를 돌려준다."""
    if not (CACHE / '.git').exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        git('clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse', REPO, str(CACHE))
        git('sparse-checkout', 'set', '--no-cone', '/registry/', '/CREDITS.md', '/LICENSE', cwd=CACHE)
    else:
        git('fetch', '-q', '--depth', '1', 'origin', 'main', cwd=CACHE)
        git('reset', '-q', '--hard', 'origin/main', cwd=CACHE)
    return git('rev-parse', 'HEAD', cwd=CACHE)


def item_dir(it):
    return CACHE / 'registry' / (it['type'] + 's') / it['name']


def main_html(it):
    """항목 본 파일 — 장면 컴포지션이면 그대로 렌더되고, 조각이면 demo.html 이 있을 때 그것으로 렌더한다."""
    d = item_dir(it)
    return d / f"{it['name']}.html"


def fetch():
    out = subprocess.run(['npx', '--yes', HF, 'catalog', '--json'], capture_output=True, text=True, check=True).stdout
    return json.loads(out[out.index('['):])


def enrich(it):
    d = item_dir(it)
    meta = json.loads((d / 'registry-item.json').read_text(encoding='utf-8'))
    html = main_html(it).read_text(encoding='utf-8') if main_html(it).exists() else ''
    size = SIZE.search(html)
    dur = re.search(r'data-composition-id="[^"]+"[^>]*?data-duration="([\d.]+)"', html) or re.search(r'data-duration="([\d.]+)"', html)
    out = {k: it.get(k) for k in ('name', 'type', 'title', 'description', 'tags')}
    out['composition'] = 'data-composition-id' in html   # False 면 장면에 붙여 넣는 조각
    out['demo'] = (d / 'demo.html').exists()
    if it.get('dimensions'): out['dimensions'] = it['dimensions']
    elif size: out['dimensions'] = {'width': int(size.group(1)), 'height': int(size.group(2))}
    out['duration'] = it.get('duration') or (float(dur.group(1)) if dur else None)
    pv = meta.get('preview') or {}
    out['preview'] = {k: pv[k] for k in ('poster', 'video') if str(pv.get(k, '')).startswith('https://')}
    out['variables'] = [{k: v.get(k) for k in ('id', 'type', 'label', 'default', 'options') if v.get(k) is not None} for v in meta.get('variables') or []]
    out['sync'] = [{'id': s.get('id'), 'offset': s.get('offset')} for s in meta.get('syncPoints') or [] if isinstance(s.get('offset'), (int, float))]
    if meta.get('license'): out['license'] = meta['license']
    return out


def alive(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'meta-motion-plugin/1', 'Range': 'bytes=0-1'}), timeout=20).status in (200, 206)
    except OSError:
        return False


def drop_dead_previews(items):
    """registry-item.json 에 적힌 미리보기 주소 중 열리지 않는 것을 뺀다 — 2026-10-17 실측 포스터 174 중 63·영상 144 중 3 이 403."""
    urls = sorted({u for it in items for u in it['preview'].values()})
    with ThreadPoolExecutor(16) as ex: ok = dict(zip(urls, ex.map(alive, urls)))
    for it in items: it['preview'] = {k: u for k, u in it['preview'].items() if ok[u]}
    return sum(not v for v in ok.values())


def main():
    items = fetch()
    if len(items) < FLOOR: sys.exit(f'항목 {len(items)}개 — {FLOOR}개 미만이라 중단(catalog --json 형식 확인)')
    sha = sync_repo()
    keep = [enrich(it) for it in sorted(items, key=lambda x: x['name']) if it['name'] not in EXCLUDE]
    dead = drop_dead_previews(keep)
    data = {'source': 'https://github.com/heygen-com/hyperframes/tree/main/registry', 'license': 'Apache-2.0',
            'cli': HF, 'commit': sha, 'fetched': datetime.date.today().isoformat(), 'excluded': EXCLUDE, 'items': keep}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(keep)}개 저장(받은 {len(items)} · 제외 {len(items) - len(keep)} · 안 열리는 미리보기 {dead} · repo {sha[:7]}) → {OUT}')


if __name__ == '__main__':
    main()

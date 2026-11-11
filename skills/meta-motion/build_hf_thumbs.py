#!/usr/bin/env python3
"""HyperFrames 레지스트리 항목마다 실제 렌더한 한 장면을 data/hf_thumb/<이름>.jpg(가로 480px)로 만든다 — preview.html 목록 그림.
공식 미리보기는 444개 중 절반 정도만 있어(2026-10-17 실측 포스터 174) 모두 같은 방법으로 직접 렌더한다.
항목 폴더를 임시 프로젝트로 복사해 demo.html(있으면 — 투명 배경 컴포넌트도 화면 맥락이 보인다) 또는 본 파일을 index.html 로 두고
`hyperframes snapshot` 으로 길이의 60% 시점을 찍는다. 단색이면 30%·90% 시점을 다시 찍는다. 투명 배경은 회색 바탕에 합성.
80 아래로 흐리면 다른 시점을 더 찍고, 그래도 흐리면 공식 포스터가 더 또렷할 때 그것을 쓴다. 비면 실제로 쓸 때처럼 host 조각(data-composition-src)으로 감싼 루트에서 다시 찍고(<template> 안에 든 하위 컴포지션은 단독으로 안 그려진다),
끝까지 안 되면 공식 포스터를 받는다(런타임 오류 항목 — 예: vfx-shatter 의 drawElementImage).
실행: python3 build_hf_thumbs.py [--workers 4] [--only 이름,…] [--force]   · 필요: npx·ffmpeg·build_hf.py 캐시 클론"""
import json, re, shutil, subprocess, sys, tempfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from build_hf import CACHE, HF, item_dir

HERE = Path(__file__).resolve().parent
REG = json.loads((HERE / 'data' / 'hf_registry.json').read_text(encoding='utf-8'))
OUT = HERE / 'data' / 'hf_thumb'
BLANK = 16    # 밝기(Y) 최댓값−최솟값이 이보다 작으면 단색(빈 화면) — 크기로 재면 검은 바탕 하단 자막 같은 단순한 화면이 걸린다
GOOD = 80     # 이만큼 또렷하면 더 찍지 않는다 — 아래면 다른 시점·공식 포스터와 비교해 더 또렷한 것을 쓴다(전환 중간의 흐린 장면을 피함)


def source(it):
    d = item_dir(it)
    f = d / 'demo.html' if (d / 'demo.html').exists() else d / f"{it['name']}.html"
    return d, f


def duration(text, it):
    m = re.search(r'data-composition-id="[^"]+"[^>]*?data-duration="([\d.]+)"', text) or re.search(r'data-(?:composition-)?duration="([\d.]+)"', text)
    return float(m.group(1)) if m else (it.get('duration') or 3.0)


def shoot(proj, t, png_dir):
    shutil.rmtree(png_dir, ignore_errors=True)
    r = subprocess.run(['npx', '--yes', HF, 'snapshot', '--at', f'{t:.2f}', '--no-end', '--keep', '-o', str(png_dir)],
                       cwd=proj, capture_output=True, text=True, timeout=180)
    pngs = sorted(png_dir.glob('*.png'))
    return pngs[0] if r.returncode == 0 and pngs else None


def to_jpg(png, out):
    # 투명 부분은 회색 바탕(미리보기 화면의 체크무늬 색)에 합성하고 가로 480px 로 줄인다
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=0xD9DEE6:s=16x16', '-i', str(png),
                    '-filter_complex', '[0][1]scale2ref[b][f];[b][f]overlay=format=auto,scale=480:-2', '-frames:v', '1', '-q:v', '5', str(out)],
                   check=True, capture_output=True)
    return contrast(out)


def contrast(jpg):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(jpg), '-vf', 'signalstats,metadata=print:file=-', '-f', 'null', '-'],
                       capture_output=True, text=True)
    v = {k: int(x) for k, x in re.findall(r'lavfi\.signalstats\.(YMIN|YMAX)=(\d+)', r.stdout)}
    return v.get('YMAX', 0) - v.get('YMIN', 0)


HOST = """<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width={w}, height={h}">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:#D9DEE6}}</style></head><body>
<div id="root" data-composition-id="thumb-host" data-start="0" data-duration="{d}" data-width="{w}" data-height="{h}">
<div id="item" class="clip" data-composition-id="{cid}" data-composition-src="{src}" data-start="0" data-duration="{d}" data-track-index="0" data-width="{w}" data-height="{h}"></div>
</div>
<script>window.__timelines = window.__timelines || {{}}; window.__timelines["thumb-host"] = gsap.timeline({{ paused: true }});</script>
</body></html>
"""


def attempts(it, d, f, proj):
    """index.html 후보를 차례로 — ① demo.html 또는 본 파일 그대로 ② 본 파일을 하위 컴포지션으로 부르는 host 루트."""
    yield f.read_text(encoding='utf-8')
    main = d / f"{it['name']}.html"
    cid = re.search(r'data-composition-id="([^"]+)"', main.read_text(encoding='utf-8')) if main.exists() else None
    target = next((x['target'] for x in json.loads((d / 'registry-item.json').read_text(encoding='utf-8')).get('files', []) if x['path'] == main.name), None)
    if cid and target:
        dims = it.get('dimensions') or {'width': 1920, 'height': 1080}
        yield HOST.format(w=dims['width'], h=dims['height'], d=duration(main.read_text(encoding='utf-8'), it), cid=cid.group(1), src=target)


def official(it, out):
    """공식 포스터를 받아 같은 꼴 JPEG 로 — 또렷함(contrast)을 돌려준다, 없으면 0."""
    url = (it.get('preview') or {}).get('poster')
    if not url: return 0
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'meta-motion-plugin/1'}), timeout=30).read()
    except OSError as ex:  # 목록에 있어도 403 인 포스터가 있다(2026-10-17 실측) — 없는 것으로 친다
        print(f"{it['name']}: 공식 포스터 못 받음 {ex}", file=sys.stderr); return 0
    with tempfile.NamedTemporaryFile(suffix='.' + url.rsplit('.', 1)[-1].split('?')[0]) as t:
        t.write(data); t.flush()
        return to_jpg(Path(t.name), out)


def thumb(it):
    out = OUT / f"{it['name']}.jpg"
    d, f = source(it)
    if not f.exists(): return it['name'], 'no-html'
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / 'p'
        shutil.copytree(d, proj)
        # 자산은 registry-item.json 의 설치 위치(target, 예: assets/background.jpeg)에 둔다 — 항목 HTML 이 그 경로로 부른다
        for x in json.loads((d / 'registry-item.json').read_text(encoding='utf-8')).get('files', []):
            src, dst = (d / x['path']).resolve(), (proj / x['target']).resolve()
            # 외부 저장소가 적은 경로라 절대 경로·.. 로 항목 폴더·임시 프로젝트 밖을 가리키면 건너뛴다
            if src.is_file() and src.is_relative_to(d.resolve()) and dst.is_relative_to(proj.resolve()):
                dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
        best = (0, None)  # (또렷함, 시점)
        for html in attempts(it, d, f, proj):
            (proj / 'index.html').write_text(html, encoding='utf-8')
            dur = duration(html, it)
            for frac in (0.6, 0.3, 0.9):
                png = shoot(proj, dur * frac, Path(tmp) / 'snap')
                if not png: continue
                size = to_jpg(png, Path(tmp) / 'cand.jpg')
                if size > best[0]: shutil.copyfile(Path(tmp) / 'cand.jpg', Path(tmp) / 'best.jpg'); best = (size, frac)
                if size >= GOOD: break
            if best[0] >= GOOD: break
        if best[0] < GOOD and official(it, Path(tmp) / 'official.jpg') > best[0]:
            shutil.copyfile(Path(tmp) / 'official.jpg', out); return it['name'], 'ok-official'
        if best[0] >= BLANK:
            shutil.copyfile(Path(tmp) / 'best.jpg', out); return it['name'], 'ok'
        if best[1]: shutil.copyfile(Path(tmp) / 'best.jpg', out); return it['name'], 'blank'
        return it['name'], 'snapshot-failed'


def main():
    a = sys.argv[1:]
    workers = int(a[a.index('--workers') + 1]) if '--workers' in a else 4
    only = set(a[a.index('--only') + 1].split(',')) if '--only' in a else None
    if not (CACHE / 'registry').exists(): sys.exit('캐시 클론이 없다 — build_hf.py 를 먼저 실행')
    OUT.mkdir(exist_ok=True)
    todo = [it for it in REG['items'] if (not only or it['name'] in only) and ('--force' in a or not (OUT / f"{it['name']}.jpg").exists())]
    print(f'렌더 {len(todo)}개 / 전체 {len(REG["items"])}', file=sys.stderr)
    res = {}
    with ThreadPoolExecutor(workers) as ex:
        for i, (name, st) in enumerate(ex.map(thumb, todo), 1):
            res[name] = st
            if st != 'ok' or i % 25 == 0: print(f'[{i}/{len(todo)}] {name}: {st}', file=sys.stderr)
    for name in {p.stem for p in OUT.glob('*.jpg')} - {it['name'] for it in REG['items']}: (OUT / f'{name}.jpg').unlink()  # 목록에서 빠진 항목
    bad = {k: v for k, v in res.items() if not v.startswith('ok')}
    print(f'끝: ok {len(res) - len(bad)} · 문제 {len(bad)} {bad}', file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

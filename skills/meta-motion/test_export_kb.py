#!/usr/bin/env python3
"""export_kb.py 점검 — 내보낸 KB 페이지가 원본 영상 모드·뒤로 가기·자료 5개·레지스트리 그림을 갖췄는지. 실행: python3 test_export_kb.py"""
import tempfile
from pathlib import Path
from export_kb import DATA, KO, build

with tempfile.TemporaryDirectory() as d:
    build(Path(d))
    html = (Path(d) / 'index.html').read_text(encoding='utf-8')
    assert html.startswith('<!doctype html>') and html.count('<meta charset') == 1
    assert "window.MOTION_MEDIA = 'origin'" in html and '← PillDocKb</a>\n    <h1>' in html
    assert sorted(p.stem for p in (Path(d) / 'anim').glob('*.html')) == sorted(p.stem for p in (Path(__file__).resolve().parent / 'data/anim').glob('*.html')) and not (Path(d) / 'anim/index.json').exists() and len(list((Path(d) / 'anim/thumb').glob('*.jpg'))) == len(list((Path(__file__).resolve().parent / 'data/anim/thumb').glob('*.jpg')))
    assert all((Path(d) / f).stat().st_size > 1000 for f in DATA)
    assert all(k not in (Path(d) / f).read_text(encoding='utf-8') for f in KO for k in ('"src_sha"', '"cat_src"', '"hold_checked"', '"commit"'))
    assert len(list((Path(d) / 'hf_thumb').glob('*.jpg'))) == len(list((Path(__file__).resolve().parent / 'data/hf_thumb').glob('*.jpg'))) > 400
print('ok')

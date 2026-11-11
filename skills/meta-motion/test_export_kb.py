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
    assert all(len((Path(d) / f).read_text(encoding='utf-8')) < 480_000 for f in KO)   # KB PR AI 리뷰 diff 상한 50만 자 — 파일 하나가 한 PR 에 들어가야 한다
    assert len(list((Path(d) / 'hf_thumb').glob('*.jpg'))) == len(list((Path(__file__).resolve().parent / 'data/hf_thumb').glob('*.jpg'))) > 400

with tempfile.TemporaryDirectory() as d:   # 로컬 보기(serve.py · motion.py 인자 없음) — KB 로 가는 링크·KB 아이콘 없이, 원본 영상 모드는 같게
    build(Path(d), back=False)
    html = (Path(d) / 'index.html').read_text(encoding='utf-8')
    assert "window.MOTION_MEDIA = 'origin'" in html and '← PillDocKb' not in html and '/static/' not in html and html.count('<h1>') == 1
# 옵션처럼 생긴 인자(--help·-h)는 출력 폴더로 받지 않는다 — 2026-11-11 `export_kb.py --help` 가 「--help」 폴더를 만들었다
import os, subprocess, sys
with tempfile.TemporaryDirectory() as d:
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'export_kb.py'), '--help'], cwd=d, capture_output=True, text=True)
    assert r.returncode != 0 and not os.path.exists(os.path.join(d, '--help')), (r.returncode, os.listdir(d))
print('ok')

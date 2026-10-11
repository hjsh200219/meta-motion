#!/usr/bin/env python3
"""export_kb.py 점검 — 내보낸 KB 페이지가 원본 영상 모드·뒤로 가기·자료 3개를 갖췄는지. 실행: python3 test_export_kb.py"""
import tempfile
from pathlib import Path
from export_kb import build

with tempfile.TemporaryDirectory() as d:
    build(Path(d))
    html = (Path(d) / 'index.html').read_text(encoding='utf-8')
    assert html.startswith('<!doctype html>') and html.count('<meta charset') == 1
    assert "window.MOTION_MEDIA = 'origin'" in html and '← PillDocKb</a>\n    <h1>' in html
    assert all((Path(d) / f).stat().st_size > 1000 for f in ('motion.json', 'prompt_motion.json', 'prompt_motion_ko.json'))
print('ok')

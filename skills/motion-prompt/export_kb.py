#!/usr/bin/env python3
"""preview.html 을 사내 KB(kb.pilldoc.co.kr/motion/)용 페이지로 내보낸다 — preview.html 이 정본, 내보낸 파일은 고치지 않는다.
KB 에는 외부 영상을 막는 CSP 가 없어 원본 영상·그림을 바로 쓴다(window.MOTION_MEDIA='origin'). 접근은 KB 로그인(kb 역할)이 막는다.
실행: python3 export_kb.py <PillDocKb>/site/motion   → index.html + motion.json·prompt_motion.json·prompt_motion_ko.json"""
import shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEAD = """<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<!-- 생성 파일 — 정본은 motion-prompt repo skills/motion-prompt/preview.html, export_kb.py 로 다시 만든다 -->
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<link rel="icon" href="/static/icon.png">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<script>window.MOTION_MEDIA = 'origin'</script>
"""
BACK = '<a href="/" style="color:inherit;opacity:.7;font-size:13px;text-decoration:none">← PillDocKb</a>\n    <h1>'


def build(out: Path) -> None:
    src = (HERE / 'preview.html').read_text(encoding='utf-8')
    assert src.startswith('<meta charset="utf-8">\n') and src.count('<h1>') == 1, 'preview.html 머리 모양이 바뀜 — 이 스크립트를 맞출 것'
    out.mkdir(parents=True, exist_ok=True)
    body = src.removeprefix('<meta charset="utf-8">\n').replace('<h1>', BACK, 1)
    (out / 'index.html').write_text(HEAD + body + '\n</html>\n', encoding='utf-8')
    for f in ('motion.json', 'prompt_motion.json', 'prompt_motion_ko.json'):
        shutil.copyfile(HERE / 'data' / f, out / f)


if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    build(Path(sys.argv[1]))
    print(f'내보냄 → {sys.argv[1]}', file=sys.stderr)

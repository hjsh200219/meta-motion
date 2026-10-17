#!/usr/bin/env python3
"""hf.py 점검(네트워크 없음) — 레지스트리 목록·제외 항목·host 조각·비율/서체 짚기·브랜드 표시. 실행: python3 test_hf.py"""
import contextlib, io
from build_hf import EXCLUDE, FLOOR
from hf import ITEMS, REG, checks, host, is_brand, search

assert len(REG['items']) >= FLOOR - len(EXCLUDE), len(REG['items'])
assert not set(EXCLUDE) & set(ITEMS) and set(REG['excluded']) == set(EXCLUDE)   # 출처 미확인 자산 항목은 목록에서 빠진다
assert all(it['type'] in ('block', 'component') and it['description'] for it in REG['items'])
assert all(it.get('dimensions') for it in REG['items'] if it['type'] == 'block')  # 블록은 크기가 있어야 --portrait 가 걸러진다

# lint 가 요구하는 속성(host_missing_composition_id·studio_missing_editable_id)이 다 들어가고, CLI 조각의 크기는 유지
h = host('<div data-composition-id="lt-clean-bar" data-composition-src="compositions/lt-clean-bar.html" data-duration="4.8" data-width="1920" data-height="1080"></div>',
         'lt-clean-bar', 'compositions/lt-clean-bar.html', ('1920', '1080'), '4.8', 0, 2)
for a in ('id="lt-clean-bar"', 'class="clip"', 'data-composition-id="lt-clean-bar"', 'data-start="0"', 'data-track-index="2"', 'data-duration="4.8"', 'data-width="1920"'):
    assert a in h, (a, h)
h = host('<!-- paste from x into your composition -->', 'cap', 'compositions/components/cap.html', None, '8', 1, 3)  # 주석만 오는 컴포넌트도 host 를 만든다
assert 'data-composition-src="compositions/components/cap.html"' in h and 'data-start="1"' in h and 'data-width' not in h

src = '<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@700"> width: 1600px; var W = 1400; color:#A6A6A6'
c = ' '.join(checks(src, ('1920', '1080'), (1080, 1920)))
assert '비율 다름' in c and '1400, 1600' in c and 'Poppins' in c and '#838383' in c
assert checks('<div></div>', ('1080', '1920'), (1080, 1920)) == []             # 같은 비율·서체 없음이면 짚을 것 없음

assert is_brand(ITEMS['instagram-follow']) and is_brand(ITEMS['blue-sweater-intro-video'])   # 이름 브랜드 · @계정
assert not is_brand(ITEMS['caption-highlight'])                                             # 태그 tiktok = 스타일, 브랜드 흉내 아님

buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
    search(['caption', 'karaoke'])
assert 'caption-pill-karaoke' in buf.getvalue()
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
    search(['--portrait'])
rows = [l.split('\t') for l in buf.getvalue().splitlines() if l]
assert rows and all(int(r[-4].split('x')[1]) > int(r[-4].split('x')[0]) for r in rows), rows[:2]
print('ok')

#!/usr/bin/env python3
"""build_herk.py — herk-edit-kit 스타일 카드를 템플릿 색·서체로 바꿔 쓰는 도구의 정적 검사(브라우저 없이).
캐시(~/.cache/meta-motion/herk-edit-kit)가 없으면 건너뛴다. 자료 파일(data/anim_herk_*.json)이 있으면 카드와 맞는지도 본다."""
import json, re, sys
from pathlib import Path

import build_herk as hk

if not (hk.LIB / 'registry.json').exists():
    print('test_build_herk: 건너뜀(캐시 없음 — python3 build_herk.py sync)'); sys.exit(0)

cards = hk.cards()
assert len(cards) == 404 and not any(c['id'] in hk.SKIP for c in cards), len(cards)  # 406 − 칸 밖 브랜드 문구 2장
codes = [hk.code_of(c) for c in cards]
assert len(set(codes)) == len(codes) and all(re.fullmatch(r'hk-(paper|glow)-t[12]-[a-z0-9-]+', k) for k in codes)
assert not any(re.search(r'vox|kallaway|ais', k) for k in codes)  # 코드에 실제 채널·크리에이터·브랜드 이름을 쓰지 않는다

# 바꾼 HTML: 브랜드 색 0건 · 쓰는 토큰 변수가 모두 정의됨 · Google Fonts·tokens.css 링크 없음 · 칸 채우기 스크립트가 카드 스크립트보다 먼저
for tpl in ('beige-terracotta', 'charcoal-orange', 'navy-lime'):
    for c in cards:
        h, _ = hk.prepare(c, {}, tpl)
        assert not hk.AIS.search(h) and not hk.AIS_DEEP.search(h), (hk.code_of(c), tpl)
        assert 'tokens.css' not in h and 'fonts.googleapis.com' not in h, hk.code_of(c)
        und = lambda s: set(re.findall(r'var\((--[\w-]+)\s*[,)]', s)) - set(re.findall(r'(--[\w-]+)\s*:', s))
        orig = (hk.LIB / c['file']).read_text(encoding='utf-8') + (hk.LIB / hk.registry_folder(c['style']) / 'tokens.css').read_text(encoding='utf-8')
        assert und(h) <= und(orig), (hk.code_of(c), sorted(und(h) - und(orig))[:5])  # 바꾸면서 정의 안 된 토큰이 새로 생기지 않는다(원본 자체의 누락은 그대로)
        i, j = h.find('meta-motion: 칸(data-slot)'), h.find('window.__timelines')
        assert 0 <= i < j or j < 0, hk.code_of(c)

# 손잡이(data 속성) — @속성 으로 들어간다
bar = next(c for c in cards if hk.code_of(c) == 'hk-paper-t1-stat-bar')
assert hk.knobs(bar) == [('n_fill', 'data-fill', None, '0.73')]
h, _ = hk.prepare(bar, {'n_fill': '0.4'})
assert '"@data-fill": "0.4"' in h

# 자료 파일이 있으면 — 모든 칸(HTML data-slot 전부 + 손잡이)에 예시값이 있고, 안 준 칸이 원본 영어로 남지 않는다
items = hk.items_all()
if items:
    from bs4 import BeautifulSoup
    by = {hk.code_of(c): c for c in cards}
    for k, it in items.items():
        c = by[k]
        _s = BeautifulSoup((hk.LIB / c['file']).read_text(encoding='utf-8'), 'html.parser')
        slots = {el['data-slot'] for el in _s.select('[data-slot]')} - {''}  # 빈 data-slot 은 칸이 아니다
        slots -= {el['data-slot'] for el in _s.select('[data-slot]') if not el.get_text(strip=True) and not el.find('img') and (el.name in hk.TEXT_TAGS or not hk.IMG_SLOT.search(el['data-slot']))}  # 원본에서 비어 있던 글 칸·장식 칸은 비운 채 둔다(#540 2·4차)
        v = hk.vals_of(it)
        assert slots <= set(v), (k, sorted(slots - set(v)))
        assert {x[0] for x in hk.knobs(c)} <= {f['k'] for f in it['fields']} | set(it.get('derive') or {}), k  # 손잡이는 칸이거나 숫자 글 칸에서 계산
        ks = [f['k'] for f in it['fields']]; ls = [f['label'] for f in it['fields']]
        assert len(ks) == len(set(ks)) and len(ls) == len(set(ls)), k  # 같은 키·같은 라벨 없음(KB 리뷰 #540)
        assert not hk.locked(c), k  # 핵심 자료가 칸 밖에 박힌 카드는 넣지 않는다
        assert all(not re.search(r'[A-Za-z]{4,}', str(f['ex'])) or re.fullmatch(r'@\S+', str(f['ex'])) for f in it['fields'] if not f['k'].startswith('n_')), k
        assert it['size'] == [1920, 1080] and it['kit'] == 'herk-edit-kit' and it['path'].startswith('style-library/'), k
        assert not re.search(r'\d+(?:\.\d+)?\s*(?:초|px|배)', it['tpl']), k  # 수치는 장면 순서에만
    # 숫자 글 칸에서 그래픽 손잡이를 계산한다(KB 리뷰 #540 F4)
    assert hk.vals_of(items['hk-paper-t1-stat-arc-gauge'], {'stat': '45%'})['n_pct'] == '45'
    assert hk.vals_of(items['hk-paper-t1-stat-bar'], {'stat': '30%'})['n_fill'] == '0.3'
    _m = hk.vals_of(items['hk-glow-t1-stat-money'], {'stat': '$1.5M'}); assert (_m['n_value'], _m['n_prefix'], _m['n_suffix'], _m['n_decimals']) == ('1500000', '$', 'M', '1')
    assert hk.vals_of(items['hk-glow-t1-stat-delta'], {'stat': '-12%'})['n_dir'] == 'down'
    # 양 끝값 범위·복제 칸(#540 2차)
    assert hk.vals_of(items['hk-paper-t1-stat-linear-meter'], {'stat': '100', 'minLabel': '0', 'maxLabel': '200'})['n_pct'] == '50'
    assert hk.vals_of(items['hk-paper-t1-stat-timeline-point'], {'stat': '2023', 'axisStart': '2015', 'axisEnd': '2035'})['n_pos'] == '0.4'
    assert hk.vals_of(items['hk-paper-t1-stat-spotlight'], {'stat': '7조원'})['stat-blur'] == '7조원'  # 원본 슬롯 이름
    assert 'hk-paper-t1-stat-ticker-tape' not in items  # 원본 영어 소식이 칸 밖에 박힌 카드
    # 칸 밖 짧은 원본 영어는 한국어 기본값 선택 칸으로(#540 3차) — 들어간 카드에 고정 영어가 남지 않는다
    assert all(not hk.fixed_text(by[k]) for k in items)
    _d = items['hk-paper-t2-label-definition']; assert any(f.get('fixed') == 'noun' and f['ex'] == '명사' for f in _d['fields'])
    assert hk.vals_of(_d)['__fixed'] == {'noun': '명사'} and hk.vals_of(_d, {'fx1': '동사'})['__fixed'] == {'noun': '동사'}
    assert all(not f.get('opt') for f in items['hk-paper-t1-stat-ledger']['fields'] if f['k'].startswith('row'))  # 합계에 들어가는 행은 필수
    # 고정 글을 다른 칸 계산 값으로(같은 수를 두 번 받지 않게, #541 1차)
    _r = items['hk-glow-t1-stat-rank']; assert any(f['k'] == 'n_outof' and not f.get('opt') for f in _r['fields'])  # 전체 수는 전용 칸 하나(#541 2차)
    assert hk.vals_of(_r, {'n_outof': '9,500'})['__fixed'] == {'out of 4,200': '전체 9,500 중'}
    assert all(f.get('opt') for c in items.values() for f in c['fields'] if f['k'].startswith('n_') and not str(f.get('ex', '')).strip())  # 예시가 빈 손잡이는 선택
    print(f'test_build_herk: ok (카드 {len(cards)}장 · 자료 {len(items)}장)')
else:
    print(f'test_build_herk: ok (카드 {len(cards)}장 · 자료 파일 없음)')

#!/usr/bin/env python3
"""recommend.py 점검(네트워크 없음) — 장면 나누기·후보 목록·비율 거르기·Jev choice 옵션 상한·결승→적합도 재정렬 흐름(가짜 Jev). 실행: python3 test_recommend.py"""
import collections, sys, types
import recommend
from recommend import FINALISTS, LOW, MAX_OPTIONS, chunks, fits_ratio, items, scenes

assert scenes('가\n\n나\n다\n\n\n라') == ['가', '나\n다', '라']          # 빈 줄 = 장면 경계
assert scenes('첫 줄\n둘째 줄\n') == ['첫 줄', '둘째 줄']                # 빈 줄이 없으면 줄마다
assert scenes(' \n\n ') == []
pool = items()
src = collections.Counter(it['src'] for it in pool)
assert src['card'] == 152 and src['pm'] == 233 and src['hf'] == 444, src     # 요청 카드 + 실전 예시 + 레지스트리
assert len({it['code'] for it in pool}) == len(pool)                         # 코드 겹침 없음
assert all(it['how'] == f"show {it['code']}" for it in pool)                 # 어느 출처든 show 로 자세히 사양을 꺼낸다

# 비율 거르기 — 레지스트리의 고정 크기만 본다(요청 카드·실전 예시·크기 미표기 조각은 남는다)
v = [it for it in pool if fits_ratio(it, '세로')]
h = [it for it in pool if fits_ratio(it, '가로')]
assert collections.Counter(it['src'] for it in v)['card'] == 152 and collections.Counter(it['src'] for it in v)['pm'] == 233
assert 'caption-pill-karaoke' not in {it['code'] for it in v} and 'caption-pill-karaoke' in {it['code'] for it in h}  # 1920x1080 고정
assert len(v) < len(pool) and len(h) < len(pool) and all(fits_ratio(it, '') for it in pool)

# 후보 전체를 넣어도 결승 방식이면 Jev choice 한 번의 옵션이 상한 안이다
for n in (len(pool), len(v), MAX_OPTIONS + 1, 2 * MAX_OPTIONS + 7):
    cs = chunks(list(range(n)))
    assert sorted(x for c in cs for x in c) == list(range(n)) and all(len(c) <= MAX_OPTIONS for c in cs), n
    assert len(cs) * FINALISTS <= MAX_OPTIONS
cs = chunks([{'src': 'card'}] * 100 + [{'src': 'hf'}] * 300)                # 번갈아 담아 한 묶음에 한 출처만 몰리지 않는다
assert all({x['src'] for x in c} == {'card', 'hf'} for c in cs)

# 흐름(가짜 Jev): choice 는 코드 사전순으로 확률을 주고, noul 은 최종 choice 2위만 높게 — 순서는 choice 그대로, 적합도는 카드마다 붙는지 본다
calls, last = collections.Counter(), []
by_name = {it['name']: it['code'] for it in v}
def ask(state, qs):
    assert set(state) == {'scene', 'position', 'previous_scene', 'next_scene'}
    out = {}
    for k, q in qs.items():
        calls[q['type']] += 1
        if q['type'] == 'choice':
            opts = sorted(q['criteria']); assert 2 <= len(opts) <= MAX_OPTIONS
            last[:] = opts
            out[k] = {'probabilities': {o: 1 / (j + 2) for j, o in enumerate(opts)}}
        else:
            name = q['instructions'].split(' 모션: ')[1].split(' — ')[0]
            out[k] = {'noul': 0.95 if by_name.get(name) == last[1] else 0.2}
    return out
fake = types.SimpleNamespace(ask=ask, choice=lambda i, c: {'type': 'choice', 'instructions': i, 'criteria': c},
                             noul=lambda i: {'type': 'noul', 'instructions': i},
                             noul_of=lambda a, k, d=None: (a.get(k) or {}).get('noul', d))
sys.modules['jev'] = fake
r = recommend.recommend_scene(['인사', '숫자 38%', '끝'], 1, v, 3, '세로')
assert calls['choice'] == len(chunks(v)) + 1 and calls['noul'] == 3, calls   # 묶음 결승 + 최종 + 적합도 한 요청(고른 3개)
assert [p['code'] for p in r['picks']] == last[:3] and [p['fit'] for p in r['picks']] == [0.2, 0.95, 0.2]   # 순서는 choice, 적합도는 따로
assert all(set(p) >= {'code', 'fit', 'p', 'src', 'cat'} for p in r['picks']) and 0 < LOW < 1
print('ok')

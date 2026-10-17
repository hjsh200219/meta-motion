#!/usr/bin/env python3
"""recommend.py 점검(네트워크 없음) — 장면 나누기와 후보 목록·Jev choice 옵션 상한. 실행: python3 test_recommend.py"""
import collections
from recommend import FINALISTS, MAX_OPTIONS, chunks, items, scenes

assert scenes('가\n\n나\n다\n\n\n라') == ['가', '나\n다', '라']          # 빈 줄 = 장면 경계
assert scenes('첫 줄\n둘째 줄\n') == ['첫 줄', '둘째 줄']                # 빈 줄이 없으면 줄마다
assert scenes(' \n\n ') == []
pool = items()
src = collections.Counter(it['src'] for it in pool)
assert src['card'] == 152 and src['pm'] == 233 and src['hf'] == 444, src     # 요청 카드 + 실전 예시 + 레지스트리
assert len({it['code'] for it in pool}) == len(pool)                         # 코드 겹침 없음
assert all(it['how'] == f"show {it['code']}" for it in pool)                 # 어느 출처든 show 로 자세히 사양을 꺼낸다

# 분류 3개를 다 넣어 255개를 넘어도 결승 방식이면 Jev choice 한 번의 옵션이 상한 안이다
size = sorted(collections.Counter(it['cat'] for it in pool).values(), reverse=True)
for n in (sum(size[:3]), MAX_OPTIONS + 1, 2 * MAX_OPTIONS + 7):
    cs = chunks(list(range(n)))
    assert sorted(x for c in cs for x in c) == list(range(n)) and all(len(c) <= MAX_OPTIONS for c in cs), n
    assert len(cs) * FINALISTS <= MAX_OPTIONS
cs = chunks([{'src': 'card'}] * 100 + [{'src': 'hf'}] * 300)                # 번갈아 담아 한 묶음에 한 출처만 몰리지 않는다
assert all({x['src'] for x in c} == {'card', 'hf'} for c in cs)
print('ok')

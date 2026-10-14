#!/usr/bin/env python3
"""recommend.py 점검(네트워크 없음) — 장면 나누기와 Jev choice 옵션 상한. 실행: python3 test_recommend.py"""
import collections
from recommend import MAX_OPTIONS, items, scenes

assert scenes('가\n\n나\n다\n\n\n라') == ['가', '나\n다', '라']          # 빈 줄 = 장면 경계
assert scenes('첫 줄\n둘째 줄\n') == ['첫 줄', '둘째 줄']                # 빈 줄이 없으면 줄마다
assert scenes(' \n\n ') == []
pool = items()
assert len(pool) == 385 and len({it['code'] for it in pool}) == 385     # 요청 카드 152 + 실전 예시 233, 코드 겹침 없음
size = sorted(collections.Counter(it['cat'] for it in pool).values(), reverse=True)
assert sum(size[:3]) <= MAX_OPTIONS, size[:3]                          # 분류 3개를 다 넣어도 choice 상한 안
print('ok')

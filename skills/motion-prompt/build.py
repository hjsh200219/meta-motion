#!/usr/bin/env python3
"""nondev-thinking.web.app/motion/ 에서 카드 152개 + 자세히 재료(dx.json) + 조립 코드(compose.js)를 받아 data/ 를 다시 만든다."""
import hashlib, html, json, re, sys, urllib.request
from pathlib import Path

BASE = 'https://nondev-thinking.web.app/motion/'
OUT = Path(__file__).resolve().parent / 'data'
get = lambda p: urllib.request.urlopen(BASE + p, timeout=30).read().decode('utf-8')

page, dx = get(''), json.loads(get('dx.json'))
COMPOSE_SHA = 'd3c4e64e539f87f0'  # motion.py 가 옮긴 조립 규칙 판 — 바뀌면 motion.py 를 다시 맞춰야 한다
compose = get('compose.js')
(OUT / 'compose.mjs').write_text(compose, encoding='utf-8')
if hashlib.sha256(compose.encode()).hexdigest()[:16] != COMPOSE_SHA:
    print('경고: 사이트 조립 규칙(compose.js)이 바뀜 — data/compose.mjs 와 motion.py 를 대조해 맞출 것', file=sys.stderr)
U = html.unescape
cards, cat = [], None
for m in re.finditer(r'<section class="sec" id="cat-\w+"[^>]*><h2[^>]*>([^<]+)</h2>|<article class="mcard" (.*?)</article>', page, re.S):
    if m.group(1):
        cat = U(m.group(1)).strip(); continue
    a = m.group(2)
    attr = lambda k: U(re.search(rf'{k}="([^"]*)"', a).group(1))
    meta = [U(re.sub('<[^>]+>', '', x)) for x in re.findall(r'<span>(.*?)</span>', re.search(r'<div class="meta">(.*?)</div>', a, re.S).group(1))]
    code = attr('id')
    cards.append({
        'code': code, 'cat': cat, 'name': attr('data-name'), 'en': attr('data-en'),
        'plain': U(re.search(r'<p class="plain">(.*?)</p>', a, re.S).group(1)),
        'len': next((x.replace('⏱ ', '') for x in meta if x.startswith('⏱')), ''),
        'when': next((x.replace('이럴 때 · ', '') for x in meta if x.startswith('이럴 때')), ''),
        'inds': attr('data-ind').split(), 'd3': attr('data-d3') == '1',
        'fields': [{'k': k, 'label': U(re.sub('<em>.*?</em>', '', lab)).strip(), 'opt': bool(o), 'ex': U(ex)}
                   for lab, k, o, ex in re.findall(r'<span class="lab">(.*?)</span><input type="text" data-f="(\w+)"( data-opt="1")? data-ex="([^"]*)"', a)],
        'tpl': attr('data-tpl'), 'dx': dx.get(code, {}).get('dx'),
    })
assert len(cards) >= 150, f'카드 {len(cards)}개뿐 — 사이트 구조가 바뀌었는지 확인'
(OUT / 'motion.json').write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding='utf-8')
# 간단 문장이 사이트에 새겨진 문장과 같은지 전수 대조(motion.py 조립 규칙 검증)
sys.path.insert(0, str(OUT.parent)); import motion
motion.CARDS[:] = cards; motion.BY.clear(); motion.BY.update({c['code']: c for c in cards})
site = {c: U(re.sub('<[^>]+>', '', t)).strip() for c, t in re.findall(r'<article class="mcard" id="(\w+)".*?<p class="ask-txt" data-lvl="s">(.*?)</p>', page, re.S)}
bad = [c['code'] for c in cards if motion.simple(motion.TOOLS['auto'], c, {}, {'ratio': '가로 16:9', 'color': '', 'file': ''}) != site.get(c['code'])]
if bad: print(f'경고: 간단 문장 불일치 {len(bad)}개 {bad[:5]} — motion.py 조립 규칙 점검', file=sys.stderr)
print(f'카드 {len(cards)}개 · dx 없음 {sum(not c["dx"] for c in cards)}개 → {OUT}', file=sys.stderr)

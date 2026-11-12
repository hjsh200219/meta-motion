"""claude-animation-skills 6개(MIT © 2026 Artem Novitckii)를 한 카탈로그에 넣었는지 검사. python3 test_animskills.py (네트워크 없음)."""
import collections, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animskills, catalog, motion, recommend

HERE = os.path.dirname(os.path.abspath(__file__))
run = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, 'motion.py'), *a], capture_output=True, text=True)
CODES = {'as-graph', 'as-map-route', 'as-breakdown', 'as-line-art', 'as-stick-figure', 'as-3d-cartoon'}

idx = animskills.load()
assert set(idx['items']) == CODES, set(idx['items'])
assert idx['license'].startswith('MIT') and len(idx['commit']) == 40 and idx['source'].startswith('https://github.com/artemnovitckii/')
assert {c['skill'] for c in idx['items'].values()} == {'graph', 'map-route', 'breakdown', 'minimalistic-graphics', 'stick-figure', 'zach-d-films'}
cats = {c['cat'] for c in motion.CARDS}
for code, c in idx['items'].items():  # 같은 카드 꼴 — 기존 16개 분류 안에서만, 사양 문장이 조립된다
    assert c['cat'] in cats, (code, c['cat'])
    assert c['tpl'] and c['fields'] and c['dx']['beats'] and c['plain'] and c['when'] and c['len'], code
    assert os.path.exists(os.path.join(HERE, 'data', 'as_thumb', f'{code}.jpg')), code
    assert 'zach' not in c['name'].lower() and 'zack' not in c['name'].lower(), code  # 실제 크리에이터 이름은 제목에 쓰지 않는다

# 한 목록: motion·catalog·recommend 어디서나 보이고 id 가 겹치지 않는다
ev = {c['code']: c for c in motion.everything()}
assert CODES <= set(ev) and all(ev[k]['src'] == 'as' for k in CODES)
by = {i['id']: i for i in catalog.items()}
for k in CODES:
    p = by[k]['provenance']
    assert by[k]['kind'] == 'motion' and p['source'] == 'animation-skills' and p['license'].startswith('MIT') and p['creator'] == 'Artem Novitckii', p
    assert by[k]['size'] == (1080, 1920), by[k]['size']
assert catalog.search(['분해도'])[0]['id'] == 'as-breakdown'
assert 'as-map-route' in {i['id'] for i in catalog.search(['지도', '경로'])}
pool = {it['code']: it for it in recommend.items()}
assert CODES <= set(pool) and collections.Counter(it['src'] for it in pool.values())['as'] == 6
assert recommend.fits_ratio(pool['as-graph'], '세로') and not recommend.fits_ratio(pool['as-graph'], '가로')  # 1080x1920 고정

# 명령: show 는 사양 문장 + 원본 스킬(고정 커밋 캐시)과 만드는 법, list·search 꼬리표
r = run('show', 'as-graph', '-v'); assert r.returncode == 0, r.stderr
assert '[원본 스킬]' in r.stdout and 'build.py' in r.stdout and idx['commit'][:7] in r.stdout and 'MIT' in r.stdout, r.stdout
r = run('show', 'as-stick-figure'); assert '음성' in r.stdout, r.stdout  # 엔진 둘은 한 편짜리 작업이라고 알린다
assert '내레이션·음악·효과음 없음' not in r.stdout and '내레이션·음악·효과음 없음' in run('show', 'as-graph').stdout  # 음성이 붙는 엔진에 「내레이션 없음」을 붙이지 않는다
r = run('search', '막대', '인간'); assert 'as-stick-figure' in r.stdout and '애니메이션 스킬' in r.stdout, r.stdout
print('test_animskills: ok')

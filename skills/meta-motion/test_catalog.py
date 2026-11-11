"""catalog.py 검사 — 출처를 나누지 않는 한 카탈로그(모션·기법·템플릿). python3 test_catalog.py (네트워크 없음)."""
import contextlib, io, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog, cokac, fonts, hf, motion

HERE = os.path.dirname(os.path.abspath(__file__))
run = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, 'motion.py'), *a], capture_output=True, text=True)

items = catalog.items()
by = {i['id']: i for i in items}
# 수: 모션(요청 카드·실전 예시·레지스트리) + 기법 + 템플릿 — 하나라도 빠지거나 겹치면 안 된다
n_motion, n_tech, n_theme = len(motion.everything()), len(cokac.load()['items']), len(fonts.TEMPLATES)
assert len(items) == len(by) == n_motion + n_tech + n_theme, (len(items), len(by), n_motion, n_tech, n_theme)
assert {k: sum(i['kind'] == k for i in items) for k in ('motion', 'technique', 'theme')} == {'motion': n_motion, 'technique': n_tech, 'theme': n_theme}
# 공통 필드는 모든 항목에 있다
KEYS = {'id', 'aliases', 'kind', 'title', 'summary', 'when', 'tags', 'category', 'actions', 'provenance', 'brand', 'size', 'search'}
assert all(KEYS <= set(i) for i in items), [i['id'] for i in items if not KEYS <= set(i)][:3]

# 출처·권리 정보는 그대로 따라온다
pm = next(i for i in items if i['provenance']['source'] == 'prompt-motion')
assert pm['provenance']['creator'] and pm['provenance']['url'].startswith('https://prompt-motion.com'), pm['provenance']
assert by['caret-swap']['provenance']['license'] == 'MIT AND OFL-1.1' and by['caption-pill-karaoke']['provenance']['license'] == 'Apache-2.0'
assert by['instagram-follow']['brand'] is True and by['caption-pill-karaoke']['brand'] is False
assert by['12-stable-fluids']['provenance']['license'].startswith('MIT') and '12' in by['12-stable-fluids']['aliases']
assert by['navy-lime']['kind'] == 'theme' and 'show' in by['navy-lime']['actions']
assert 'add' in by['caption-pill-karaoke']['actions'] and 'add' not in by['I02']['actions']
# 쓰지 않는 레지스트리 항목(자산 출처 미확인)은 어디에도 없다
assert not set(hf.REG['excluded']) & set(by), set(hf.REG['excluded']) & set(by)

# 찾기: 출처 구분 없이 한 번에 — 만든 사람·기법 이름·템플릿 이름으로도
assert {i['kind'] for i in catalog.search(['잉크'])} >= {'motion', 'technique'}
assert any(i['id'] == pm['id'] for i in catalog.search([pm['provenance']['creator'].lower()]))
assert [i['id'] for i in catalog.search(['남색', '라임'], kind='theme')] == ['navy-lime']
assert catalog.find('12')['id'] == '12-stable-fluids' and catalog.find('I02')['kind'] == 'motion' and catalog.find('없는것') is None

# 색 배선 한곳: 사용자 색 > 템플릿 · 토큰은 템플릿 값 그대로
th = fonts.resolve_theme('navy-lime')
assert th['template'] == 'navy-lime' and th['color'] == fonts.TEMPLATES['navy-lime']['color'] and th['tokens']['accent'] == fonts.TEMPLATES['navy-lime']['accent']
assert th['title_font']['id'] == fonts.TEMPLATES['navy-lime']['font'] and th['caption_font']['id'] == fonts.TEMPLATES['navy-lime']['caption_font']
assert fonts.resolve_theme('navy-lime', color='빨강과 흰색')['color'] == '빨강과 흰색'

# 명령: 하나의 명령 집합 — show 가 모든 종류를, 옛 명령은 그대로
r = run('show', 'navy-lime'); assert r.returncode == 0 and '#C9FE3A'.lower() in r.stdout.lower(), r.stdout + r.stderr
r = run('show', 'I02', '--template', 'navy-lime', '-v'); assert r.returncode == 0 and '라임' in r.stdout and '[색 토큰]' in r.stdout, r.stdout + r.stderr
r = run('search', '잉크'); assert r.returncode == 0 and '12-stable-fluids' in r.stdout and '[기법' in r.stdout, r.stdout
r = run('search', '남색', '라임'); assert 'navy-lime' in r.stdout and '[템플릿' in r.stdout, r.stdout
r = run('list'); assert '## 표현 기법' in r.stdout and '## 색·서체 템플릿' in r.stdout, r.stdout[-500:]
# 옛 명령(별칭) — 출력 계약 유지
old = run('search', '--cards', '로고').stdout
assert old and '[기법' not in old and '[템플릿' not in old  # --cards 는 예전처럼 요청 카드만
assert run('technique', '12').stdout == run('show', '12-stable-fluids').stdout
assert run('examples', 'chart').returncode == 0 and run('registry', 'caption', 'karaoke').returncode == 0
# 맨 앞 출처 표기 — 실전 예시 show 는 만든 사람, 기법 show 는 규칙 경고
assert pm['provenance']['creator'] in run('show', pm['id']).stdout
print('test_catalog: ok')

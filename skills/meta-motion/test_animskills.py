"""애니메이션 스킬(GitHub 모션 키트 여러 곳)을 한 카탈로그에 넣었는지 검사. python3 test_animskills.py (네트워크 없음).
키트: claude-animation-skills 6개(2026-11-13) + 쇼츠 «10 GitHub Repos That Level Up HyperFrames Videos» 의 키트들(2026-11-22)."""
import collections, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animskills, catalog, motion, recommend

HERE = os.path.dirname(os.path.abspath(__file__))
run = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, 'motion.py'), *a], capture_output=True, text=True)
ORIG = {'as-graph', 'as-map-route', 'as-breakdown', 'as-line-art', 'as-stick-figure', 'as-3d-cartoon'}
KITS = {'claude-animation-skills', 'reelforge', 'hyperframes-motion-library', 'tegaki', 'animated-diagrams-skill', 'saas-motion-kit',
        'huashu-design', 'product-launch-motion'} | ({'herk-edit-kit'} if any(f.exists() for f in animskills.HERK) else set())  # herk 스타일 카드(build_herk.py) — 자료 파일이 있을 때만
PREFIX = {'herk-edit-kit': 'hk-', 'claude-animation-skills': 'as-', 'reelforge': 'rf-', 'hyperframes-motion-library': 'ml-', 'tegaki': 'tg-',
          'animated-diagrams-skill': 'dg-', 'saas-motion-kit': 'tr-', 'huashu-design': 'hs-', 'product-launch-motion': 'pl-'}

idx = animskills.load()
assert set(idx['kits']) == KITS, set(idx['kits'])
for name, k in idx['kits'].items():  # 출처마다 고정 커밋·라이선스·만든 사람
    assert k['source'].startswith('https://github.com/') and len(k['commit']) == 40 and k['license'] and k['creator'], name
    assert k['license'].startswith(('MIT', 'Apache-2.0')), (name, k['license'])
items = idx['items']
assert ORIG <= set(items) and len(items) >= 80, len(items)
cats = {c['cat'] for c in motion.CARDS}
for code, c in items.items():  # 같은 카드 꼴 — 기존 16개 분류 안에서만, 사양 문장이 조립된다
    assert c['kit'] in KITS and code.startswith(PREFIX[c['kit']]), (code, c.get('kit'))
    assert c['cat'] in cats, (code, c['cat'])
    assert c['tpl'] and c['fields'] and c['dx']['beats'] and c['plain'] and c['when'] and c['len'] and c['path'], code
    assert c['size'] is None or (len(c['size']) == 2 and all(isinstance(n, int) for n in c['size'])), (code, c['size'])
    assert all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', f['k']) and f['k'] not in ('ratio', 'color', 'file', 'tool') for f in c['fields']), code  # 전역 옵션 이름이면 덮어써진다 · motion-library 는 변수 id(camelCase) 그대로
    assert os.path.exists(os.path.join(HERE, 'data', 'as_thumb', f'{code}.jpg')) == bool(c.get('thumb')), code  # 그림은 thumb 원천이 있는 것만
    assert not re.search(r'netflix|apple|zach|zack|vox|kallaway|cheerful', c['name'], re.I), code  # 실제 회사·크리에이터 이름은 제목에 쓰지 않는다
    assert not c['dx']['base'] or all(b['t0'] < 0 or (0 <= b['t0'] <= b['t1'] <= c['dx']['base'] + 0.01) for b in c['dx']['beats']), (code, c['dx']['base'])  # 초 있는 구간은 카드 길이 안(KB 리뷰 2026-11-22 — 루프·셋째 줄이 길이 밖에 있던 것)
    assert not c['dx']['base'] or all((b['t0'] < 0) == bool(b['label']) for b in c['dx']['beats']), code  # 이름(label) 붙은 것은 초 없는 규칙 — 초 있는 구간에 붙으면 진행표에서 빠진다
# 색 칸이 있으면 모양 문장도 같은 칸을 쓴다 — 고정 원본 색과 입력 색이 한 요청에 함께 들어가지 않게(KB 리뷰 14차)
for code, c in items.items():
    for f in c['fields']:
        if f['k'] in ('accent_color', 'background', 'palette', 'scheme') and c['dx'].get('look') and not code.startswith('hk-'):
            assert '{%s}' % f['k'] in c['dx']['look'] and not f['opt'], (code, f['k'])
# 손글씨는 길이 칸을 비우면 문구 길이로 — 쓰기 끝이 카드 실측(7.66초)보다 뒤, 그 뒤 1.2초 이상 머묾
hw = items['tg-handwriting']
assert motion.auto_len(hw, {}) == 7.7 and motion.auto_len(hw, {'text': '오늘도 감사합니다'}) == 9.1  # 원본 글자별 glyph.t 표(15차)
w = hw['dx']['beats'][hw['dx']['auto']['beat']]['t1'] * 9.1 / hw['dx']['base']
assert 7.66 <= w <= 9.1 - 1.2, w
assert len(hw['dx']['auto']['t']) > 700 and max(hw['dx']['auto']['t'].values()) == 2.41
# 비운 선택 칸이 가리키는 요소는 [비운 칸] 으로 빼라고 알린다(KB 리뷰 15차) — 채우면 붙지 않는다
assert '[비운 칸] 작은 윗글자·좌표 글자·작은 메모' in run('show', 'rf-zoom-portal').stdout
assert '[비운 칸]' not in run('show', 'rf-zoom-portal', 'kicker=다음', 'coordinate=좌표', 'note=메모').stdout
# [[A||B]]: 칸을 비우면 B(원본 설명), 채우면 A — 막대 색(16차 F2)
assert motion.compose('[[막대 {c}||회색]]', lambda k: None) == '회색' and motion.compose('[[막대 {c}||회색]]', lambda k: '빨강') == '막대 빨강'
# 손글씨 길이를 문구보다 짧게 넣으면 최소 길이로(16차 F1)
assert '최소 길이로 잡음' in run('show', 'tg-handwriting', 'dur=1초').stdout and '전체 20초' in run('show', 'tg-handwriting', 'dur=20초').stdout
# 개수가 같아야 하는 쉼표 칸은 어긋나면 맨 앞 [입력 확인](17차 F3), 여러 줄 칸은 앞 들여쓰기 유지(17차 F2)
assert run('show', 'ml-bar-chart-grow', 'labels=가,나,다,라,마').stdout.startswith('[입력 확인] 항목 이름 5개·숫자 4개')
assert all('[입력 확인]' not in run('show', k).stdout for k in ('ml-bar-chart-grow', 'ml-line-chart-draw', 'as-graph', 'dg-concept'))
assert '\n    들여쓴 첫 줄\n' in run('show', 'dg-code-walkthrough', 'code=    들여쓴 첫 줄\n둘째 줄').stdout
# 18차: 간단 모드에도 손글씨 길이, 맞대결 기호는 비우면 숫자로·모순이면 [입력 확인], 꺾은선 숫자 2개 이상
assert '\n전체 길이 약 9.1초(문구 길이로 잡음).' in run('show', 'tg-handwriting', '--simple', 'text=오늘도 감사합니다').stdout
assert '기호: <.' in run('show', 'ml-stat-duel', 'leftValue=80', 'rightValue=90').stdout
assert run('show', 'ml-stat-duel', 'leftValue=80', 'rightValue=90', 'operator=>').stdout.startswith('[입력 확인] 기호 「>」')
assert run('show', 'ml-line-chart-draw', 'labels=1월', 'values=3').stdout.startswith('[입력 확인] 숫자는 2개 이상')
# 19차: .5 도 숫자로, 결론은 선택 칸, 숫자 목록에 숫자 아닌 값이면 [입력 확인]
assert '기호: <.' in run('show', 'ml-stat-duel', 'leftValue=.5', 'rightValue=1').stdout and '[입력 확인]' not in run('show', 'ml-stat-duel', 'leftValue=.5', 'rightValue=1', 'operator=<').stdout
assert '결론' not in run('show', 'ml-stat-duel', '--simple', 'leftValue=80', 'rightValue=90').stdout
assert run('show', 'ml-line-chart-draw', 'labels=1월,2월', 'values=120,미정').stdout.startswith('[입력 확인] 숫자에 숫자가 아닌 값(미정)')
assert all('[입력 확인]' not in run('show', k).stdout for k in ('ml-stat-duel', 'ml-bar-chart-grow', 'ml-line-chart-draw', 'as-graph'))
# 원래 6개는 그대로(기존 스킬 이름·크기)
assert {items[k]['skill'] for k in ORIG} == {'graph', 'map-route', 'breakdown', 'minimalistic-graphics', 'stick-figure', 'zach-d-films'}
assert all(items[k]['kit'] == 'claude-animation-skills' and items[k]['size'] == [1080, 1920] for k in ORIG)
# 넣지 않기로 한 것 — openai/plugins(HeyGen 공식 스킬 사본). herk-edit-kit 카드는 2026-11-23 사용자 결정으로 템플릿 토큰을 바꿔 넣었다(build_herk.py)
assert not any(k.startswith('oa-') for k in items)
assert all(items[k]['kit'] == 'herk-edit-kit' for k in items if k.startswith('hk-'))
assert not any(k.startswith('hk-') for k in items) or len([k for k in items if k.startswith('hk-')]) >= 330  # 넣었으면 검증·자료 잠금 검사를 통과한 344장 안팎

# 한 목록: motion·catalog·recommend 어디서나 보이고 id 가 겹치지 않는다
ev = {c['code']: c for c in motion.everything()}
assert set(items) <= set(ev) and all(ev[k]['src'] == 'as' for k in items)
by = {i['id']: i for i in catalog.items()}
for k, c in items.items():
    kit, p = idx['kits'][c['kit']], by[k]['provenance']
    assert by[k]['kind'] == 'motion' and p['source'] == 'animation-skills' and p['license'] == kit['license'] and p['creator'] == kit['creator'], (k, p)
    assert p['url'].startswith(kit['source']) and kit['commit'][:7] in p['url'] and p['commit'] == kit['commit'], (k, p['url'])
    assert by[k]['size'] == (tuple(c['size']) if c['size'] else None), (k, by[k]['size'])
    assert kit['license'].split()[0] in catalog.label(by[k]), catalog.label(by[k])  # 꼬리표에 그 출처의 라이선스
assert catalog.search(['분해도'])[0]['id'] == 'as-breakdown'
assert 'as-map-route' in {i['id'] for i in catalog.search(['지도', '경로'])}
pool = {it['code']: it for it in recommend.items()}
assert set(items) <= set(pool) and collections.Counter(it['src'] for it in pool.values())['as'] == len(items)
assert recommend.fits_ratio(pool['as-graph'], '세로') and not recommend.fits_ratio(pool['as-graph'], '가로')  # 1080x1920 고정
land = next(k for k, c in items.items() if c['size'] == [1920, 1080])
assert recommend.fits_ratio(pool[land], '가로') and not recommend.fits_ratio(pool[land], '세로'), land  # 크기는 항목마다
free = next(k for k, c in items.items() if c['size'] is None)
assert recommend.fits_ratio(pool[free], '가로') and recommend.fits_ratio(pool[free], '세로'), free

# 명령: show 는 사양 문장 + 원본(고정 커밋)과 만드는 법, list·search 꼬리표
r = run('show', 'as-graph', '-v'); assert r.returncode == 0, r.stderr
assert '[원본 스킬]' in r.stdout and 'build.py' in r.stdout and idx['kits']['claude-animation-skills']['commit'][:7] in r.stdout and 'MIT' in r.stdout, r.stdout
r = run('show', 'as-stick-figure'); assert '음성' in r.stdout, r.stdout  # 엔진 둘은 한 편짜리 작업이라고 알린다
assert '내레이션·음악·효과음 없음' not in r.stdout and '내레이션·음악·효과음 없음' in run('show', 'as-graph').stdout  # 음성이 붙는 엔진에 「내레이션 없음」을 붙이지 않는다
r = run('search', '막대', '인간'); assert 'as-stick-figure' in r.stdout and '애니메이션 스킬' in r.stdout, r.stdout
for kit in KITS - {'claude-animation-skills'}:  # 새 출처마다 한 장씩 — 원본 경로·커밋·만드는 법
    code = next(k for k, c in items.items() if c['kit'] == kit)
    r = run('show', code); assert r.returncode == 0, (code, r.stderr)
    k = idx['kits'][kit]
    assert '[원본]' in r.stdout and k['commit'][:7] in r.stdout and items[code]['path'].split('#')[0] in r.stdout and '[만드는 법]' in r.stdout, r.stdout
    assert k['license'].split()[0] in run('search', code).stdout, code
print(f'test_animskills: ok ({len(items)}개 · 출처 {len(idx["kits"])}곳)')

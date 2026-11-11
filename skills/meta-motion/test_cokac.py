"""cokac.py 검사 — python3 test_cokac.py (네트워크 없음: 가짜 색인·가짜 캐시로)."""
import io, json, os, sys, tempfile, contextlib
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cokac, build_cokac

SRC = {'name': 'aimotion', 'principle': '기술만 가져간다.', 'count': 3, 'groups': ['웹 그래픽 기법', 'GSAP'],
       'demos': [
           {'id': '01-svg-ink', 'number': 1, 'title': '먹 한 방울', 'tech': 'SVG 필터 · feTurbulence', 'group': '웹 그래픽 기법',
            'scene': '한지 위로 먹 한 방울', 'points': ['젖은 먹'], 'libraries': [], 'cautions': [], 'files': ['main.js'], 'poster': True, 'sheet': True},
           {'id': '61-gsap-flip', 'number': 61, 'title': '자리 바꾸기', 'tech': 'GSAP Flip', 'group': 'GSAP',
            'scene': '카드가 섞인다', 'points': ['Flip.from'], 'libraries': ['GSAP'], 'cautions': ['플러그인 필요'], 'files': ['main.js'], 'poster': True, 'sheet': False},
           {'id': '04-sketch', 'number': 4, 'title': '손으로 그린 설명', 'tech': 'rough.js 손그림', 'group': '웹 그래픽 기법',
            'scene': '스케치북', 'points': [], 'libraries': ['rough.js'], 'cautions': [], 'files': ['main.js'], 'poster': False, 'sheet': False},
       ]}

# 색인 만들기: 원본 index.json → 필요한 칸만 · 출처·커밋·라이선스를 붙인다 · 150개 미만이면 거절(부분 수집 방지)
idx = build_cokac.convert(SRC, commit='c417b16c6020c25949845051f00f1c964d7e6d54', fetched='2026-11-11', minimum=3)
assert idx['commit'] == 'c417b16c6020c25949845051f00f1c964d7e6d54' and idx['license'].startswith('MIT') and idx['rule'] == '기술만 가져간다.', idx
assert [d['id'] for d in idx['items']] == ['01-svg-ink', '04-sketch', '61-gsap-flip']  # 번호순
assert set(idx['items'][0]) == {'id', 'number', 'title', 'tech', 'group', 'scene', 'points', 'libraries', 'cautions'}
try:
    build_cokac.convert(SRC, commit='x', fetched='x', minimum=150); raise AssertionError('150개 미만인데 통과')
except SystemExit as e:
    assert '150' in str(e)

# 찾기: 여러 단어는 AND · 제목·기법·분류·장면·요점·라이브러리 어디서든 · --group 으로 분류 제한
assert [d['id'] for d in cokac.find(idx, ['먹'])] == ['01-svg-ink']
assert [d['id'] for d in cokac.find(idx, ['gsap'])] == ['61-gsap-flip']
assert [d['id'] for d in cokac.find(idx, ['손그림', 'rough'])] == ['04-sketch']
assert [d['id'] for d in cokac.find(idx, [], group='웹 그래픽')] == ['01-svg-ink', '04-sketch']
assert cokac.find(idx, ['없는말']) == []
# 고르기: id 또는 번호
assert cokac.pick(idx, '61')['id'] == '61-gsap-flip' and cokac.pick(idx, '04-sketch')['number'] == 4 and cokac.pick(idx, '9') is None

# 보기: 규칙을 맨 앞에 · 캐시에 받은 NOTES.md 전문 · 소스 경로 · 출처
with tempfile.TemporaryDirectory() as td:
    demo = Path(td) / 'skills' / 'aimotion' / 'demos' / '01-svg-ink'
    demo.mkdir(parents=True)
    (demo / 'NOTES.md').write_text('# 01 · 먹 한 방울\n## 기법과 원리\n- feTurbulence', encoding='utf-8')
    (demo / 'main.js').write_text('// x', encoding='utf-8')
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cokac.show(idx, idx['items'][0], cache=Path(td))
    out = buf.getvalue()
    assert out.index('기술만 가져간다') < out.index('## 기법과 원리'), out
    assert str(demo / 'main.js') in out and 'MIT' in out and 'c417b16' in out, out
print('test_cokac: ok')

"""check.py 검사 — python3 test_check.py (네트워크·브라우저 없음 · 안전 영역 실제 실행은 SKILL.md 의 check 명령으로 따로 확인)."""
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check

with tempfile.TemporaryDirectory() as td:
    p = Path(td)
    (p / 'compositions').mkdir()
    (p / 'js').mkdir()
    (p / 'node_modules' / 'x').mkdir(parents=True)
    # 컴포지션 HTML: lint 가 이미 잡는 Math.random 은 다시 알리지 않고, lint 가 놓치는 것만 알린다
    (p / 'index.html').write_text('<script>\nconst a = Math.random();\nsetTimeout(() => go(), 50);\n'
                                  'tl.to("#t", { scrambleText: { text: "A" } }, 1);\n</script>', encoding='utf-8')
    (p / 'compositions' / 's2.html').write_text('<script>\ngsap.ticker.add(tick);\n// setInterval 은 주석이라 무시\n'
                                                 'gsap.delayedCall(1, f);\n</script>', encoding='utf-8')
    # 외부 JS 는 lint 가 아예 보지 않는다 — 전부 알린다
    (p / 'js' / 'scene.js').write_text('const r = Math.random();\nconst n = Date.now();\nrequestAnimationFrame(f);\n'
                                       'const ok = rand(seed); // Math.random 대신 시드\n', encoding='utf-8')
    # 남의 라이브러리·묶음 파일은 보지 않는다
    (p / 'js' / 'gsap.min.js').write_text('Math.random();setTimeout(f)', encoding='utf-8')
    (p / 'node_modules' / 'x' / 'i.js').write_text('Math.random()', encoding='utf-8')

    got = [(f['file'], f['line'], f['code']) for f in check.scan(p)]
    assert got == [
        ('compositions/s2.html', 2, 'gsap_ticker'),
        ('compositions/s2.html', 4, 'gsap_delayed_call'),
        ('index.html', 3, 'timer'),
        ('index.html', 4, 'scramble_text'),
        ('js/scene.js', 1, 'math_random'),
        ('js/scene.js', 2, 'date_now'),
        ('js/scene.js', 3, 'raf'),
    ], got
    # 한 줄이 1000자를 넘는 JS(압축 묶음)와 .min/.iife/.bundle/.umd 이름은 남의 라이브러리로 보고 건너뛴다 — 건너뛴 파일은 따로 알린다
    (p / 'js' / 'shaders.iife.js').write_text('Math.random()', encoding='utf-8')
    (p / 'js' / 'packed.js').write_text('Math.random();' + 'x' * 1200, encoding='utf-8')
    assert [r for _, r in check.files(p)] == ['compositions/s2.html', 'index.html', 'js/scene.js'], list(check.files(p))
    assert check.skipped(p) == ['js/packed.js'], check.skipped(p)  # 이름이 .min/.iife 인 것은 라이브러리가 분명해 알리지 않는다
    sev = {f['code']: f['severity'] for f in check.scan(p)}
    assert sev['timer'] == 'warning' and sev['math_random'] == 'error' and sev['gsap_delayed_call'] == 'warning', sev

# 안전 영역 띠: 9:16 기본은 위 250·아래 350·오른쪽 50px — caption-zone 비율 문자열로 바꾼다
z = check.zones(1080, 1920, seek='0.2,0.7')
assert [n for n, _ in z] == ['top', 'bottom', 'right'], z
assert z[0][1] == 'x0=0;y0=0;x1=1;y1=0.1302;severity=warning;seek=0.2,0.7', z[0]
assert z[1][1] == 'x0=0;y0=0.8177;x1=1;y1=1;severity=warning;seek=0.2,0.7', z[1]
assert z[2][1] == 'x0=0.9537;y0=0;x1=1;y1=1;severity=warning;seek=0.2,0.7', z[2]

# seek 는 영상 전체 길이에 대한 비율이다(실측: seek=.5 = 73.04초 영상의 36.52초 한 곳뿐) — 루트 아래 클립마다 가운데 시각을 비율로
ROOT = ('<div id="root" data-composition-id="main" data-start="0" data-duration="10" data-width="1080" data-height="1920">'
        '<div id="s1" class="clip" data-start="0" data-duration="4"></div><div id="s2" data-start="4" data-duration="6" data-composition-src="c/s2.html"></div>'
        '<div id="cap" data-start="0.5" data-duration="3.5"></div><audio id="a" data-start="1" data-duration="2"></audio>'
        '<div id="dup" data-start="0" data-duration="4.0"></div></div>')
assert check.seeks(ROOT) == '0.2,0.225,0.7', check.seeks(ROOT)
assert check.seeks('<div data-composition-id="main" data-width="1080" data-height="1920"></div>') == '0.5'  # 클립이 없으면 가운데 한 번
# 가로 영상은 플랫폼 UI 가 덮지 않으니 띠 없음 · 값을 0 으로 주면 그 띠를 뺀다
assert check.zones(1920, 1080) == []
assert [n for n, _ in check.zones(1080, 1920, top=0)] == ['bottom', 'right']
assert check.zones(1080, 1920, top=240, bottom=480, right=180)[2][1].startswith('x0=0.8333;')

# 프로젝트 크기는 루트 index.html 의 data-width/height
with tempfile.TemporaryDirectory() as td:
    (Path(td) / 'index.html').write_text('<div id="root" data-composition-id="main" data-width="1080" data-height="1920">', encoding='utf-8')
    assert check.size(Path(td)) == (1080, 1920)
print('test_check: ok')

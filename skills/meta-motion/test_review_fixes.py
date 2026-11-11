"""2026-11-11 Astra(EDB) 검토 지적 회귀 시험 — python3 test_review_fixes.py (네트워크·Jev·브라우저 없음)."""
import json, os, re, shlex, sys, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, film, fonts, hf, localnet, motion, build_pm, build_card_anim

REC = {"ratio": "세로", "low": 0.5, "scenes": [
    {"scene": "첫 장면", "low": False, "picks": [{"code": "T03", "name": "쇼츠 3초 훅", "cat": "타이틀", "src": "card", "fit": 0.8, "p": 0.4}]}]}

# 1. film split.sh — 공백·셸 문법이 든 원본 경로를 인용한다
out = film.build(REC, [3.0], source='clips/my reel $(rm -rf x);.mp4')
for line in out['ffmpeg']:
    args = shlex.split(line)
    assert args[args.index('-i') + 1] == 'clips/my reel $(rm -rf x);.mp4', line

# 10. film base.css — 제목(.line)은 제목 서체, 자막(.sub)은 자막 서체 · 굵기도 각자
pal = fonts.TEMPLATES['black-neon']
css = film.base_css(pal, title=('GasoekOne', 400), caption=('Pretendard-ExtraBold', 800))
line = re.search(r'\.line \{([^}]*)\}', css).group(1)
sub = re.search(r'\.sub \{([^}]*)\}', css).group(1)
assert '"GasoekOne"' in line and 'font-weight:400' in line, line
assert '"Pretendard-ExtraBold"' in sub and 'GasoekOne' not in sub and 'font-weight:800' in sub, sub

# 2. localnet — pidfile 의 pid 가 지금 이 도구의 서버가 아니면(pid 재사용) 끄지 않는다
with patch.object(localnet, '_listeners', return_value=[4242]), patch.object(localnet, '_read_pid', return_value=4242), \
        patch.object(localnet, '_is_ours', return_value=False), patch.object(localnet.os, 'kill') as kill:
    assert localnet.free_port(8765, '/nonexistent') is False
    kill.assert_not_called()

# 3. build_pm — 빈 수집·크게 줄어든 수집은 기존 파일을 덮지 않는다
for rows, slugs, old in (([], [], 233), ([{}] * 10, ['a'] * 10, 233), ([{}] * 5, ['a'] * 9, 0)):
    try:
        build_pm.validate(rows, slugs, old); raise AssertionError(f'통과하면 안 됨: {len(rows)}/{len(slugs)} 기존 {old}')
    except SystemExit:
        pass
build_pm.validate([{}] * 230, ['a'] * 240, 233)  # 정상

# 6. fonts — 같은 시리즈 이력이 있으면 Jev 를 부르지 않는다
with tempfile.TemporaryDirectory() as td:
    h = Path(td) / 'h.jsonl'
    h.write_text(json.dumps({'slug': 'ep1', 'series': 's', 'template': 'navy-lime', 'summary': 'x'}) + '\n', encoding='utf-8')
    with patch.object(fonts, 'judge_jev', side_effect=AssertionError('Jev 호출됨')), patch.object(fonts, 'ensure_installed', return_value=[]):
        r = fonts.pick('대본', series='s', history_path=str(h))
    assert r['template'] == 'navy-lime' and r['template_how'] == 'series:ep1', r

# 7. fonts — Jev 없이 기본 템플릿으로 갈 때도 제외 목록을 지킨다 · 남은 후보가 없으면 실패
tpl, how = fonts.choose_template(None, None, 0, 'info', exclude=('light-teal',))
assert tpl != 'light-teal' and tpl in fonts.TEMPLATES, tpl
try:
    fonts.choose_template(None, None, 0, 'info', exclude=tuple(fonts.TEMPLATES)); raise AssertionError('후보 없음인데 통과')
except SystemExit:
    pass

# 8. check — --strict 는 비결정 코드 경고에도 적용
with tempfile.TemporaryDirectory() as td:
    (Path(td) / 'index.html').write_text('<script>setTimeout(f, 1)</script>', encoding='utf-8')
    for args, code in ((['--no-zone'], 0), (['--no-zone', '--strict'], 1)):
        try:
            check.main([td, *args]); raise AssertionError('종료 안 함')
        except SystemExit as e:
            assert e.code == code, (args, e.code)

# 9. check — 영역 요청과 판정이 같은 배율(2160x3840 에서 위 경고 띠 = 480px = 비율 0.125)
z = dict(check.zones(2160, 3840))
assert z['top'].startswith('x0=0;y0=0;x1=1;y1=0.125;'), z['top']
assert check.classify('top', {'rect': {'left': 0, 'top': 300, 'right': 10, 'bottom': 350}}, 2160, 3840, check.LIMITS) == 'warning'  # 4K 에서 오류 띠 240·경고 띠 480

# 4·5. 레지스트리 항목 라이선스·브랜드 흉내를 모든 출력 경로에 붙인다
c = next(x for x in motion.everything() if x['code'] == 'caret-swap')
assert 'MIT AND OFL-1.1' in motion.credit(c) and 'Apache-2.0)' not in motion.credit(c), motion.credit(c)
assert hf.license_of('caret-swap') == 'MIT AND OFL-1.1' and hf.license_of('caption-pill-karaoke') == 'Apache-2.0'
b = next(x for x in motion.everything() if x['code'] == 'instagram-follow')
assert '브랜드 흉내' in motion.credit(b) and '브랜드 흉내' in motion.where(b)
import recommend
assert next(i for i in recommend.items() if i['code'] == 'instagram-follow')['brand'] is True

# 11. build_card_anim — 이미 색인에 있던 카드라도 이번 재생성이 실패하면 실패로 센다
assert build_card_anim.unfinished(['A', 'B', 'C'], ok={'A'}) == ['B', 'C']
print('test_review_fixes: ok')

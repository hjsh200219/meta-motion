"""film.py 검사 — python3 test_film.py (Jev·네트워크 없음)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import film

REC = {"ratio": "세로", "low": 0.5, "scenes": [
    {"scene": "필독 AI 플러그인은 약국 상담을 도와줍니다.", "low": False, "picks": [{"code": "T03", "name": "쇼츠 3초 훅", "cat": "타이틀", "src": "card", "fit": 0.81, "p": 0.4}]},
    {"scene": "복약 지도 문구가 자동으로 봉투에 들어갑니다.", "low": True, "picks": [{"code": "F08", "name": "핵심 요약", "cat": "설명", "src": "card", "fit": 0.32, "p": 0.2},
                                                                         {"code": "caption-pill-karaoke", "name": "알약 가라오케 자막", "cat": "자막", "src": "hf", "fit": 0.21, "p": 0.1}]},
    {"scene": "지금 바로 문의하세요. " * 12, "low": False, "picks": [{"code": "emollick-8661a8", "name": "숫자 세기 " * 8, "cat": "데이터", "src": "pm", "fit": 0.66, "p": 0.3}]}]}

out = film.build(REC, [3.2, 5.0, 2.5], template='navy-lime', title='시험')
plan = out['plan']
assert [p['id'] for p in plan] == ['intro', 's1-t03', 's2-native', 's3-emollick-8661a8', 'outro'], plan
assert all(film.ID_RE.match(p['id']) for p in plan)
assert [p['mode'] for p in plan] == ['clip', 'clip', 'native', 'clip', 'clip']
assert plan[2]['candidates'][0]['code'] == 'F08' and plan[2]['brief'].startswith('복약')
assert abs(out['total'] - 16.2) < 1e-9 and plan[3]['start'] == 10.7
assert out['stage'] == 'rough', 'native 장면이 있으면 rough(페이지가 이름 카드로 보여 준다)'
assert out['size'] == [1080, 1920]
assert all(len(p['name']) <= 48 for p in plan) and all(len(p['desc']) <= 140 for p in plan)

# 기록 순서·모양: film/meta 첫 번째, film/script 마지막, scenes.json 에 fonts 없음(한글), palettes 네 색, theirs 1
w = out['writes']
assert (w[0]['collection'], w[0]['doc_id']) == ('film', 'meta') and (w[-1]['collection'], w[-1]['doc_id']) == ('film', 'script')
assert w[-1]['data']['code'] == 'window.CUT = kit.scenes();'
sj = json.loads(next(x for x in w if x['doc_id'] == 'scenes.json')['data']['text'])
assert 'fonts' not in sj and len(sj['palettes'][0]) == 4 and sj['theirs'] == 1 and sj['width'] == 1080 and sj['height'] == 1920
assert [s['id'] for s in sj['scenes']] == [p['id'] for p in plan] and all(s['dur'] >= 1 for s in sj['scenes'])
assert len({x['doc_id'] for x in w if x['collection'] == 'assets'}) == 4 + 1, '클립 4 + 서체 1(제목·자막 같은 파일)'
assert all(x['data']['mime'] in ('video/mp4', 'font/ttf', 'font/otf') for x in w if x['collection'] == 'assets')
css = next(x for x in w if x['doc_id'] == 'base.css')['data']['text']
assert '--ground:#08125C' in css and '"Pretendard-ExtraBold"' in css and '.clipbox' in css
assert set(out['modules']) == {'scene-intro.js', 'scene-s1-t03.js', 'scene-s3-emollick-8661a8.js', 'scene-outro.js'}
assert "kit.video('clip-s1-t03.mp4'" in out['modules']['scene-s1-t03.js']
assert out['ffmpeg'][1].startswith('ffmpeg -y -loglevel error -ss 2.5 -t 3.2 -i reel.mp4 -an')
assert all(os.path.exists(f) for f in out['fonts'])

# 가로·인트로 없음·템플릿 자동(키워드 분위기)
o2 = film.build(REC, [3, 3, 3], ratio='가로', intro=0, outro=0)
assert o2['size'] == [1920, 1080] and [p['id'] for p in o2['plan']][0] == 's1-t03' and o2['template'] in film.fonts.TEMPLATES

# 한계 — 길이 수 불일치·1초 미만·300초 초과·나쁜 템플릿
for bad in (lambda: film.build(REC, [3, 3]), lambda: film.build(REC, [0.5, 3, 3]), lambda: film.build(REC, [150, 150, 10]), lambda: film.build(REC, [3, 3, 3], template='없음')):
    try: bad(); raise AssertionError('막혀야 한다')
    except SystemExit: pass

# CLI --out
with tempfile.TemporaryDirectory() as d:
    src = os.path.join(d, 'rec.json'); open(src, 'w', encoding='utf-8').write(json.dumps(REC, ensure_ascii=False))
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): film.main([src, '--durs', '3.2,5,2.5', '--template', 'navy-lime', '-v', '--out', os.path.join(d, 'out')])
    names = sorted(os.listdir(os.path.join(d, 'out')))
    assert names == ['batch.json', 'plan.json', 'plan.md', 'scene-intro.js', 'scene-outro.js', 'scene-s1-t03.js', 'scene-s3-emollick-8661a8.js', 'split.sh'], names
    assert 'native' in open(os.path.join(d, 'out', 'plan.md'), encoding='utf-8').read()
print('ok')

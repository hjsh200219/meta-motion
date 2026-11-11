#!/usr/bin/env python3
"""Claude Motion 검토 필름 생성 — `motion.py film`.

HyperFrames 로 렌더한 영상을 장면 클립으로 잘라 Claude Motion(Artifact «Motion» 타입) 필름에 올리면 사용자가
페이지에서 긁어 보고(scrub) 시각에 댓글을 단다. 이 모듈은 그 필름의 첫 묶음(film/meta · scenes.json · base.css ·
film/script)과 장면 모듈(클립 재생), 클립 자르는 ffmpeg 명령, 장면별 계획(plan)을 표준 라이브러리만으로 만든다.
Jev 를 부르지 않는다 — 입력은 `motion.py recommend --json` 결과(이미 Jev 가 고른 것)와 장면 길이다.

장면 모드:
  clip   — 카드(요청 카드·실전 예시·레지스트리)가 맞아 HyperFrames 로 그린 장면. 필름에서는 무음 클립으로 재생.
  native — 1위 적합도가 문턱(LOW) 미만(「확신 낮음」)이라 맞는 카드가 없는 장면. Motion 안에서 kit.scene 으로 직접 그린다
           (rough-cut.md·finalize.md 규칙). 확정되면 data/motion_kit.js 로 HyperFrames 하위 컴포지션에 옮겨 최종 MP4 에 넣는다.

Motion 타입 규약(2026-10-18 설명서 실측): id `[a-z][a-z0-9-]{0,31}` · name 48자 이하 · dur 1초 이상 · 합계 300초 이하 · 장면 24개 이하 ·
한글 필름은 fonts 를 비우고 서체 파일을 자산으로 올린다 · 클립은 무음(내레이션은 안 들린다) · 자산 15MB/파일, 96개 이하.
"""
import json, shlex, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fonts  # noqa: E402  색·서체 템플릿(TEMPLATES·CATALOG·TONE_TEMPLATE·judge_tone)

ID_RE = re.compile(r'^[a-z][a-z0-9-]{0,31}$')
LIMITS = {'name': 48, 'min_dur': 1.0, 'total': 300.0, 'scenes': 24, 'assets': 96}
SIZE = {'세로': (1080, 1920), '가로': (1920, 1080), '정사각': (1080, 1080)}
FPS = 30
SCRIPT = 'window.CUT = kit.scenes();'


def slug(s, n=20):
    """한글·공백을 뺀 소문자 id 조각 — 비면 빈 문자열."""
    s = re.sub(r'[^a-z0-9]+', '-', str(s).lower()).strip('-')
    return s[:n].rstrip('-')


def scene_id(i, code, used):
    base = f's{i}-{slug(code) or "x"}'[:32]
    sid, k = base, 2
    while sid in used: sid = f'{base[:29]}-{k}'; k += 1
    if not ID_RE.match(sid): raise SystemExit(f'id 규약 위반: {sid}')
    used.add(sid); return sid


def clip_module(sid, name):
    """무음 클립 하나를 장면 전체에 재생하는 kit.scene 모듈(Motion film-api kit.video)."""
    return (f"kit.scene('{sid}', {{\n"
            f"  init(kit) {{\n    kit.stage.append(kit.h('<div class=\"ground\"></div>'));\n"
            f"    kit.stage.append(kit.video('{name}', {{ start: 0, class: 'clipbox' }}));\n  }},\n"
            f"  render(t) {{}},\n}});")


def base_css(pal, title=None, caption=None):
    """템플릿 색을 Motion 의 네 변수로: ground=bg · main=band · second=text · accent=accent.
    title·caption = (서체 파일 stem, 굵기) — 제목(.line)과 자막(.sub·기본 글자)에 따로 건다. 한 목록으로 합치면 자막도 제목용 장식 서체를 먼저 집는다."""
    face = lambda f: f'"{f[0]}", ' if f else ''
    tw, cw = (title or (None, 800))[1], (caption or (None, 400))[1]
    return (f"#stage {{ --ground:{pal['bg']}; --main:{pal['band'] or pal['bg']}; --second:{pal['text']}; --accent:{pal['accent']}; "
            f"color:var(--second); font-family:{face(caption)}var(--sans, system-ui, sans-serif) }}\n"
            ".ground { position:absolute; inset:0; background:var(--ground) }\n"
            ".clipbox { position:absolute; inset:0; width:100%; height:100%; object-fit:contain }\n"
            ".words { position:absolute; margin:0; display:flex; flex-direction:column; gap:24px } .words > * { margin:0 }\n"
            f".line {{ font-family:{face(title)}var(--display, var(--sans, system-ui, sans-serif)); font-size:84px; line-height:1.15; font-weight:{tw}; word-break:keep-all }} "
            f".sub {{ font-family:{face(caption)}var(--sans, system-ui, sans-serif); font-size:36px; font-weight:{cw} }}")


def build(rec, durs, template=None, ratio='세로', title='검토 필름', intro=2.5, outro=3.0, source='reel.mp4', low=None):
    """recommend --json 결과 + 장면 길이 → 필름 기록·장면 모듈·계획. 순수 함수(파일을 쓰지 않는다)."""
    scenes_in = rec.get('scenes', [])
    low = rec.get('low', 0.5) if low is None else low
    if len(durs) != len(scenes_in):
        raise SystemExit(f'--durs 개수({len(durs)})가 추천 장면 수({len(scenes_in)})와 다르다')
    text = '\n\n'.join(s['scene'] for s in scenes_in)
    tid = template or fonts.TONE_TEMPLATE[fonts.judge_tone(text)[0]]
    if tid not in fonts.TEMPLATES: raise SystemExit(f'알 수 없는 템플릿: {tid} (python3 fonts.py list)')
    pal = fonts.TEMPLATES[tid]
    w, h = SIZE.get(ratio, SIZE['세로'])
    used, plan, t0 = set(), [], 0.0

    def add(sid, name, dur, desc, mode, **more):
        nonlocal t0
        if len(name) > LIMITS['name']: name = name[:LIMITS['name'] - 1] + '…'
        if dur < LIMITS['min_dur']: raise SystemExit(f'장면 {sid} 길이 {dur}초 — Motion 은 1초 이상')
        plan.append({'id': sid, 'name': name, 'dur': round(dur, 3), 'start': round(t0, 3), 'desc': desc, 'mode': mode, 'clip': f'clip-{sid}.mp4' if mode == 'clip' else None, **more})
        t0 += dur

    if intro: add('intro', '인트로', intro, '로고·제목으로 연다(규칙 0 — 인트로 카드).', 'clip')
    for i, (s, d) in enumerate(zip(scenes_in, durs), 1):
        picks = s.get('picks') or []
        top = picks[0] if picks else None
        is_low = s.get('low', not top or top['fit'] < low)
        desc = re.sub(r'\s+', ' ', s['scene']).strip()
        desc = desc if len(desc) <= 140 else desc[:139] + '…'
        if top and not is_low:
            add(scene_id(i, top['code'], used), top['name'], d, desc, 'clip', card=top['code'], fit=top['fit'], src=top['src'])
        else:
            add(scene_id(i, 'native', used), f'장면 {i}', d, desc, 'native', card=None, fit=top['fit'] if top else None,
                candidates=[{'code': p['code'], 'name': p['name'], 'fit': p['fit']} for p in picks], brief=s['scene'])
    if outro: add('outro', '아웃트로', outro, '로고를 다시 보여 주고 한 줄로 닫는다(규칙 0 — 아웃트로 카드).', 'clip')

    total = sum(p['dur'] for p in plan)
    if total > LIMITS['total']: raise SystemExit(f'합계 {total:.1f}초 — Motion 은 300초 이하')
    if len(plan) > LIMITS['scenes']: raise SystemExit(f'장면 {len(plan)}개 — Motion 은 24개 이하')
    clips = [p for p in plan if p['mode'] == 'clip']
    if len(clips) > LIMITS['assets']: raise SystemExit('자산 96개 초과')
    stage = 'final' if all(p['mode'] == 'clip' for p in plan) else 'rough'
    scenes_json = {'v': 1, 'stage': stage, 'look': f"{pal['name']} — HyperFrames 렌더 클립 검토 필름(템플릿 {tid})",
                   'palettes': [[pal['bg'], pal['band'] or pal['bg'], pal['text'], pal['accent']]], 'theirs': 1,
                   'width': w, 'height': h, 'fps': FPS, 'background': pal['bg'],
                   'scenes': [{'id': p['id'], 'name': p['name'], 'dur': p['dur'], 'desc': p['desc']} for p in plan]}
    # 한글 필름: fonts 는 비운다(설명서) — 서체는 파일 자산. 제목·자막 서체 파일(템플릿)을 올리면 stem 으로 등록된다
    tf, cf = fonts.CATALOG[pal['font']], fonts.CATALOG[pal['caption_font']]
    font_files = sorted({tf['file'], cf['file']})
    title_face, caption_face = (Path(tf['file']).stem, tf['weight']), (Path(cf['file']).stem, cf['weight'])
    writes = [{'op': 'set', 'collection': 'film', 'doc_id': 'meta', 'data': {'v': 1, 'title': title, 'updatedAt': '<now ISO8601>'}}]
    writes += [{'op': 'set', 'collection': 'assets', 'doc_id': p['clip'], 'data': {'ref': '<upload ref>', 'mime': 'video/mp4', 'w': w, 'h': h}} for p in clips]
    writes += [{'op': 'set', 'collection': 'assets', 'doc_id': f, 'data': {'ref': '<upload ref>', 'mime': 'font/otf' if f.endswith('.otf') else 'font/ttf'}} for f in font_files]
    writes += [{'op': 'set', 'collection': 'modules', 'doc_id': 'scenes.json', 'data': {'kind': 'json', 'text': json.dumps(scenes_json, ensure_ascii=False)}},
               {'op': 'set', 'collection': 'modules', 'doc_id': 'base.css', 'data': {'kind': 'css', 'text': base_css(pal, title_face, caption_face)}},
               {'op': 'set', 'collection': 'film', 'doc_id': 'script', 'data': {'code': SCRIPT}}]
    ffmpeg = [f'ffmpeg -y -loglevel error -ss {p["start"]} -t {p["dur"]} -i {shlex.quote(source)} -an -c:v libx264 -crf 23 -pix_fmt yuv420p {shlex.quote(p["clip"])}' for p in clips]
    modules = {f"scene-{p['id']}.js": clip_module(p['id'], p['clip']) for p in clips}
    return {'template': tid, 'ratio': ratio, 'size': [w, h], 'total': round(total, 3), 'stage': stage, 'plan': plan, 'writes': writes,
            'modules': modules, 'ffmpeg': ffmpeg, 'fonts': [os.path.join(fonts.FONT_DIR, f) for f in font_files], 'low': low}


def plan_md(out):
    L = [f"# 검토 필름 계획 — 템플릿 {out['template']} · {out['ratio']} {out['size'][0]}x{out['size'][1]} · 합계 {out['total']}초 · stage {out['stage']}", '']
    for p in out['plan']:
        if p['mode'] == 'clip':
            L.append(f"- {p['id']}  {p['start']}s +{p['dur']}s  클립  {p['name']}" + (f"  [{p['card']} 적합도 {p['fit']}]" if p.get('card') else ''))
        else:
            cands = ' · '.join(f"{c['code']}({c['fit']})" for c in p.get('candidates', [])) or '없음'
            L.append(f"- {p['id']}  {p['start']}s +{p['dur']}s  **native — 맞는 카드 없음(1위 적합도 {p['fit']} < {out['low']})** · 후보 {cands}")
            L.append(f"  대본: {p['brief'][:200]}")
    L += ['', '순서: ① ffmpeg 로 클립 자르기 → ② 클립·서체를 자산으로 올리고 writes 의 <upload ref> 를 채워 batch → ③ 장면 모듈을 하나씩 set(clip 은 modules 파일 그대로, native 는 Motion 규칙으로 직접 작성) → ④ 사용자가 페이지에서 긁어 보고 댓글 → ArtifactComments read → 시각을 start 로 장면에 대응']
    return '\n'.join(L)


def main(args):
    if not args or args[0] in ('-h', '--help') and len(args) == 1:
        print('사용법: python3 motion.py film <recommend.json|-> --durs 3.2,5.1,… [--template <id>] [-v|-h] [--title 제목] [--source reel.mp4] [--intro 2.5] [--outro 3] [--out <폴더>]\n'
              '  recommend.json = python3 motion.py recommend 대본.txt --json 결과 · --durs 는 그 장면 순서대로 초(내레이션 길이) · --out 에 batch.json·plan.json·plan.md·scene-*.js 를 쓴다(없으면 JSON 을 stdout)')
        return
    opt = {'durs': '', 'template': None, 'title': '검토 필름', 'source': 'reel.mp4', 'intro': '2.5', 'outro': '3', 'out': None, 'ratio': None}
    rest, it = [], iter(args)
    for a in it:
        if a == '-v': opt['ratio'] = '세로'
        elif a == '-h': opt['ratio'] = '가로'
        elif a.startswith('--'): opt[a[2:]] = next(it, '')
        else: rest.append(a)
    src = rest[0] if rest else '-'
    rec = json.loads(sys.stdin.read() if src == '-' else Path(src).read_text(encoding='utf-8'))
    durs = [float(x) for x in opt['durs'].split(',') if x.strip()] if opt['durs'] else []
    out = build(rec, durs, opt['template'], opt['ratio'] or rec.get('ratio', '세로'), opt['title'],
                float(opt['intro'] or 0), float(opt['outro'] or 0), opt['source'])
    if not opt['out']:
        print(json.dumps(out, ensure_ascii=False, indent=1)); return
    d = Path(opt['out']); d.mkdir(parents=True, exist_ok=True)
    (d / 'batch.json').write_text(json.dumps(out['writes'], ensure_ascii=False, indent=1), encoding='utf-8')
    (d / 'plan.json').write_text(json.dumps({k: v for k, v in out.items() if k not in ('writes', 'modules')}, ensure_ascii=False, indent=1), encoding='utf-8')
    (d / 'plan.md').write_text(plan_md(out), encoding='utf-8')
    (d / 'split.sh').write_text('#!/bin/sh\nset -e\n' + '\n'.join(out['ffmpeg']) + '\n', encoding='utf-8')
    for name, text in out['modules'].items(): (d / name).write_text(text, encoding='utf-8')
    print(plan_md(out)); print(f"\n쓴 곳: {d}  (batch.json · plan.json · split.sh · {len(out['modules'])}개 scene-*.js · 서체 {len(out['fonts'])}개는 plan.json fonts)")


if __name__ == '__main__':
    main(sys.argv[1:])

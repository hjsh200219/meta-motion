#!/usr/bin/env python3
"""preview.html 을 사내 KB(kb.pilldoc.co.kr/motion/)용 페이지로 내보낸다 — preview.html 이 정본, 내보낸 파일은 고치지 않는다.
KB 에는 외부 영상을 막는 CSP 가 없어 원본 영상·그림을 바로 쓴다(window.MOTION_MEDIA='origin'). 접근은 KB 로그인(kb 역할)이 막는다.
실행: python3 export_kb.py <PillDocKb>/site/motion   → index.html + motion.json·prompt_motion.json·prompt_motion_ko.json·hf_registry.json·hf_registry_ko.json
                                                     + anim_skills.json(+ anim_herk_*.json — --base-only 면 뺌) + anim/(요청 카드 샘플) + hf_thumb/(레지스트리 렌더 그림) + as_thumb/(애니메이션 스킬 그림)"""
import json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEAD = """<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<!-- 생성 파일 — 정본은 meta-motion repo skills/meta-motion/preview.html, export_kb.py 로 다시 만든다 -->
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<link rel="icon" href="/static/icon.png">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<script>window.MOTION_MEDIA = 'origin'</script>
"""
# 만들 때만 쓰는 키(재료 해시·repo 커밋·카드 재료인 변수·싱크 지점)를 빼고 내보내는 파일과 그 꼴.
# KB PR 의 AI 리뷰는 diff 50만 자 상한이 있다(2026-10-17 #284 초과) — 한 줄로 줄여 파일 하나가 한 PR 에 들어가게 한다.
# prompt_motion_ko.json 은 KB 에 이미 있는 그대로 둔다(해시를 빼면 233줄이 바뀌어 diff 16만 자가 더 붙는다).
KO = {'hf_registry_ko.json': None, 'hf_registry.json': None, 'anim_skills.json': None, 'anim_herk_paper.json': None, 'anim_herk_glow.json': None}
BUILD_KEYS = {'src_sha', 'cat_src', 'cat_p', 'hold_checked', 'commit', 'variables', 'sync'}



def dump_lines(d):
    """herk 자료 JSON — 카드 한 장을 한 줄로(값은 같다). 한 줄짜리 파일은 카드 하나만 고쳐도 diff 가 파일 전체 두 배가 되어
    KB AI 리뷰 상한(50만 자, 지운 줄+새 줄)을 넘고 리뷰가 매번 전 카드를 다시 읽었다(PillDocKb #541)."""
    j = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':'))
    rest = {k: v for k, v in d.items() if k != 'items'}
    head = j(rest)[:-1] + (',' if rest else '')
    rows = ',\n'.join(f'{j(k)}:{j(v)}' for k, v in d.get('items', {}).items())
    return head + '"items":{\n' + rows + '\n}}\n'

def strip_build(v):
    if isinstance(v, dict): return {k: strip_build(x) for k, x in v.items() if k not in BUILD_KEYS}
    if isinstance(v, list): return [strip_build(x) for x in v]
    return v


DATA = ('motion.json', 'prompt_motion.json', 'prompt_motion_ko.json', 'hf_registry.json', 'hf_registry_ko.json', 'anim_skills.json', 'anim_herk_paper.json', 'anim_herk_glow.json')
OPTIONAL = {'anim_herk_paper.json', 'anim_herk_glow.json'}  # herk 스타일 카드(build_herk.py) — 없으면 건너뛴다
BACK = '<a href="/" style="color:inherit;opacity:.7;font-size:13px;text-decoration:none">← PillDocKb</a>\n    <h1>'


def build(out: Path, back: bool = True, base_only: bool = False) -> None:  # base_only: herk 스타일 카드(OPTIONAL)와 그 그림을 빼고 — KB PR 을 나눠 올릴 때  # back=False: 로컬 보기(serve.py) — KB 첫 화면으로 가는 링크가 없다
    src = (HERE / 'preview.html').read_text(encoding='utf-8')
    assert src.startswith('<meta charset="utf-8">\n') and src.count('<h1>') == 1, 'preview.html 머리 모양이 바뀜 — 이 스크립트를 맞출 것'
    out.mkdir(parents=True, exist_ok=True)
    body = src.removeprefix('<meta charset="utf-8">\n')
    if back: body = body.replace('<h1>', BACK, 1)
    head = HEAD if back else '\n'.join(l for l in HEAD.split('\n') if '/static/' not in l)  # 로컬엔 KB 아이콘이 없다
    (out / 'index.html').write_text(head + body + '\n</html>\n', encoding='utf-8')
    for f in DATA:
        if f in OPTIONAL and (base_only or not (HERE / 'data' / f).exists()): continue
        if f in KO:  # 만들 때만 쓰는 키(재료 해시·repo 커밋)는 빼고 내보낸다 — 16진 해시가 KB pre-commit 시크릿 검사에 걸린다(2026-10-17)
            data = json.loads((HERE / 'data' / f).read_text(encoding='utf-8'))
            for k in data.get('kits', {}).values() if f.startswith('anim_') else ():  # 화면의 원본 링크용 짧은 커밋(7자는 시크릿 검사에 안 걸린다)
                k['ref'] = k['commit'][:7]
            text = dump_lines(strip_build(data)) if f.startswith('anim_herk_') else json.dumps(strip_build(data), ensure_ascii=False, indent=KO[f], separators=(',', ': ') if KO[f] else (',', ':'))
            (out / f).write_text(text, encoding='utf-8')
        else:
            shutil.copyfile(HERE / 'data' / f, out / f)
    shutil.rmtree(out / 'anim', ignore_errors=True)
    shutil.copytree(HERE / 'data' / 'anim', out / 'anim', ignore=shutil.ignore_patterns('index.json'))
    shutil.rmtree(out / 'hf_thumb', ignore_errors=True)
    shutil.copytree(HERE / 'data' / 'hf_thumb', out / 'hf_thumb')
    shutil.rmtree(out / 'as_thumb', ignore_errors=True)
    shutil.copytree(HERE / 'data' / 'as_thumb', out / 'as_thumb', ignore=shutil.ignore_patterns('hk-*') if base_only else None)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--base-only']
    if len(args) != 1 or args[0].startswith('-'): sys.exit(__doc__)  # --help 를 폴더 이름으로 받지 않는다
    build(Path(args[0]), base_only='--base-only' in sys.argv)
    print(f'내보냄 → {args[0]}', file=sys.stderr)

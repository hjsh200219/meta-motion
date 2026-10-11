#!/usr/bin/env python3
"""영상 스크립트를 장면별로 나눠 어울리는 모션 카드(요청 카드 152 + 실전 예시 233)를 Jev(TypeSafe)로 추천한다.
Jev choice 는 옵션이 255개까지라 두 단계로 고른다 — ① 장면마다 분류 16개 중 고르고 ② 확률 위쪽 분류들의 카드 중 고른다.
장면 나누기·후보 모으기·순위 매기기는 코드가, 고르기만 Jev 가 한다. 스크립트 글은 외부 API(api.typesafe.ai)로 나간다.
필요: workspace shared/jev.py(또는 같은 폴더의 jev.py)와 JEV_API_KEY(환경변수 또는 workspace .env).
실행: python3 motion.py recommend <스크립트.txt|-> [--top 3]"""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(Path.home() / 'workspace' / 'shared')]
MAX_OPTIONS = 255  # Jev choice 옵션 상한
CAT_MASS = 0.8     # 분류 확률을 위에서부터 이만큼 모을 때까지(최대 3개) 후보로 넣는다
LOW = 0.3          # 1순위 확률이 이보다 낮으면 «확신 낮음» — 카드 목록에 딱 맞는 게 없다는 신호


def items():
    """요청 카드와 실전 예시(한국어 카드)를 한 목록으로 — preview.html 처럼 출처를 나누지 않는다."""
    cards = json.loads((HERE / 'data/motion.json').read_text(encoding='utf-8'))
    out = [{'code': c['code'], 'name': c['name'], 'plain': c['plain'], 'when': c['when'], 'cat': c['cat'], 'how': f"show {c['code']}"} for c in cards]
    ko = HERE / 'data/prompt_motion_ko.json'
    if ko.exists():
        for k, c in json.loads(ko.read_text(encoding='utf-8')).items():
            out.append({'code': k, 'name': c['name'], 'plain': c['plain'], 'when': c['when'], 'cat': c['cat'], 'how': f'example {k}'})
    return out


def scenes(text):
    """빈 줄로 나눈 문단이 장면. 빈 줄이 없으면 줄마다 한 장면. 장면 머리표(#·S1·장면 1·1.)는 떼지 않고 그대로 둔다."""
    parts = [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    if len(parts) == 1: parts = [l.strip() for l in parts[0].splitlines() if l.strip()]
    return parts


def describe(it):
    return f"{it['name']} — {it['plain']} 쓸 때: {it['when']}"[:300]


def recommend_scene(sc, i, pool, cats, top):
    import jev
    # 스크립트 전체를 주면 뒤 장면 내용(예: 위치 안내)에 끌려 첫 인사에 지도 카드를 고른다(2026-10-12 실측) — 위치와 앞뒤 장면만 준다
    state = {'scene': sc[i], 'position': f'전체 {len(sc)}장면 중 {i + 1}번째' + (' (첫 장면)' if i == 0 else ' (마지막 장면)' if i == len(sc) - 1 else ''),
             'previous_scene': sc[i - 1] if i else '', 'next_scene': sc[i + 1] if i + 1 < len(sc) else ''}
    by_cat = {k: [it for it in pool if it['cat'] == k] for k in cats}
    cat_opts = {k: ' · '.join(it['name'] for it in v[:6]) for k, v in by_cat.items()}
    a = jev.ask(state, {'cat': jev.choice('scene 에 화면 그래픽(모션)을 넣는다면 어떤 종류가 가장 알맞은가. position·앞뒤 장면은 흐름을 보려는 참고다.', cat_opts)})
    probs = sorted((a.get('cat') or {}).get('probabilities', {}).items(), key=lambda x: -x[1])
    picked, mass = [], 0.0
    for k, p in probs:
        if k not in by_cat or len(picked) == 3: continue
        picked.append(k); mass += p
        if mass >= CAT_MASS: break
    cand = [it for k in picked for it in by_cat[k]]
    assert 2 <= len(cand) <= MAX_OPTIONS, f'후보 {len(cand)}개 — Jev choice 범위(2~{MAX_OPTIONS}) 밖'
    a = jev.ask(state, {'card': jev.choice('scene 의 내용을 화면으로 보여 주기에 가장 알맞은 모션은 무엇인가.', {it['code']: describe(it) for it in cand})})
    ranked = sorted((a.get('card') or {}).get('probabilities', {}).items(), key=lambda x: -x[1])[:top]
    code = {it['code']: it for it in cand}
    return {'scene': sc[i], 'cats': picked, 'picks': [{**code[k], 'p': round(p, 3)} for k, p in ranked if k in code]}


def run(text, top=3, workers=4):
    try:
        import jev  # noqa: F401
    except ImportError:
        sys.exit('Jev 클라이언트(jev.py)를 찾지 못했습니다 — workspace shared/jev.py 를 이 폴더에 복사하거나 workspace 에서 실행하세요')
    pool, sc = items(), scenes(text)
    if not sc: sys.exit('스크립트가 비어 있습니다')
    cats = list(dict.fromkeys(it['cat'] for it in pool))
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda i: recommend_scene(sc, i, pool, cats, top), range(len(sc))))


def main(args):
    top = int(args[args.index('--top') + 1]) if '--top' in args else 3
    rest = [a for i, a in enumerate(args) if a != '--top' and (i == 0 or args[i - 1] != '--top')]
    src = rest[0] if rest else '-'
    text = sys.stdin.read() if src == '-' else Path(src).read_text(encoding='utf-8')
    for i, r in enumerate(run(text, top), 1):
        low = ' · 확신 낮음 — 직접 고르거나 search 로 찾기' if not r['picks'] or r['picks'][0]['p'] < LOW else ''
        print(f"\n## 장면 {i}: {r['scene'][:80]}{'…' if len(r['scene']) > 80 else ''}\n   (분류 후보: {', '.join(r['cats'])}{low})")
        for it in r['picks']:
            print(f"   {it['p']:.2f}  {it['code']}\t{it['name']}\t→ python3 motion.py {it['how']}")


if __name__ == '__main__':
    main(sys.argv[1:])

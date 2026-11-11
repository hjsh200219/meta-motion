#!/usr/bin/env python3
"""표현 기법 참고서 cokacmotion(aimotion, MIT © 2026 kstost) 찾기·읽기 — 기법 하나당 데모 하나(data/cokac.json, build_cokac.py).
카드(요청 카드·실전 예시·레지스트리)가 「무엇을 보여 줄지」라면 이건 「그 효과를 어떻게 짜는지」다. 맞는 카드가 없는 장면, 카드 사양의
볼거리를 직접 구현할 때(잉크·수채·필름·유리·유체·입자·글자 깨짐 등) 원리와 소스를 읽고 지금 영상의 소재로 다시 짠다.
⛔ 기술만 가져간다: 데모의 소재·장면·구도·문구·색·9:16 틀은 옮기지 않는다(데모를 본 사람이 영상에서 그 데모를 알아보면 실패).
실행: python3 motion.py technique [단어…] [--group 분류]      찾기(여러 단어 AND · 인자 없으면 분류별 개수)
      python3 motion.py technique <번호|id>                   노트 전문 + 소스·그림 경로(처음 한 번 캐시 클론 ~/.cache/meta-motion/cokacmotion)"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data' / 'cokac.json'


def load():
    return json.loads(DATA.read_text(encoding='utf-8'))


def _hay(d):
    return ' '.join([d['id'], d['title'], d['tech'], d['group'], d['scene'], *d['points'], *d['libraries']]).lower()


def find(idx, words, group=''):
    qs = [w.lower() for w in words]
    return [d for d in idx['items'] if (not group or group in d['group']) and all(q in _hay(d) for q in qs)]


def pick(idx, key):
    return next((d for d in idx['items'] if d['id'] == key or (key.isdigit() and d['number'] == int(key))), None)


def show(idx, d, cache=None):
    if cache is None:
        import build_cokac
        build_cokac.sync_repo(idx['commit'])
        cache = build_cokac.CACHE
    demo = Path(cache) / 'skills' / 'aimotion' / 'demos' / d['id']
    print(f"⛔ {idx['rule']}\n")
    notes = next((demo / n for n in ('NOTES.md', 'notes.md') if (demo / n).exists()), None)
    print(notes.read_text(encoding='utf-8') if notes else f"# {d['number']:02d} · {d['title']} — {d['tech']}\n(노트 없음)")
    print('\n소스: ' + ' · '.join(str(p) for p in sorted(demo.glob('*')) if p.suffix in ('.js', '.html', '.css')))
    pics = [str(p) for p in sorted((demo / 'out').glob('*.jpg'))] if (demo / 'out').exists() else []
    if pics: print('그림: ' + ' · '.join(pics))
    if d['libraries']: print('라이브러리: ' + ', '.join(d['libraries']) + ' — HyperFrames 런타임은 GSAP 본체만 부른다. 없는 라이브러리는 원리만 가져와 Canvas 2D·SVG·WebGL 로 직접 쓴다')
    for c in d['cautions']: print('주의: ' + c)
    print(f"출처: {idx['source']}/demos/{d['id']} ({idx['license']}, 커밋 {idx['commit'][:7]}) — 코드 덩어리를 거의 그대로 옮기면 저작권 고지를 함께 둔다")


def main(args):
    idx = load()
    group = args[args.index('--group') + 1] if '--group' in args else ''
    words = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] != '--group')]
    if len(words) == 1 and pick(idx, words[0]):
        return show(idx, pick(idx, words[0]))
    if not words and not group:
        from collections import Counter
        for g, n in Counter(d['group'] for d in idx['items']).items(): print(f'{g}\t{n}개')
        print(f"\n({len(idx['items'])}개 · {idx['license']} · 찾기: technique <단어…> · 보기: technique <번호>)", file=sys.stderr)
        return
    hit = find(idx, words, group)
    for d in hit:
        lib = f"\t[{', '.join(d['libraries'])}]" if d['libraries'] else ''
        print(f"{d['number']:>3}\t{d['id']}\t{d['title']}\t{d['group']}\t{d['tech']}{lib}")
    if not hit: print('찾은 기법 없음 — 분류: ' + ' · '.join(idx['groups']))
    print(f"\n({len(hit)}/{len(idx['items'])}개 · 보기: python3 motion.py technique <번호> · ⛔ 기술만 가져간다)", file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1:])

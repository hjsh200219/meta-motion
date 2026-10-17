#!/usr/bin/env python3
"""recommend 품질 재기 — 실제 대본 장면에 recommend 를 돌리고 edb-p(sonnet) 심판이 1~5점을 매겨 지표를 낸다. 심판 점수는 정답이 아니다.
대본은 장면 목록 JSON([{"slug", "scenes": [장면 글, …]}, …])이고, 공개된 글만 넣는다 — recommend 가 장면 글을 api.typesafe.ai 로 보낸다.
게시된 인스타 릴스 카드(SHC/shconsulting scripts/instagram/cards, 게시 목록 published-instagram.json)에서 만드는 명령이 `set` 이다.

  python3 eval_recommend.py set <instagram 폴더> set.json [--n 10] [--offset 0] [--skip 이전set.json]
  python3 eval_recommend.py run set.json run.json [-h]
  python3 eval_recommend.py judge set.json judge.json run.json [run2.json …]   (이미 매긴 장면·카드는 다시 묻지 않는다)
  python3 eval_recommend.py report judge.json run.json [run2.json …]

2026-10-17 기록(recommend.py 머리의 EVAL): 평가 64장면 · 검증 75장면(겹치지 않는 대본 10편) — 검증에서 예전 두 단계 1위 평균 2.84 → 지금 4.00."""
import glob, json, os, random, re, statistics as st, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import recommend
from recommend import fits_ratio, items

LEAN = ['--setting-sources', '', '--system-prompt', '요청에 그대로 답한다. 한국어로 답한다.']
GUIDE = """너는 {ratio} 정보 영상의 모션 그래픽 감독이다.
각 장면(scene)마다 후보 모션 카드들이 주어진다. 카드마다 «이 장면을 이 모션으로 그리면 얼마나 알맞은가»를 1~5점으로 매겨라.
5 = 장면 내용(숫자·목록·인용·제목 등)을 그대로 살려 가장 잘 보여 준다
4 = 잘 맞는다, 조금 손보면 된다
3 = 쓸 수는 있지만 장면의 핵심을 살리지 못하거나 어색하다
2 = 장면과 거리가 멀다(장면에 없는 요소를 억지로 끌어와야 한다)
1 = 맞지 않는다(전혀 다른 용도·영상과 다른 비율로 크기가 고정돼 못 씀 등)
앞뒤 장면은 흐름 참고용이다. 점수는 카드끼리 상대 비교가 아니라 절대 기준이다.
출력은 ```json 블록 하나: [{"sid": "...", "scores": {"<코드>": 점수, ...}}, ...] — 모든 장면·모든 코드에 점수를 준다."""


def scene_text(c):
    """릴스 카드 한 장 → 장면 글(shconsulting motion/pick.mjs 의 sceneText 와 같은 순서)."""
    parts = [c.get('marker'), c.get('headline'), c.get('hook'), c.get('title'), c.get('body'),
             c.get('value') and f"{c['value']}{c.get('unit', '')}", c.get('caption'), *(c.get('items') or []), c.get('quote')]
    return re.sub(r'\s+', ' ', re.sub(r'<br\s*/?>', ' ', ' / '.join(str(p) for p in parts if p)))


def make_set(ig, out, n=10, offset=0, skip=None):
    ig = Path(ig)
    done = {p['slug'] for p in json.loads((ig / 'published-instagram.json').read_text(encoding='utf-8'))}
    used = {s['slug'] for s in json.loads(Path(skip).read_text(encoding='utf-8'))} if skip else set()
    files = [f for f in sorted(glob.glob(str(ig / 'cards' / '*.json'))) if Path(f).stem in done and Path(f).stem not in used]
    pick = files[offset::max(1, len(files) // n)][:n]
    data = [{'slug': Path(f).stem, 'scenes': [scene_text(c) for c in json.loads(Path(f).read_text(encoding='utf-8'))['cards']]} for f in pick]
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{len(data)}편 {sum(len(s['scenes']) for s in data)}장면 → {out}")


def run(set_path, out, ratio='세로', workers=6):
    pool = [it for it in items() if fits_ratio(it, ratio)]
    jobs = [(s['slug'], s['scenes'], i) for s in json.loads(Path(set_path).read_text(encoding='utf-8')) for i in range(len(s['scenes']))]

    def one(job):
        slug, sc, i = job
        t = time.time()
        for _ in range(3):
            try:
                r = recommend.recommend_scene(sc, i, pool, 3, ratio); break
            except Exception as e:  # noqa: BLE001 — 기록하고 다음 장면으로
                r = {'error': str(e)[:200]}; time.sleep(2)
        return {'slug': slug, 'i': i, 'picks': [{k: p[k] for k in ('code', 'p', 'fit')} for p in r.get('picks', [])],
                **({'error': r['error']} if 'error' in r else {}), 'sec': round(time.time() - t, 2)}
    with ThreadPoolExecutor(workers) as ex: rows = list(ex.map(one, jobs))
    Path(out).write_text(json.dumps({'ratio': ratio, 'pool': len(pool), 'rows': rows}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{len(rows)}장면 · 오류 {sum('error' in r for r in rows)} → {out}")


def judge(set_path, out, runs):
    es = {s['slug']: s for s in json.loads(Path(set_path).read_text(encoding='utf-8'))}
    code = {it['code']: it for it in items()}
    done = json.loads(Path(out).read_text(encoding='utf-8')) if Path(out).exists() else {}
    data = [json.loads(Path(r).read_text(encoding='utf-8')) for r in runs]
    rows = [row for d in data for row in d['rows']]
    ratio = data[0].get('ratio', '세로')
    assert all(d.get('ratio', '세로') == ratio for d in data), '비율이 다른 실행은 따로 채점한다'
    guide = GUIDE.replace('{ratio}', '세로 숏폼(인스타 릴스 4:5·9:16)' if ratio == '세로' else '가로(16:9)')
    todo = []
    for slug, s in es.items():
        for i, sc in enumerate(s['scenes']):
            sid = f'{slug}#{i}'
            cs = sorted({p['code'] for row in rows if row['slug'] == slug and row['i'] == i for p in row['picks']} - set(done.get(sid, {})))
            if not cs: continue
            random.Random(sid).shuffle(cs)  # 어느 변형·몇 위인지 심판이 모르게
            info = lambda it: {**{k: it[k] for k in ('code', 'name', 'plain', 'when', 'cat')}, **({} if fits_ratio(it, ratio) else {'size': '영상과 다른 비율로 크기 고정'})}
            todo.append({'sid': sid, 'scene': sc, 'previous_scene': s['scenes'][i - 1] if i else '',
                         'next_scene': s['scenes'][i + 1] if i + 1 < len(s['scenes']) else '', 'candidates': [info(code[c]) for c in cs]})

    def one(batch):
        task = guide + '\n<data>\n' + json.dumps(batch, ensure_ascii=False) + '\n</data>'
        for _ in range(2):
            r = subprocess.run([str(Path.home() / '.local/bin/edb-p'), '--model', 'sonnet', '--effort', 'medium', '--tools', '', '--strict-mcp-config',
                                '--permission-mode', 'default'] + LEAN, input=task, capture_output=True, text=True, timeout=900,
                               env=dict(os.environ, CLAUDE_CODE_DISABLE_CLAUDE_MDS='1'))
            if r.returncode == 3: sys.exit('edb 주간 상한 — 리셋 뒤 다시')
            m = re.search(r'```json\s*(\[.*?\])\s*```', r.stdout, re.S)
            if m: return json.loads(m.group(1))
        print('채점 실패:', r.stdout[-200:], r.stderr[-200:]); return []
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, [todo[k:k + 4] for k in range(0, len(todo), 4)]):
            for x in res: done.setdefault(x['sid'], {}).update({k: int(v) for k, v in x['scores'].items()})
    Path(out).write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'채점 {len(todo)}장면 → {out}')


def auc(pairs):
    pos = [s for s, g in pairs if g]; neg = [s for s, g in pairs if not g]
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / max(1, len(pos) * len(neg))


def report(judge_path, runs):
    J = json.loads(Path(judge_path).read_text(encoding='utf-8'))
    code = {it['code']: it for it in items()}
    print('실행\t장면\t초/장면\t1위 심판평균\t1위 ≥4\t위쪽3 중 ≥4\t가로고정\t확신낮음\t적합도 AUC\t확신낮음 장면 평균 / 나머지')
    for r in runs:
        rows = sorted((x for x in json.loads(Path(r).read_text(encoding='utf-8'))['rows'] if x['picks']), key=lambda x: (x['slug'], x['i']))
        sc = lambda x, c: J.get(f"{x['slug']}#{x['i']}", {}).get(c)
        rows = [x for x in rows if all(sc(x, p['code']) is not None for p in x['picks'])]
        if not rows: print(r, '채점된 장면 없음'); continue
        j1 = [sc(x, x['picks'][0]['code']) for x in rows]
        j3 = [max(sc(x, p['code']) for p in x['picks']) for x in rows]
        land = sum(not fits_ratio(code[p['code']], '세로') for x in rows for p in x['picks']) / sum(len(x['picks']) for x in rows)
        low = [x for x in rows if x['picks'][0].get('fit', 1) < recommend.LOW]
        lo = [sc(x, x['picks'][0]['code']) for x in low]; hi = [sc(x, x['picks'][0]['code']) for x in rows if x not in low]
        a = auc([(x['picks'][0]['fit'], j >= 4) for x, j in zip(rows, j1)]) if 'fit' in rows[0]['picks'][0] else float('nan')
        print(f"{Path(r).name}\t{len(rows)}\t{st.mean(x['sec'] for x in rows):.1f}\t{st.mean(j1):.2f}\t{sum(j >= 4 for j in j1) / len(j1):.0%}\t"
              f"{sum(j >= 4 for j in j3) / len(j3):.0%}\t{land:.0%}\t{len(low)}/{len(rows)}\t{a:.2f}\t"
              f"{st.mean(lo) if lo else float('nan'):.2f} / {st.mean(hi) if hi else float('nan'):.2f}")


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if a[:1] == ['set']: make_set(a[1], a[2], int(opt('--n', 10)), int(opt('--offset', 0)), opt('--skip'))
    elif a[:1] == ['run']: run(a[1], a[2], '가로' if '-h' in a else '세로')
    elif a[:1] == ['judge']: judge(a[1], a[2], a[3:])
    elif a[:1] == ['report']: report(a[1], a[2:])
    else: sys.exit(__doc__)

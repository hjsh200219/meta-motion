#!/usr/bin/env python3
"""영상 스크립트를 장면별로 나눠 어울리는 모션 카드(요청 카드 152 + 실전 예시 233 + HyperFrames 레지스트리 444)를 Jev(TypeSafe)로 추천한다.
① 화면 비율에 못 쓰는 항목을 코드가 뺀다(세로면 가로 고정 레지스트리 항목) ② 남은 후보 전체를 255개 이하 묶음으로 고르게 나눠
묶음마다 Jev choice 로 위쪽 몇 개를 뽑고 ③ 그 결승 후보 중에서 다시 골라 순서를 정한 뒤 ④ 고른 카드마다 Jev noul 로 절대 적합도를 물어 확신 표시에 쓴다.
분류(16개)를 먼저 고르던 두 단계 방식은 분류를 잘못 고르면 맞는 카드가 후보에서 통째로 빠져 버려서 뺐다(2026-10-17 실측 — 아래 EVAL).
장면 나누기·비율 거르기·순위 합치기는 코드가, 고르기·적합도는 Jev 가 한다. 스크립트 글은 외부 API(api.typesafe.ai)로 나간다.
필요: 같은 폴더의 jev.py(번들 사본)와 Jev API 키 — `python3 setup.py`(Windows 는 python)로 한 번 저장(환경변수 JEV_API_KEY·workspace .env 도 읽음).
실행: python3 motion.py recommend <스크립트.txt|-> [--top 3] [-v|-h] [--json]"""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(Path.home() / 'workspace' / 'shared')]
MAX_OPTIONS = 255  # Jev choice 옵션 상한
FINALISTS = 8      # 묶음마다 결승에 올리는 수
KB = 'https://kb.pilldoc.co.kr/motion/#'  # 사내 KB 미리보기 — #코드 로 그 카드가 골라진 채 열린다(로그인 필요)
LOW = 0.5          # 1위 적합도가 이보다 낮으면(=Jev 가 «안 맞는다» 쪽에 더 걸면) «확신 낮음» — 아래 EVAL 에서 64장면 중 10개, 심판 평균 3.60 대 나머지 4.17
# EVAL(2026-10-17) 게시된 릴스 대본 10편 64장면, 채점은 edb-p sonnet 심판(정답 아님, 1~5점 블라인드):
#   예전 두 단계(분류→카드) 1위 평균 2.64 · 1위 4점 이상 28% · 위쪽 3개 중 4점 이상 52% · 위쪽 3개의 23% 가 가로 고정
#   비율 거르기만 더해도 3.50 · 48% · 67% · 0%, 분류 관문을 빼고 전체 결승(지금 방식)으로 4.08 · 73% · 89% · 0% — 관문이 가장 큰 손실이었다.
#   Jev 호출은 장면당 2 → 5회(결승 묶음 3 + 최종 1 + 적합도 1, 장면당 약 1.4초 — 장면끼리는 병렬)
#   순서는 결승 choice 확률로 둔다 — 적합도로 다시 줄 세우면 1위 평균이 오히려 내려갔다(3.78~3.81 대 4.06~4.16).
#   예전 «확신 낮음»(1위 choice 확률 <0.3)은 품질을 못 갈랐다(심판 4점 이상과의 순위 일치도 AUC 0.45) — choice 확률은 옵션 수에 따라 작아지는 상대값이라
#   레지스트리를 합친 뒤 확신 낮음이 19% → 42% 로 늘었다. 그래서 옵션 수와 무관한 noul 적합도(AUC 0.66)로 바꿨다. 문턱은 이 64장면으로 정했다.
#   검증(겹치지 않는 대본 10편 75장면): 예전 2.84 · 33% · 75% · 17% → 지금 4.00 · 72% · 97% · 0%, 확신 낮음 9/75(심판 평균 3.22 대 나머지 4.11).
#   다시 재기: eval_recommend.py(set → run → judge → report).
FIT_Q = ('{ratio} 영상의 이 장면(`scene`)을 아래 모션으로 그리면 장면 내용을 잃지 않고 잘 보여 주는가. '
         '장면에 없는 요소(지도·가게·인물·로고 등)를 억지로 끌어와야 하면 아니다.')
PICK_Q = 'scene 의 내용을 화면으로 보여 주기에 가장 알맞은 모션은 무엇인가. position·앞뒤 장면은 흐름을 보려는 참고다.'


def items():
    """요청 카드·실전 예시·레지스트리(한국어 카드)를 한 목록으로 — motion.py·preview.html 처럼 출처를 나누지 않는다."""
    import motion
    return [{'code': c['code'], 'name': c['name'], 'plain': c['plain'], 'when': c['when'], 'cat': c['cat'], 'src': c.get('src', 'card'),
             'how': f"show {c['code']}"} for c in motion.everything()]


def fits_ratio(it, ratio):
    """레지스트리 항목은 크기가 고정이다 — 세로 영상에 가로 고정(블록 192·컴포넌트 29개), 가로 영상에 세로 고정 항목을 넣으면 화면 밖으로 넘친다.
    요청 카드·실전 예시는 비율을 요청 문장으로 정하고, 크기 미표기 컴포넌트는 조각이라 남긴다."""
    if it['src'] != 'hf' or not ratio: return True
    import hf
    d = hf.ITEMS.get(it['code'], {}).get('dimensions')
    if not d: return True
    return d['width'] <= d['height'] if ratio == '세로' else d['width'] >= d['height']


def chunks(cand, size=MAX_OPTIONS):
    """후보를 size 이하 묶음으로 고르게 나눈다 — 앞뒤로 자르면 한 묶음에 한 분류·출처만 몰리므로 번갈아 담는다."""
    k = -(-len(cand) // size)
    return [cand[i::k] for i in range(k)]


def scenes(text):
    """빈 줄로 나눈 문단이 장면. 빈 줄이 없으면 줄마다 한 장면. 장면 머리표(#·S1·장면 1·1.)는 떼지 않고 그대로 둔다."""
    parts = [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    if len(parts) == 1: parts = [l.strip() for l in parts[0].splitlines() if l.strip()]
    return parts


def describe(it):
    return f"{it['name']} — {it['plain']} 쓸 때: {it['when']}"[:300]


def recommend_scene(sc, i, pool, top, ratio='세로'):
    import jev
    # 스크립트 전체를 주면 뒤 장면 내용(예: 위치 안내)에 끌려 첫 인사에 지도 카드를 고른다(2026-10-12 실측) — 위치와 앞뒤 장면만 준다
    state = {'scene': sc[i], 'position': f'전체 {len(sc)}장면 중 {i + 1}번째' + (' (첫 장면)' if i == 0 else ' (마지막 장면)' if i == len(sc) - 1 else ''),
             'previous_scene': sc[i - 1] if i else '', 'next_scene': sc[i + 1] if i + 1 < len(sc) else ''}
    code = {it['code']: it for it in pool}
    ask = lambda opts: sorted((jev.ask(state, {'card': jev.choice(PICK_Q, {it['code']: describe(it) for it in opts})}).get('card') or {})
                              .get('probabilities', {}).items(), key=lambda x: -x[1])
    cand = pool
    if len(cand) > MAX_OPTIONS:  # 결승: 묶음마다 위쪽 FINALISTS 개
        cand = [code[k] for ch in chunks(cand) for k, _ in ask(ch)[:FINALISTS] if k in code]
    assert 2 <= len(cand) <= MAX_OPTIONS, f'후보 {len(cand)}개 — Jev choice 범위(2~{MAX_OPTIONS}) 밖'
    head = [(code[k], p) for k, p in ask(cand) if k in code][:top]
    a = jev.ask(state, {f'f{j}': jev.noul(FIT_Q.format(ratio=ratio) + f' 모션: {describe(it)}') for j, (it, _) in enumerate(head)})  # 한 요청에 noul top 개
    return {'scene': sc[i], 'picks': [{**it, 'p': round(p, 3), 'fit': round(jev.noul_of(a, f'f{j}', 0.0), 3)} for j, (it, p) in enumerate(head)]}


def run(text, top=3, ratio='세로', workers=4):
    try:
        import jev  # noqa: F401
    except ImportError:
        sys.exit('Jev 클라이언트(jev.py)를 찾지 못했습니다 — 플러그인을 다시 설치하세요(skills/meta-motion/jev.py)')
    sc = scenes(text)
    if not sc: sys.exit('스크립트가 비어 있습니다')
    pool = [it for it in items() if fits_ratio(it, ratio)]
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda i: recommend_scene(sc, i, pool, top, ratio), range(len(sc))))


def main(args):
    top = int(args[args.index('--top') + 1]) if '--top' in args else 3
    given = args[args.index('--ratio') + 1] if '--ratio' in args[:-1] else ''
    ratio = '가로' if '-h' in args or given == '가로' else '세로'  # 기본 세로 9:16(SKILL.md) — -h·--ratio 가로일 때만 가로
    rest = [a for i, a in enumerate(args) if a not in ('--top', '--ratio', '-v', '-h', '--json') and (i == 0 or args[i - 1] not in ('--top', '--ratio'))]
    src = rest[0] if rest else '-'
    text = sys.stdin.read() if src == '-' else Path(src).read_text(encoding='utf-8')
    res = run(text, top, ratio)
    if '--json' in args:
        keep = ('code', 'name', 'cat', 'src', 'fit', 'p')
        print(json.dumps({'ratio': ratio, 'low': LOW, 'scenes': [{'scene': r['scene'], 'low': not r['picks'] or r['picks'][0]['fit'] < LOW,
                                                                 'picks': [{k: it[k] for k in keep} for it in r['picks']]} for r in res]},
                         ensure_ascii=False, indent=1))
        return
    src_name = {'card': '요청 카드', 'pm': '실전 예시', 'hf': '레지스트리'}
    print(f'비율 {ratio} · 순서 = Jev 가 후보 전체에서 고른 순 · 적합도 = «이 장면을 이 모션으로 잘 보여 주나»에 Jev 가 답한 예 확률'
          f'(0~1, 후보 수와 무관) · 1위 적합도 {LOW} 미만이면 확신 낮음')
    for i, r in enumerate(res, 1):
        low = '   ⚠ 확신 낮음 — 딱 맞는 카드가 없을 수 있다: 직접 고르거나 search 로 찾기, 맞는 게 없으면 이 장면은 건너뛴다\n' \
            if not r['picks'] or r['picks'][0]['fit'] < LOW else ''
        print(f"\n## 장면 {i}: {r['scene'][:80]}{'…' if len(r['scene']) > 80 else ''}\n{low}", end='')
        for it in r['picks']:
            add = f"\n         넣기 python3 motion.py registry-add {it['code']} --dir <프로젝트>" if it['src'] == 'hf' else ''
            print(f"   적합도 {it['fit']:.2f}  {it['code']}\t{it['name']}\t[{it['cat']} · {src_name[it['src']]}]\n"
                  f"         자세히 python3 motion.py {it['how']}{' -h' if ratio == '가로' else ' -v'}\n         보기 {KB}{it['code']}{add}")


if __name__ == '__main__':
    main(sys.argv[1:])

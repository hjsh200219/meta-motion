#!/usr/bin/env python3
"""prompt_motion.json(영어 실전 예시)을 요청 카드(motion.json)와 같은 모양의 한국어 카드로 바꿔 data/prompt_motion_ko.json 에 쌓는다.
영상 길이는 ffprobe 로 재고, 변환은 edb-p(claude -p)에 몇 개씩 묶어 맡긴다. 이미 바꾼 항목(프롬프트가 같으면)은 건너뛴다.
실행: python3 build_pm_ko.py [--batch 8] [--workers 4] [--limit N]   · 필요: ffprobe, ~/.local/bin/edb-p"""
import hashlib, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

D = Path(__file__).resolve().parent / 'data'
SRC, OUT = D / 'prompt_motion.json', D / 'prompt_motion_ko.json'
CARDS = json.loads((D / 'motion.json').read_text(encoding='utf-8'))
CATS = list(dict.fromkeys(c['cat'] for c in CARDS))
KINDS = {'scene', 'overlay', 'transition', 'loop'}
COMMON = {'ratio', 'color', 'file'}
SAMPLE = [next(c for c in CARDS if c['code'] == k) for k in ('T06', 'B01')]


def sha(e):
    return hashlib.sha256(e['prompt'].encode()).hexdigest()[:16]


def duration(url):
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', url],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return round(float(out), 1)
    except Exception:
        return None


def ngrams(text, n=8):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {' '.join(w[i:i + n]) for i in range(len(w) - n + 1)}


def check(card, e):
    """요청 카드 모양·값 범위·원문 베끼기(영어 8단어 연속) 검사 — 문제 목록을 돌려준다."""
    bad = []
    for k in ('name', 'plain', 'when', 'len', 'cat', 'tpl', 'fields', 'dx'):
        if k not in card: bad.append(f'{k} 없음')
    if bad: return bad
    if card['cat'] not in CATS: bad.append(f"cat 이 목록 밖: {card['cat']}")
    keys = set()
    for f in card['fields']:
        if not (isinstance(f, dict) and re.fullmatch(r'[a-z]\w*', str(f.get('k', ''))) and f.get('label') and 'ex' in f and isinstance(f.get('opt'), bool)):
            bad.append(f'fields 항목 모양: {f}'); continue
        keys.add(f['k'])
    used = set(re.findall(r'\{(\w+)\}', card['tpl'] + json.dumps(card['dx'], ensure_ascii=False)))
    if used - keys - COMMON: bad.append(f'정의 안 된 칸: {sorted(used - keys - COMMON)}')
    dx = card['dx']
    if dx.get('kind') not in KINDS: bad.append(f"kind: {dx.get('kind')}")
    base = e.get('_dur') or dx.get('base') or 0
    for b in dx.get('beats', []):
        if not b.get('s'): bad.append('beat s 없음')
        elif b.get('label'):
            if (b.get('t0'), b.get('t1')) != (-1, -1): bad.append('label 있는 beat 는 t0=t1=-1')
        elif not (0 <= b.get('t0', -1) < b.get('t1', -1) <= base + 0.05): bad.append(f"beat 시간 범위: {b.get('t0')}~{b.get('t1')} / base {base}")
    if not dx.get('beats'): bad.append('beats 비어 있음')
    if not re.search(r'[가-힣]', card['tpl']): bad.append('tpl 이 한국어가 아님')
    copied = ngrams(json.dumps(card, ensure_ascii=False)) & ngrams(e['prompt'])
    if copied: bad.append(f'원문 영어를 그대로 옮김: {sorted(copied)[:2]}')
    return bad


GUIDE = f"""너는 모션그래픽 «요청 카드» 편집자다. 아래 실전 예시(영어 프롬프트 + 실제 영상 길이)를 각각 요청 카드 하나로 바꿔라.
도구는 쓰지 말고, 답은 ```json 블록 하나에 JSON 배열만 낸다(입력 순서 그대로, 항목마다 id 포함).

카드 모양(예시 두 장 — 이 키·모양을 그대로 따른다, code·en·inds·d3 는 빼도 된다):
{json.dumps([{k: c[k] for k in ('name', 'plain', 'len', 'when', 'cat', 'fields', 'tpl', 'dx')} for c in SAMPLE], ensure_ascii=False)}

규칙
- 모든 글은 자연스러운 한국어. 영어 프롬프트 문장을 옮겨 적거나 번역해 붙이지 말고, 영상이 «무엇을 어떻게 움직이는지»를 우리 말로 새로 쓴다(영어 8단어 이상 연속 금지). 브랜드·제품 이름은 칸(예시값)으로 뺀다.
- name: 이 모션을 부르는 짧은 한국어 이름(제품 이름 말고 모션 종류, 예: «앱 화면 기능 소개 릴»). plain: 초보자용 2문장 설명. when: 쓸 때(쉼표로 3개쯤).
- cat: 다음 중 하나 그대로 — {' | '.join(CATS)}
- fields: 사용자가 바꿔 넣을 칸 2~5개 {{k(영문 소문자), label, opt(bool), ex(예시값)}}. 길이 칸이 필요하면 k=dur. 공통 칸 {{ratio}}·{{color}}·{{file}} 은 fields 에 넣지 않는다.
- tpl: «… 만들어줘.» 로 끝나는 한국어 요청 한두 문장. 칸은 {{k}}, 선택 칸이 든 구절은 [[ … {{k}} …]] 로 감싼다.
- dx.kind: scene|overlay|transition|loop. dx.base = 주어진 영상 길이(초). dx.beats: 3~7개, 시간 순서, 0 ≤ t0 < t1 ≤ base, label 은 "".
  머무는 구간은 hold:true. 시간과 무관한 규칙은 label 에 이름을 쓰고 t0=t1=-1. 각 s 는 그 구간에 화면에서 벌어지는 일을 구체적으로.
- dx.look(모양·색·글꼴), dx.wow(볼거리 한 번), dx.avoid(하지 말 것), dx.lenText 는 "". len 은 «약 N초».
- 프롬프트가 「무엇을 만들지 물어보라」는 식이면 그 질문 항목을 fields 로 만든다. 스킬(설치형) 항목은 그 스킬이 만드는 영상의 일반적인 흐름으로 쓴다.
"""


def ask(batch):
    items = [{'id': e['id'], 'title': e['title'], 'tags': e['tags'], 'size': e['size'], 'seconds': e['_dur'],
              'type': e['type'], 'prompt': e['prompt'][:6000]} for e in batch]
    task = GUIDE + '\n입력:\n' + json.dumps(items, ensure_ascii=False)
    r = subprocess.run([str(Path.home() / '.local/bin/edb-p'), '--model', 'sonnet', '--effort', 'medium'],
                       input=task, capture_output=True, text=True, timeout=1800)
    if r.returncode == 3: sys.exit('edb 주간 상한 — 레인에서 처리하거나 리셋 뒤 다시')
    m = re.search(r'```json\s*(\[.*?\])\s*```', r.stdout, re.S)
    if not m: raise ValueError(f'JSON 블록 없음 (종료 {r.returncode}): {r.stdout[-300:]}{r.stderr[-300:]}')
    return json.loads(m.group(1))


def main():
    a = sys.argv[1:]
    n = int(a[a.index('--batch') + 1]) if '--batch' in a else 8
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else None
    workers = int(a[a.index('--workers') + 1]) if '--workers' in a else 4
    src = json.loads(SRC.read_text(encoding='utf-8'))
    out = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    todo = [e for e in src if out.get(e['id'], {}).get('src_sha') != sha(e)][:limit]
    print(f'바꿀 항목 {len(todo)}개 / 전체 {len(src)}', file=sys.stderr)
    for e in todo: e['_dur'] = duration(e['video']) or 15
    fails = {}
    for rnd in range(3):  # 검사에 걸린 항목만 다시 보낸다
        batches = [todo[i:i + n] for i in range(0, len(todo), n)]
        with ThreadPoolExecutor(workers) as pool:  # edb-p 호출을 몇 개씩 동시에 — 저장·검사는 이 스레드에서만
            futs = {pool.submit(ask, b): b for b in batches}
            for done, fut in enumerate(as_completed(futs), 1):
                batch = futs[fut]
                try:
                    got = {c.get('id'): c for c in fut.result()}
                except Exception as ex:
                    print(f'묶음 실패: {ex}', file=sys.stderr); fails.update({e['id']: [str(ex)[:200]] for e in batch}); continue
                for e in batch:
                    c = got.get(e['id'])
                    bad = check(c, e) if isinstance(c, dict) else ['응답에 없음']
                    if c and not bad:
                        c['dx']['base'] = e['_dur']; c['dx'].setdefault('lenText', '')
                        out[e['id']] = {**{k: c[k] for k in ('name', 'plain', 'when', 'len', 'cat', 'fields', 'tpl', 'dx')}, 'src_sha': sha(e)}
                        fails.pop(e['id'], None)
                    else:
                        fails[e['id']] = bad
                OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
                print(f'[{rnd}] 묶음 {done}/{len(batches)} · 통과 누계 {len(out)} · 실패 {len(fails)}', file=sys.stderr)
        todo = [e for e in todo if e['id'] in fails]
        if not todo: break
    print(f'끝: {len(out)}개 저장 · 실패 {len(fails)}개 {list(fails.items())[:5]}', file=sys.stderr)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()

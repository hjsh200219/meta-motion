#!/usr/bin/env python3
"""cokacmotion(aimotion) 기법 데모 목록을 받아 data/cokac.json 을 다시 만든다.
목록은 제목·기법·분류·장면·요점·라이브러리·주의만 싣는다. 노트(NOTES.md)·소스·그림(약 100MB)은 repo 에 싣지 않는다.
볼 때 `cokac.py` 가 캐시 클론에서 읽는다.
출처: https://github.com/kstost/cokacmotion (skills/aimotion, MIT © 2026 kstost) — script-to-motion 이 쓰는 기법 참고서.
실행: python3 build_cokac.py  (git·네트워크 필요 · 클론 캐시 ~/.cache/meta-motion/cokacmotion)"""
import datetime, json, subprocess, sys
from pathlib import Path

REPO = 'https://github.com/kstost/cokacmotion.git'
CACHE = Path.home() / '.cache' / 'meta-motion' / 'cokacmotion'
OUT = Path(__file__).resolve().parent / 'data' / 'cokac.json'
FLOOR = 150   # 2026-11-11 실측 166 — 이보다 적으면 색인 형식이 바뀐 것으로 보고 중단
KEYS = ('id', 'number', 'title', 'tech', 'group', 'scene', 'points', 'libraries', 'cautions')


def git(*a, cwd=None):
    return subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def sync_repo(commit=None, cache=CACHE):
    """캐시 클론을 맞춘다 — commit(전체 SHA)을 주면 그 커밋(cokac.py 가 목록과 같은 판을 보게), 없으면 최신 main.
    그 커밋을 못 받으면(저장소 이력 정리 등) 최신 main 으로 받고 알린다 — 노트가 목록과 조금 다를 수 있다."""
    cache = Path(cache)
    if not (cache / '.git').exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        git('clone', '-q', '--depth', '1', REPO, str(cache))
    head = git('rev-parse', 'HEAD', cwd=cache)
    if commit and head == commit: return head
    try:
        git('fetch', '-q', '--depth', '1', 'origin', commit or 'main', cwd=cache)
    except subprocess.CalledProcessError:
        if not commit: raise
        print(f'주의: cokacmotion 커밋 {commit[:7]} 을 받지 못해 최신 main 으로 봅니다 — build_cokac.py 로 목록을 다시 만들면 맞춰진다', file=sys.stderr)
        git('fetch', '-q', '--depth', '1', 'origin', 'main', cwd=cache)
    git('reset', '-q', '--hard', 'FETCH_HEAD', cwd=cache)
    return git('rev-parse', 'HEAD', cwd=cache)


def convert(src, commit, fetched, minimum=FLOOR):
    items = sorted(({k: d.get(k, [] if k in ('points', 'libraries', 'cautions') else '') for k in KEYS} for d in src['demos']),
                   key=lambda d: d['number'])
    if len(items) < minimum: sys.exit(f'데모 {len(items)}개 — {minimum}개 미만이라 중단(색인 형식 확인)')
    return {'source': 'https://github.com/kstost/cokacmotion/tree/main/skills/aimotion', 'license': 'MIT © 2026 kstost',
            'commit': commit, 'fetched': fetched, 'rule': src.get('principle', ''),
            'groups': [g if isinstance(g, str) else g.get('name', '') for g in src.get('groups', [])], 'items': items}


def main():
    commit = sync_repo()
    src = json.loads((CACHE / 'skills' / 'aimotion' / 'index.json').read_text(encoding='utf-8'))
    out = convert(src, commit, datetime.date.today().isoformat())
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"{OUT.name}: {len(out['items'])}개 · 커밋 {out['commit']} · 분류 {len(out['groups'])}개")


if __name__ == '__main__':
    main()

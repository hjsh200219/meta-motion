#!/usr/bin/env python3
"""애니메이션 스킬 6개 — claude-animation-skills(MIT © 2026 Artem Novitckii)를 한국어 카드로 한 카탈로그에 싣는다(data/anim_skills.json).
빠른 4개(그래프·3D 지도·3D 분해도·라인 아트)는 JSON 사양 → 원본 template.html → HyperFrames 로 1080x1920 영상 한 개,
엔진 2개(막대 인간·3D 만화)는 음성이 붙는 릴스 한 편짜리 작업이다. 카드는 손으로 쓴 한국어 사양이고, 원본(SKILL.md·build.py·템플릿)은
싣지 않고 쓸 때 고정 커밋 캐시 클론(~/.cache/meta-motion/claude-animation-skills)에서 읽는다 — 검토한 판만 쓰도록 커밋을 고정한다.
실행: python3 animskills.py thumbs   목록 그림(data/as_thumb/<code>.jpg)을 원본 docs/skills.jpg 에서 잘라 다시 만든다(ffmpeg)"""
import functools, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data' / 'anim_skills.json'
CACHE = Path.home() / '.cache' / 'meta-motion' / 'claude-animation-skills'
ORDER = ['as-3d-cartoon', 'as-stick-figure', 'as-line-art', 'as-map-route', 'as-breakdown', 'as-graph']  # docs/skills.jpg 왼쪽부터


@functools.lru_cache(maxsize=1)
def load():
    return json.loads(DATA.read_text(encoding='utf-8'))


def sync():
    """고정 커밋 캐시 — 못 받거나 HEAD 가 다르면 멈춘다(build_cokac.sync_repo 와 같은 규칙)."""
    import build_cokac
    idx = load()
    return build_cokac.sync_repo(idx['commit'], cache=CACHE, repo=idx['source'] + '.git')


def credit(code):
    idx, c = load(), load()['items'][code]
    d = CACHE / 'skills' / c['skill']
    head = f"\n[원본 스킬] {c['skill']} — {idx['source']}/tree/{idx['commit'][:7]}/skills/{c['skill']} ({idx['license']}, 커밋 {idx['commit'][:7]}) · 렌더 {c['render']} · 1080x1920"
    if c['engine']:
        how = (f"\n[만드는 법] 원본 절차 {d}/SKILL.md 를 따른다 — 엔진 {d}/engine 을 새 폴더로 복사해 대본·음성·장면 코드를 새로 쓴다"
               f"\n  처음 한 번: bash {CACHE}/kit/setup.sh --voice (Node 패키지·Chromium·음성 모델 약 1GB) · 캐시가 없으면 python3 animskills.py sync")
    else:
        how = (f"\n[만드는 법] 사양 JSON(<이름>.json)을 쓰고 python3 {d}/build.py <이름>.json → <이름>.mp4 + 안전 영역 표시 미리보기 시트 <이름>.sheet.jpg"
               f"\n  처음 한 번: bash {CACHE}/kit/setup.sh (three.js·Playwright·GSAP·HyperFrames) · 캐시가 없으면 python3 animskills.py sync"
               f"\n  사양 예: {json.dumps(c['spec'], ensure_ascii=False)}")
    return head + how + ''.join(f"\n주의: {n}" for n in c.get('notes', [])) + '\n⛔ 원본 예시의 문구·장면을 그대로 쓰지 않는다 · 코드를 거의 그대로 옮기면 MIT 고지를 함께 둔다'


def thumbs():
    """docs/skills.jpg(2272x728, 6칸 · 칸 360x640, x=16+376i, y=16)를 칸마다 잘라 data/as_thumb/ 에 둔다."""
    sync()
    out = HERE / 'data' / 'as_thumb'; out.mkdir(exist_ok=True)
    for i, code in enumerate(ORDER):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(CACHE / 'docs' / 'skills.jpg'), '-vf', f'crop=360:640:{16 + 376 * i}:16',
                        '-q:v', '4', str(out / f'{code}.jpg')], check=True)
    print(f'{len(ORDER)}장 → {out}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'thumbs': thumbs()
    elif cmd == 'sync': print(sync())
    else: sys.exit(__doc__)

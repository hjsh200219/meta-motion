#!/usr/bin/env python3
"""HyperFrames 공식 레지스트리(블록·컴포넌트) 목록을 받아 data/hf_registry.json 을 다시 만든다.
목록만 저장한다(이름·설명·태그·해상도·길이) — 항목 HTML 은 쓸 때 `hf.py add` 가 `npx hyperframes add` 로 받는다.
출처: https://github.com/heygen-com/hyperframes (registry/, Apache-2.0) · 카탈로그 https://hyperframes.heygen.com/catalog
실행: python3 build_hf.py  (npx·네트워크 필요)"""
import datetime, json, subprocess, sys
from pathlib import Path

HF = 'hyperframes@0.8.162'  # SKILL.md 렌더 고정 버전과 같게
OUT = Path(__file__).resolve().parent / 'data' / 'hf_registry.json'
FLOOR = 400                 # 2026-10-17 실측 447 — 이보다 적으면 CLI 출력이 바뀐 것으로 보고 중단
# repo CREDITS.md 가 「Origin to be confirmed with the author」로 적은 자산이 든 항목 — 출처가 확인될 때까지 쓰지 않는다
EXCLUDE = {
    'canopy-part-title': 'leaf-surface-color/normal.webp 출처 미확인(CREDITS.md)',
    'glass-shard-title': 'matcap-1.png 출처 미확인(CREDITS.md)',
    'frost-sequence-camera-orbit': 'shards-atlas.png 등 텍스처 출처 미확인(CREDITS.md)',
}


def fetch():
    out = subprocess.run(['npx', '--yes', HF, 'catalog', '--json'], capture_output=True, text=True, check=True).stdout
    return json.loads(out[out.index('['):])


def main():
    items = fetch()
    if len(items) < FLOOR: sys.exit(f'항목 {len(items)}개 — {FLOOR}개 미만이라 중단(catalog --json 형식 확인)')
    keep = [{k: it.get(k) for k in ('name', 'type', 'title', 'description', 'tags', 'dimensions', 'duration')}
            for it in sorted(items, key=lambda x: x['name']) if it['name'] not in EXCLUDE]
    data = {'source': 'https://github.com/heygen-com/hyperframes/tree/main/registry', 'license': 'Apache-2.0',
            'cli': HF, 'fetched': datetime.date.today().isoformat(), 'excluded': EXCLUDE, 'items': keep}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(keep)}개 저장(받은 {len(items)} · 제외 {len(items) - len(keep)}) → {OUT}')


if __name__ == '__main__':
    main()

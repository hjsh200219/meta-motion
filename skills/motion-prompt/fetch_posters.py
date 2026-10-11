#!/usr/bin/env python3
"""prompt_motion.json 의 대표 이미지(poster, 영상의 한 장면)를 data/posters/<id>.<확장자> 로 받는다 — preview.html 이 쓴다.
이미 받은 파일은 건너뛴다. 사내 참고용(영상·이미지는 만든 사람 소유) — git 에는 올리지 않는다(.gitignore)."""
import json, sys, time, urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent / 'data'
OUT = D / 'posters'
UA = {'User-Agent': 'motion-prompt-plugin/1 (internal reference)'}


def main():
    OUT.mkdir(exist_ok=True)
    items = [e for e in json.loads((D / 'prompt_motion.json').read_text(encoding='utf-8')) if e.get('poster', '').startswith('https://')]
    got = bad = 0
    for e in items:
        f = OUT / f"{e['id']}.{e['poster'].rsplit('.', 1)[-1]}"
        if f.exists(): continue
        try:
            f.write_bytes(urllib.request.urlopen(urllib.request.Request(e['poster'], headers=UA), timeout=30).read()); got += 1
        except Exception as ex:
            bad += 1; print(f"{e['id']}: {ex}", file=sys.stderr)
        time.sleep(0.3)
    print(f'받음 {got} · 실패 {bad} · 대상 {len(items)} → {OUT}', file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

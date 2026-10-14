#!/usr/bin/env python3
"""prompt_motion.json 의 대표 이미지(poster, 영상의 한 장면)를 data/posters/<id>.<확장자> 로 받는다 — preview.html 이 쓴다.
--clips 를 주면 영상을 미리보기용(긴 변 540px·평균 약 200kbps, 합계가 Artifact 한 버전 256MB 안)으로 줄여 data/clips/<id>.mp4 로 만든다(ffmpeg 필요).
이미 받은 파일은 건너뛴다. 사내 참고용(영상·이미지는 만든 사람 소유) — git 에는 올리지 않는다(.gitignore)."""
import json, re, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

D = Path(__file__).resolve().parent / 'data'
OUT = D / 'posters'
CLIPS = D / 'clips'
UA = {'User-Agent': 'meta-motion-plugin/1 (internal reference)'}


def posters(items):
    OUT.mkdir(exist_ok=True)
    got = bad = 0
    for e in items:
        if not e.get('poster', '').startswith('https://'): continue
        f = OUT / f"{e['id']}.{e['poster'].rsplit('.', 1)[-1]}"
        if f.exists(): continue
        try:
            f.write_bytes(urllib.request.urlopen(urllib.request.Request(e['poster'], headers=UA), timeout=30).read()); got += 1
        except Exception as ex:
            bad += 1; print(f"{e['id']}: {ex}", file=sys.stderr)
        time.sleep(0.3)
    return got, bad, OUT


def clip(e):
    # 수집 자료의 주소라 사이트 영상 서버(https)만 열고 ffmpeg 도 https 계열 프로토콜만 쓰게 묶는다
    if not re.fullmatch(r'https://media\.prompt-motion\.com/[\w./-]+', e.get('video') or ''): return f"{e['id']}: 영상 주소 아님"
    f = CLIPS / f"{e['id']}.mp4"
    if f.exists(): return None
    tmp = f.with_suffix('.part.mp4')
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-protocol_whitelist', 'https,tls,tcp', '-i', e['video'],
                        '-vf', "scale='if(gte(iw,ih),min(540,iw),-2)':'if(gte(iw,ih),-2,min(540,ih))'",
                        '-c:v', 'libx264', '-preset', 'slow', '-crf', '30', '-maxrate', '220k', '-bufsize', '440k', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '32k', '-ac', '1', '-movflags', '+faststart', str(tmp)], capture_output=True, text=True, timeout=1800)
    if r.returncode: tmp.unlink(missing_ok=True); return f"{e['id']}: {r.stderr[-200:]}"
    tmp.rename(f)


def clips(items):
    CLIPS.mkdir(exist_ok=True)
    with ThreadPoolExecutor(4) as pool:
        errs = [m for m in pool.map(clip, items) if m]
    for m in errs: print(m, file=sys.stderr)
    return sum(not f.name.endswith('.part.mp4') for f in CLIPS.glob('*.mp4')), len(errs), CLIPS


def main():
    items = json.loads((D / 'prompt_motion.json').read_text(encoding='utf-8'))
    got, bad, out = (clips if '--clips' in sys.argv else posters)(items)
    print(f'받음 {got} · 실패 {bad} · 대상 {len(items)} → {out}', file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""렌더 뒤 검사 — 다 만든 영상 파일(mp4)을 ffmpeg 로 재서 눈으로 놓치기 쉬운 것을 알린다. 렌더 전 검사(check.py)·미술감독 채점(art-director.md)과 짝.
기준은 2026-11-22 쇼츠 «10 GitHub Repos That Level Up HyperFrames Videos» 의 키트들에서 가져와 실측으로 맞췄다(코드는 옮기지 않음):
  blank·frozen   reelforge gallery-verify.mjs(Apache-2.0) — 거의 모든 프레임이 검정/흰색이면, 처음부터 끝까지 움직임이 없으면 오류
  dead_time      design-engineering launch-video-review(MIT)·product-launch-motion(MIT) — 중간에 2초 넘게 멈춘 구간, 마지막 정지 3초 초과는 경고
  black_edge     huashu-design verify-video.sh(MIT) — 처음·끝 0.3초가 통째로 검으면 경고(페이드 인·아웃이면 무시해도 된다)
  size·duration  huashu-design verify-video.sh — 기대한 크기와 다르면, 길이가 ±max(2%, 0.2초) 밖이면 오류
  no_audio       사용자 기본값 1(음성은 기본으로 붙인다) — 소리 트랙이 없으면 경고(--no-audio 면 정상)
  loudness       쇼츠 납품 기준 -14 LUFS(saas-motion-kit deliver.sh·herk-edit-kit·product-launch-motion master.sh) — 통합 음량이 -18~-10 밖이면,
                 true peak 가 -1 dBTP 를 넘으면 경고(huashu verify-video.sh 의 경고 구간)
종료 코드 1 = 오류(--strict 면 경고도) · 파일이 없거나 못 읽으면 1.
실행: python3 motion.py verify <영상.mp4> [--size 1080x1920] [--dur 32.5] [--no-audio] [--strict] [--json]"""
import json, re, subprocess, sys

BLANK_Y, BLANK_SHARE = (3, 252), 0.8    # 프레임 평균 밝기(Y, 0~255)가 이 밖이면 빈 화면 · 그런 프레임이 80% 넘으면 오류
FPS, STILL_MAX, DEAD_MIN, LAST_HOLD = 10, 5, 2.0, 3.0
LUFS_OK, TP_MAX = (-18.0, -10.0), -1.0


def _ff(args):
    return subprocess.run(['ffmpeg', '-hide_banner', '-nostats', *args, '-f', 'null', '-'], capture_output=True, text=True).stderr


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,avg_frame_rate:format=duration', '-of', 'json', path],
                       capture_output=True, text=True)
    if r.returncode: raise ValueError(r.stderr.strip() or '읽을 수 없음')
    j = json.loads(r.stdout); v = next((s for s in j.get('streams', []) if s['codec_type'] == 'video'), None)
    if not v: raise ValueError('영상 트랙 없음')
    n, d = (v.get('avg_frame_rate') or '0/1').split('/')
    return {'width': v['width'], 'height': v['height'], 'fps': round(int(n) / int(d), 2) if int(d) else 0,
            'duration': float(j['format'].get('duration') or 0), 'audio': any(s['codec_type'] == 'audio' for s in j['streams'])}


def luma(path):
    """초당 4장, 160x90 으로 줄여 프레임 평균 밝기(YAVG) — 0~255 전체 범위로 바꿔 잰다(mp4 yuv420p 는 제한 범위라 검정이 16 으로 나온다, 2026-11-22 실측)."""
    err = _ff(['-i', path, '-vf', 'fps=4,scale=160:90:out_range=full,format=yuvj420p,signalstats,metadata=print:key=lavfi.signalstats.YAVG', '-an'])
    return [float(x) for x in re.findall(r'lavfi\.signalstats\.YAVG=([\d.]+)', err)]


def freezes(path):
    """멈춘 구간 [(시작, 끝)] — 끝이 None 이면 마지막까지 멈춤. 초당 10장(480 폭·회색)에서 이웃 프레임 차이의 최대값(YMAX)이 STILL_MAX 이하면 멈춤.
    ffmpeg freezedetect(평균 차이)는 가는 획·작은 라벨만 움직이는 화면(손글씨·다이어그램)을 멈춤으로 잘못 본다 — 2026-11-22 실측:
    정지 화면 차이 최대값 0 · 손글씨·다이어그램·숨 쉬는 밝기 변화 6 이상."""
    err = _ff(['-i', path, '-vf', f'fps={FPS},scale=480:-2:out_range=full,format=gray,tblend=all_mode=difference,signalstats,'
                              'metadata=print:key=lavfi.signalstats.YMAX', '-an'])
    d = [int(x) for x in re.findall(r'lavfi\.signalstats\.YMAX=(\d+)', err)]  # d[j] = 프레임 j 와 j+1 의 차이
    out, j = [], 0
    while j < len(d):
        if d[j] > STILL_MAX: j += 1; continue
        k = j
        while k + 1 < len(d) and d[k + 1] <= STILL_MAX: k += 1
        out.append((j / FPS, None if k == len(d) - 1 else (k + 1) / FPS)); j = k + 1
    return out


def blacks(path):
    err = _ff(['-i', path, '-vf', 'blackdetect=d=0.1:pic_th=0.98', '-an'])
    return [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', err)]


def loudness(path):
    err = _ff(['-i', path, '-vn', '-af', 'ebur128=peak=true'])
    tail = err[err.rfind('Summary:'):] if 'Summary:' in err else ''
    i = re.search(r'I:\s+(-?[\d.]+|-inf) LUFS', tail); p = re.search(r'Peak:\s+(-?[\d.]+|-inf) dBFS', tail)
    f = lambda m: None if not m or m.group(1) == '-inf' else float(m.group(1))
    return f(i), f(p)


def run(path, size=None, dur=None, audio=True):
    out, add = [], lambda code, sev, msg: out.append({'code': code, 'severity': sev, 'message': msg})
    info = probe(path); D = info['duration']
    if size and (info['width'], info['height']) != tuple(size):
        add('size', 'error', f"크기 {info['width']}x{info['height']} — 기대 {size[0]}x{size[1]}")
    if dur and abs(D - dur) > max(dur * 0.02, 0.2):
        add('duration', 'error', f'길이 {D:.2f}초 — 기대 {dur}초(±{max(dur * 0.02, 0.2):.2f})')
    ys = luma(path)
    if ys and sum(not (BLANK_Y[0] <= y <= BLANK_Y[1]) for y in ys) / len(ys) > BLANK_SHARE:
        add('blank', 'error', f'빈 화면 — 프레임 {len(ys)}장 중 {BLANK_SHARE:.0%} 넘게 거의 검정·흰색(평균 밝기 {BLANK_Y[0]} 미만·{BLANK_Y[1]} 초과). 글·그림이 안 그려졌거나 배경만 렌더됨')
    fz = freezes(path)
    whole = any(s <= 0.05 and (e is None or e >= D - 0.1) for s, e in fz)
    if whole:
        add('frozen', 'error', '처음부터 끝까지 움직임 없음 — 타임라인이 등록·재생되지 않았거나(window.__timelines) 시작 화면만 찍힘')
    else:
        for s, e in fz:
            if e is None or e >= D - 0.1:  # 마지막 정지 — 읽을 시간은 1.8~2초면 충분, 3초 넘으면 늘어진다
                if D - s > LAST_HOLD: add('dead_time', 'warning', f'마지막 {D - s:.1f}초가 멈춰 있음({s:.1f}초부터) — 마지막 정지는 {LAST_HOLD:.0f}초 이내로')
            elif e - s >= DEAD_MIN:
                add('dead_time', 'warning', f'{s:.1f}~{e:.1f}초({e - s:.1f}초) 화면이 멈춤 — 배경이 숨 쉬듯 조금이라도 움직이거나 장면을 줄인다')
    for a, b in blacks(path):
        if a <= 0.05 and b >= 0.3: add('black_edge', 'warning', f'첫 {b:.1f}초가 검은 화면 — 첫 프레임이 썸네일·첫인상이다(의도한 페이드 인이면 무시)')
        elif b >= D - 0.05 and D - a >= 0.3: add('black_edge', 'warning', f'마지막 {D - a:.1f}초가 검은 화면(의도한 페이드 아웃이면 무시)')
    info['lufs'] = info['true_peak'] = None
    if not info['audio']:
        if audio: add('no_audio', 'warning', '소리 트랙 없음 — 음성은 기본으로 붙인다(무음 영상이면 --no-audio). <audio> 를 넣었는데 없으면 렌더 로그·lint(media_missing_id)를 본다')
    else:
        info['lufs'], info['true_peak'] = loudness(path)
        L, P = info['lufs'], info['true_peak']
        if L is None or not (LUFS_OK[0] <= L <= LUFS_OK[1]):
            add('loudness', 'warning', f"통합 음량 {'측정 불가(무음)' if L is None else f'{L:.1f} LUFS'} — 쇼츠 납품 기준 -14 LUFS(허용 {LUFS_OK[0]:.0f}~{LUFS_OK[1]:.0f}). "
                                        "ffmpeg -af loudnorm=I=-14:TP=-1.5:LRA=11 로 맞춘다")
        if P is not None and P > TP_MAX:
            add('loudness', 'warning', f'최고 레벨 {P:.1f} dBTP — {TP_MAX:.0f} dBTP 이하로(재생기·업로드 재인코딩에서 찌그러진다)')
    return {'file': path, 'info': info, 'findings': out}


def main(args):
    opt = {'json': '--json' in args, 'strict': '--strict' in args, 'audio': '--no-audio' not in args}
    val = lambda k: args[args.index(k) + 1] if k in args and args.index(k) + 1 < len(args) else None
    files = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--size', '--dur'))]
    if len(files) != 1: sys.exit(__doc__)
    size = tuple(int(n) for n in val('--size').lower().split('x')) if val('--size') else None
    dur = float(val('--dur')) if val('--dur') else None
    try:
        r = run(files[0], size, dur, opt['audio'])
    except (ValueError, FileNotFoundError) as e:
        print(f'검사 실패: {files[0]} — {e}'); return 1
    if opt['json']: print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        i = r['info']
        print(f"{r['file']} — {i['width']}x{i['height']} · {i['fps']}fps · {i['duration']:.2f}초 · 소리 {'있음' if i['audio'] else '없음'}"
              + (f" · {i['lufs']:.1f} LUFS" if i['lufs'] is not None else '') + (f" · 최고 {i['true_peak']:.1f} dBTP" if i['true_peak'] is not None else ''))
        for f in r['findings']: print(f"{'✗' if f['severity'] == 'error' else '⚠'} {f['code']}: {f['message']}")
        if not r['findings']: print('문제 없음')
    bad = [f for f in r['findings'] if f['severity'] == 'error' or opt['strict']]
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

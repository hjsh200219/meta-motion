"""verify.py — 렌더한 영상(mp4) 검사. ffmpeg lavfi 로 만든 작은 영상으로 판정을 확인한다. python3 test_verify.py (ffmpeg 필요, 네트워크 없음)."""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify

T = tempfile.mkdtemp()


def mk(name, vf, af=None, dur=3):
    """lavfi 입력으로 320x180 30fps 영상을 만든다 — vf 는 비디오 그래프(출력 [v]), af 가 있으면 소리를 붙인다."""
    out = os.path.join(T, name)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-filter_complex', vf + (f';{af}' if af else ''), '-map', '[v]']
    if af: cmd += ['-map', '[a]', '-c:a', 'aac']
    subprocess.run(cmd + ['-t', str(dur), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '30', out], check=True)
    return out


MOVE = 'testsrc2=s=320x180:r=30:d={d}'
TONE = 'sine=f=440:d=3,volume=2.5[a]'  # 약 -14 LUFS 근처의 또렷한 소리
codes = lambda r, sev=None: {f['code'] for f in r['findings'] if sev is None or f['severity'] == sev}

good = mk('good.mp4', MOVE.format(d=3) + '[v]', TONE)
r = verify.run(good)
assert not codes(r, 'error'), r
assert r['info']['width'] == 320 and r['info']['height'] == 180 and abs(r['info']['duration'] - 3) < 0.15 and r['info']['audio'], r['info']
assert r['info']['lufs'] is not None, r['info']

r = verify.run(mk('black.mp4', 'color=c=black:s=320x180:r=30:d=3[v]', TONE))
assert 'blank' in codes(r, 'error'), r  # 거의 모든 프레임이 검은 화면

r = verify.run(mk('still.mp4', 'color=c=0x3366cc:s=320x180:r=30:d=3[v]', TONE))
assert 'frozen' in codes(r, 'error') and 'blank' not in codes(r), r  # 처음부터 끝까지 한 장면이 멈춤

dead = mk('dead.mp4', f'{MOVE.format(d=1.5)}[m1];color=c=0x3366cc:s=320x180:r=30:d=2.5[s];{MOVE.format(d=1.5)}[m2];[m1][s][m2]concat=n=3:v=1:a=0[v]',
          'sine=f=440:d=5.5,volume=2.5[a]', dur=5.5)
r = verify.run(dead)
assert 'dead_time' in codes(r, 'warning') and 'frozen' not in codes(r), r  # 중간 2.5초 정지

r = verify.run(mk('mute.mp4', MOVE.format(d=3) + '[v]'))
assert 'no_audio' in codes(r, 'warning'), r  # 기본값(음성은 기본으로 붙인다)과 다르다
assert 'no_audio' not in codes(verify.run(os.path.join(T, 'mute.mp4'), audio=False)), '--no-audio 면 소리 없음이 정상'

r = verify.run(mk('quiet.mp4', MOVE.format(d=3) + '[v]', 'sine=f=440:d=3,volume=0.02[a]'))
assert 'loudness' in codes(r, 'warning'), r

r = verify.run(mk('blackhead.mp4', f'color=c=black:s=320x180:r=30:d=0.6[b];{MOVE.format(d=2.4)}[m];[b][m]concat=n=2:v=1:a=0[v]', TONE))
assert 'black_edge' in codes(r, 'warning'), r  # 첫 화면이 검다

r = verify.run(good, size=(1080, 1920), dur=10)
assert {'size', 'duration'} <= codes(r, 'error'), r  # 기대한 크기·길이와 다르다
assert not codes(verify.run(good, size=(320, 180), dur=3.05)), '허용 범위 안'

# 명령: 종료 코드 — 오류면 1, 경고만이면 0(--strict 면 1)
run = lambda *a: subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motion.py'), 'verify', *a], capture_output=True, text=True)
p = run(good); assert p.returncode == 0, p.stdout + p.stderr
p = run(os.path.join(T, 'black.mp4')); assert p.returncode == 1 and 'blank' in p.stdout, p.stdout
p = run(os.path.join(T, 'mute.mp4')); assert p.returncode == 0 and 'no_audio' in p.stdout, p.stdout
assert run(os.path.join(T, 'mute.mp4'), '--strict').returncode == 1
assert run(os.path.join(T, 'mute.mp4'), '--no-audio', '--strict').returncode == 0
import json
j = json.loads(run(good, '--json').stdout); assert j['info']['width'] == 320 and isinstance(j['findings'], list)
assert run(os.path.join(T, 'none.mp4')).returncode == 1  # 없는 파일
print('test_verify: ok')

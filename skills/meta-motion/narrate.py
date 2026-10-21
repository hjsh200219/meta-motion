#!/usr/bin/env python3
"""장면별 내레이션 — `python3 motion.py narrate <대본.txt> --out <폴더> [--dry-run] [--force] [--tempo 1.21]`.

setup 저장소(또는 환경변수·workspace .env)에서 Fish Audio 키를 꺼내 환경변수로만 넘기고 narrate/narrate.mjs 를 돌린다(키는 찍지 않는다).
장면은 recommend 와 같은 규칙(빈 줄로 나눈 문단, 빈 줄이 없으면 줄마다). 결과 track.wav · seg-NN.wav · segments.json · `--durs` 한 줄.
필요: Node 18+, ffmpeg·ffprobe. 키가 없으면 `python3 motion.py setup --only fish`.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jev  # noqa: E402

PY = "python" if os.name == "nt" else "python3"


def main(argv):
    if os.name == "nt":  # cp949 콘솔·파이프에서 한글 안내가 깨지지 않게
        for s in (sys.stdout, sys.stderr):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError):
                pass
    if not [a for a in argv if not a.startswith("--")]:
        print(__doc__)
        return 2
    missing = [b for b in ("node", "ffmpeg", "ffprobe") if not shutil.which(b)]
    if missing:
        print("✗ 필요한 프로그램이 없습니다: " + ", ".join(missing) + " — Node.js 18+ 와 ffmpeg 를 설치하세요", file=sys.stderr)
        return 1
    env = dict(os.environ)
    if "--dry-run" not in argv:
        key, _ = jev.load_secret("fish-audio", "FISH_AUDIO_API_KEY", "FISH_AUDIO_API_KEY")
        if not key:
            print(f"✗ Fish Audio 키가 없습니다 — {PY} {os.path.join(HERE, 'setup.py')} --only fish", file=sys.stderr)
            return 1
        env["FISH_AUDIO_API_KEY"] = key
    return subprocess.run(["node", os.path.join(HERE, "narrate", "narrate.mjs"), *argv], env=env).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

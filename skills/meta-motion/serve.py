#!/usr/bin/env python3
"""KB 모션 메뉴(kb.pilldoc.co.kr/motion/)를 로컬에서 띄운다 — `python3 motion.py`(인자 없음)가 부른다. 표준 라이브러리만 쓴다.
export_kb.py 와 같은 페이지(원본 영상 모드)를 캐시 폴더에 만들고 127.0.0.1 에서 열어 둔다. Ctrl-C 로 끈다.
실행: python3 serve.py [--port 8765] [--no-open] [--out <폴더>]"""
import functools, http.server, sys, webbrowser
from pathlib import Path
from export_kb import build

OUT = Path.home() / '.cache' / 'meta-motion' / 'kb'


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass               # 요청마다 찍히는 줄로 터미널을 덮지 않는다


def main(argv):
    opt = {'port': '8765', 'out': str(OUT)}; it = iter(argv)
    for a in it:
        if a == '--no-open': opt['no-open'] = True
        elif a.startswith('--'): opt[a[2:]] = next(it, '')
    root = Path(opt['out'])
    build(root / 'motion', back=False)            # 매번 다시 만든다 — 데이터를 고친 뒤에도 바로 보이게
    handler = functools.partial(Quiet, directory=str(root))
    try:
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', int(opt['port'])), handler)
    except OSError:                               # 포트를 쓰고 있으면 빈 포트로
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    url = f'http://127.0.0.1:{srv.server_address[1]}/motion/'
    print(f'KB 모션 메뉴 → {url}  (끄기 Ctrl-C · 사용법은 motion.py help)', flush=True)
    if not opt.get('no-open'): webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main(sys.argv[1:])

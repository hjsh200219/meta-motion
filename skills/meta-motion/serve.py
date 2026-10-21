#!/usr/bin/env python3
"""KB 모션 메뉴(kb.pilldoc.co.kr/motion/)를 로컬에서 띄운다 — `python3 motion.py`(인자 없음)가 부른다. 표준 라이브러리만 쓴다.
export_kb.py 와 같은 페이지(원본 영상 모드)를 캐시 폴더에 만들고 127.0.0.1 에서 열어 둔다. Ctrl-C 로 끈다.
실행: python3 serve.py [--port 8765] [--no-open] [--out <폴더>] [--local]
  --local  SSH 로 붙은 사용자 PC 브라우저용 — 이 Mac 의 Tailscale 주소에도 띄운다(같은 Tailscale 계정 기기만 · 2시간 쉬면 꺼짐).
           마지막 줄 LOCAL_URL= 이 PC 에서 열 주소, LOCAL_BROWSER= 가 짝지은 PC 크롬(SKILL.md 대로 Claude 가 연다)."""
import http.server, os, sys, threading, webbrowser
from pathlib import Path
from export_kb import build
import localnet

OUT = Path.home() / '.cache' / 'meta-motion' / 'kb'


class Quiet(http.server.SimpleHTTPRequestHandler):
    gate = None                                   # localnet.Gate — 들어온 기기·Host 머리글 검사

    def log_message(self, *a): pass               # 요청마다 찍히는 줄로 터미널을 덮지 않는다

    def _ok(self):
        if self.gate is None or self.gate.allowed(self.client_address[0], self.headers.get('Host')): return True
        self.send_error(403, 'Invalid local request'); return False

    def do_GET(self):                             # noqa: N802
        if self._ok(): super().do_GET()

    def do_HEAD(self):                            # noqa: N802
        if self._ok(): super().do_HEAD()


def handler(root, gate):
    return type('H', (Quiet,), {'gate': gate, '__init__': lambda self, *a, **k: Quiet.__init__(self, *a, directory=str(root), **k)})


def main(argv):
    if os.name == 'nt':                           # cp949 콘솔·파이프에서 한글·기호가 깨지지 않게
        for s in (sys.stdout, sys.stderr):
            try: s.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, ValueError): pass
    opt = {'port': '8765', 'out': str(OUT)}; it = iter(argv)
    for a in it:
        if a in ('--no-open', '--local'): opt[a[2:]] = True
        elif a.startswith('--'): opt[a[2:]] = next(it, '')
    root = Path(opt['out'])
    build(root / 'motion', back=False)            # 매번 다시 만든다 — 데이터를 고친 뒤에도 바로 보이게
    port = int(opt['port'])
    if opt.get('local'): return serve_local(root, port)
    gate = localnet.Gate(port)
    try:
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler(root, gate))
    except OSError:                               # 포트를 쓰고 있으면 빈 포트로
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler(root, gate))
    gate.port = srv.server_address[1]
    url = f'http://127.0.0.1:{srv.server_address[1]}/motion/'
    print(f'KB 모션 메뉴 → {url}  (끄기 Ctrl-C · 사용법은 motion.py help)', flush=True)
    if not opt.get('no-open'): webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def serve_local(root, port):
    """127.0.0.1 + Tailscale IP 두 입구. 포트는 고정이어야 PC 가 늘 같은 주소로 연다 — 옛 화면 서버가 잡고 있으면 끄고 연다."""
    status = localnet.tailscale_status()
    why = localnet.refuse_reason(status)
    if why:
        print(f'--local 입구를 열지 않았습니다 — {why}', file=sys.stderr); return 1
    ip, dns, hosts, peers = localnet.allowlist(status)
    pidfile = str(root / 'serve.pid')
    port = localnet.pick_port(port, pidfile)
    if port is None:
        print('포트를 열 수 없습니다 — --port 로 바꿔 주세요', file=sys.stderr); return 1
    localnet.claim(pidfile, port)
    gate = localnet.Gate(port, hosts, peers)
    servers = [http.server.ThreadingHTTPServer(('127.0.0.1', port), handler(root, gate)),
               http.server.ThreadingHTTPServer((ip, port), handler(root, gate))]
    localnet.idle_watch(gate, servers)
    threading.Thread(target=servers[1].serve_forever, daemon=True).start()
    url = f'http://{dns or ip}:{port}/motion/'
    print(f'내 PC 에서 열기: {localnet.osc8(url)}  (같은 Tailscale 계정 기기만 · 2시간 쉬면 꺼짐)', flush=True)
    dev = localnet.pc_browser()
    if dev: print(f'LOCAL_BROWSER={dev}', flush=True)
    print(f'LOCAL_URL={url}', flush=True)
    try:
        servers[0].serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

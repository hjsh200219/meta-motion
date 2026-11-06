"""공식 안내 이미지 받기 — `python3 motion.py official <페이지 URL> --out <폴더> [--screens-only]`.

사용법 안내 영상에 실제 앱 화면이 필요할 때 미러링·화면 녹화·기기 조작 대신 그 서비스 회사의 공식 지원 문서
(support.apple.com 등)에 실린 화면 이미지를 쓴다(2026-11-07 사용자 지시). 페이지의 <img> 를 alt 문구와 함께 받아
`official.json`(페이지·받은 날·이미지마다 url·alt·kind·file)에 남긴다. alt 는 그 화면이 무엇인지 공식 문서가 적은 설명이라
장면 배치와 보고의 출처로 쓴다. 표준 라이브러리만 쓴다.
"""
import datetime, html as htmlmod, ipaddress, json, os, re, socket, sys, urllib.parse, urllib.request

UA = 'Mozilla/5.0 (Macintosh) meta-motion-official/1'
# 서비스 회사가 직접 운영하는 지원·도움말 도메인(끝이 일치하면 공식) — 아니면 경고만 하고 받는다
OFFICIAL = ('support.apple.com', 'developer.apple.com', 'apple.com', 'support.google.com', 'developers.google.com',
            'cs.kakao.com', 'help.naver.com', 'help.instagram.com', 'faq.whatsapp.com', 'support.microsoft.com',
            'learn.microsoft.com', 'help.netflix.com', 'support.samsung.com', 'samsung.com')

IMG_RE = re.compile(r'<img\b[^>]*>', re.I | re.S)
ATTR_RE = re.compile(r'''([\w-]+)\s*=\s*("([^"]*)"|'([^']*)')''', re.S)
STRIP_RE = re.compile(r'<(script|style|noscript)\b.*?</\1\s*>', re.I | re.S)


def is_official(url):
    host = (urllib.parse.urlsplit(url).hostname or '').lower()
    return any(host == d or host.endswith('.' + d) for d in OFFICIAL)


def _attrs(tag):
    return {m.group(1).lower(): htmlmod.unescape(m.group(3) if m.group(3) is not None else m.group(4))
            for m in ATTR_RE.finditer(tag)}


def parse_images(page_html, page_url):
    """페이지의 이미지 목록 — 절대 주소, 같은 주소는 처음 것만, data:·비콘·script 안 문자열은 뺀다."""
    body = STRIP_RE.sub('', page_html)
    out, seen = [], set()
    for tag in IMG_RE.findall(body):
        a = _attrs(tag)
        src = a.get('src') or a.get('data-src') or ''
        if not src or src.startswith('data:'):
            continue
        url = urllib.parse.urljoin(page_url, src)
        if urllib.parse.urlsplit(url).scheme not in ('http', 'https'):
            continue
        path = urllib.parse.urlsplit(url).path.lower()
        name = path.rsplit('/', 1)[-1]
        if url in seen or 'beacon' in name or 'pixel' in name or not re.search(r'\.(png|jpe?g|webp|gif|svg)$', path):
            continue
        seen.add(url)
        kind = 'icon' if 'icon' in path else 'screen'
        out.append({'url': url, 'alt': (a.get('alt') or '').strip(), 'kind': kind})
    return out


def file_names(imgs):
    return ['%02d-%s' % (i + 1, urllib.parse.unquote(urllib.parse.urlsplit(m['url']).path.rsplit('/', 1)[-1]))
            for i, m in enumerate(imgs)]


MAX_BYTES = 20 * 1024 * 1024


def _resolve(host):
    try:
        return [ai[4][0] for ai in socket.getaddrinfo(host, None)]
    except OSError:
        return []


def safe_url(url, resolve=None):
    """http(s) 이고, 호스트의 모든 주소가 공인 주소일 때만 참 — 페이지가 심은 file:·내부망·클라우드 메타데이터 주소를 막는다."""
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ('http', 'https') or not u.hostname:
        return False
    try:
        addrs = [str(ipaddress.ip_address(u.hostname))]
    except ValueError:
        addrs = (resolve or _resolve)(u.hostname) or []
    if not addrs:
        return False
    try:
        return all(ipaddress.ip_address(a.split('%')[0]).is_global for a in addrs)
    except ValueError:
        return False


def read_capped(fp, limit=MAX_BYTES):
    data = fp.read(limit + 1)
    if len(data) > limit:
        raise ValueError('응답이 %d바이트를 넘음' % limit)
    return data


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl):
            raise ValueError('안전하지 않은 리다이렉트: %s' % newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _get(url):
    if not safe_url(url):
        raise ValueError('받지 않음(공인 http(s) 주소 아님): %s' % url)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.build_opener(_SafeRedirect).open(req, timeout=30) as r:
        return read_capped(r)


def save(page_url, page_html, out_dir, get=_get, today=None, screens_only=False):
    imgs = parse_images(page_html, page_url)
    if screens_only:
        imgs = [m for m in imgs if m['kind'] == 'screen']
    os.makedirs(out_dir, exist_ok=True)
    for m, name in zip(imgs, file_names(imgs)):
        with open(os.path.join(out_dir, name), 'wb') as f:
            f.write(get(m['url']))
        m['file'] = name
    rec = {'page': page_url, 'official': is_official(page_url),
           'fetched': today or datetime.date.today().isoformat(), 'images': imgs}
    with open(os.path.join(out_dir, 'official.json'), 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return rec


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(__doc__.strip()); return
    url, out, screens = argv[0], 'official', '--screens-only' in argv
    if '--out' in argv:
        out = argv[argv.index('--out') + 1]
    if not is_official(url):
        print('경고: 공식 지원 도메인이 아님 — %s (그 회사가 운영하는 페이지인지 확인)' % url, file=sys.stderr)
    rec = save(url, _get(url).decode('utf-8', 'replace'), out, screens_only=screens)
    for m in rec['images']:
        print('%s\t%s\t%s' % (m['file'], m['kind'], m['alt'] or '(alt 없음)'))
    print('이미지 %d장 → %s/official.json' % (len(rec['images']), out))


if __name__ == '__main__':
    main(sys.argv[1:])

"""official.py 검사 — python3 test_official.py (네트워크 없음)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import official

PAGE = 'https://support.apple.com/ko-kr/118242'
HTML = '''<html><body>
<img src="/beacon.png" alt="">
<img class="icon" src="https://cdsassets.apple.com/live/x/images/inline-icons/ios-17-app-store-account-icon.png" alt="">
<figure><img src="https://cdsassets.apple.com/live/x/images/ios/locale/ko-kr/ios-27-iphone-17-pro-app-store-name-redeem-code-callout.png"
  alt="App Store의 Apple 계정 페이지에 &#x27;코드 사용&#x27; 버튼이 하이라이트되어 있는 iPhone 화면."></figure>
<img src="https://cdsassets.apple.com/live/x/images/ios/locale/ko-kr/ios-27-iphone-17-pro-app-store-name-redeem-code-callout.png" alt="중복">
<img data-src="//cdn.example.com/a/b/screen-2.jpg?w=640" alt="두 번째 화면">
<img src="data:image/png;base64,AAAA" alt="인라인">
<script>var s = '<img src="/x.png">'</script>
</body></html>'''

imgs = official.parse_images(HTML, PAGE)
urls = [i['url'] for i in imgs]
# 상대 경로·// 경로를 절대 주소로, 같은 주소는 한 번, data: 와 script 안 문자열은 빼고, 비콘(빈 alt·beacon)은 뺀다
assert urls == [
    'https://cdsassets.apple.com/live/x/images/inline-icons/ios-17-app-store-account-icon.png',
    'https://cdsassets.apple.com/live/x/images/ios/locale/ko-kr/ios-27-iphone-17-pro-app-store-name-redeem-code-callout.png',
    'https://cdn.example.com/a/b/screen-2.jpg?w=640',
], urls
# alt 는 HTML 엔티티를 풀어 그대로 — 화면 설명이자 출처 확인용
assert imgs[1]['alt'].startswith("App Store의 Apple 계정 페이지에 '코드 사용'"), imgs[1]['alt']
# 아이콘 판정: 경로에 icon 이 들어가면 kind=icon, 나머지는 screen
assert [i['kind'] for i in imgs] == ['icon', 'screen', 'screen']

# 파일 이름: 순번 + 주소 마지막 이름(질의 문자열 제거) — 겹치지 않는다
names = official.file_names(imgs)
assert names == ['01-ios-17-app-store-account-icon.png',
                 '02-ios-27-iphone-17-pro-app-store-name-redeem-code-callout.png',
                 '03-screen-2.jpg'], names

# 기록(official.json): 페이지·받은 날·이미지마다 url·alt·kind·file — 다운로드 함수는 바꿔 끼워 네트워크 없이 검사
with tempfile.TemporaryDirectory() as d:
    got = []
    def fake_get(url):
        got.append(url)
        return b'\x89PNG fake'
    rec = official.save(PAGE, HTML, d, get=fake_get, today='2026-11-07')
    assert got == urls
    assert rec['page'] == PAGE and rec['fetched'] == '2026-11-07' and len(rec['images']) == 3
    assert all(os.path.exists(os.path.join(d, i['file'])) for i in rec['images'])
    on_disk = json.load(open(os.path.join(d, 'official.json'), encoding='utf-8'))
    assert on_disk == rec
    # --screens-only 는 아이콘을 받지 않는다
    got.clear()
    rec2 = official.save(PAGE, HTML, d, get=fake_get, today='2026-11-07', screens_only=True)
    assert [i['kind'] for i in rec2['images']] == ['screen', 'screen'] and len(got) == 2

# 공식 출처 판정: 도메인 허용 목록(그 회사 지원 문서) — 아니면 경고 문구를 돌려준다(막지는 않는다)
assert official.is_official('https://support.apple.com/ko-kr/118242')
assert official.is_official('https://support.google.com/googleplay/answer/3422659?hl=ko')
assert official.is_official('https://cs.kakao.com/helps?service=8')
assert not official.is_official('https://blog.naver.com/someone/123')

# 안전: http(s) 만, 내부망·루프백·링크 로컬 호스트는 거절(페이지가 file:·내부 주소를 심어도 받지 않는다)
evil = '<img src="file:///etc/passwd.png" alt="a"><img src="ftp://x.com/a.png" alt="b"><img src="https://ok.example.com/a.png" alt="c">'
assert [i['url'] for i in official.parse_images(evil, PAGE)] == ['https://ok.example.com/a.png']
resolve = {'cdsassets.apple.com': ['17.253.1.1'], 'evil.test': ['127.0.0.1'], 'meta.test': ['169.254.169.254'],
           'lan.test': ['10.0.0.5'], 'mixed.test': ['17.1.1.1', '192.168.0.2']}.get
assert official.safe_url('https://cdsassets.apple.com/a.png', resolve=resolve)
for bad in ('http://evil.test/a.png', 'http://meta.test/latest', 'https://lan.test/a.png', 'https://mixed.test/a.png',
            'file:///etc/passwd', 'http://127.0.0.1/a.png', 'http://[::1]/a.png', 'https://unknown.test/a.png'):
    assert not official.safe_url(bad, resolve=resolve), bad
# 너무 큰 응답은 자른 채 쓰지 않고 실패
try:
    official.read_capped(__import__('io').BytesIO(b'x' * 11), limit=10); raise SystemExit('cap 실패')
except ValueError:
    pass
assert official.read_capped(__import__('io').BytesIO(b'x' * 10), limit=10) == b'x' * 10

# DNS 재바인딩: 검사 뒤 이름이 내부 주소로 바뀌어도, 실제로 붙은 상대 주소를 다시 봐서 끊는다 — 로컬 서버로 확인
import http.server, threading
srv = http.server.HTTPServer(('127.0.0.1', 0), http.server.SimpleHTTPRequestHandler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
try:
    official._opener().open('http://127.0.0.1:%d/' % srv.server_address[1], timeout=5)
    raise SystemExit('루프백 상대에 붙었는데 끊지 않음')
except Exception as e:
    assert '공인' in str(e), e
finally:
    srv.shutdown()

print('test_official OK')

#!/usr/bin/env python3
"""prompt-motion.com 갤러리(Claude 로 만든 모션 영상 + 그 프롬프트)를 받아 data/prompt_motion.json 을 다시 만든다.
사이트 robots: /api/ 금지 · Content-Signal use=reference — 항목 페이지만 1초 간격으로 읽고, 항목마다 만든 사람·원문 링크를 남긴다."""
import html, json, re, sys, time, urllib.request
from pathlib import Path

BASE = 'https://prompt-motion.com'
OUT = Path(__file__).resolve().parent / 'data' / 'prompt_motion.json'
UA = {'User-Agent': 'motion-prompt-plugin/1 (internal reference)'}
NOT_ENTRY = {'templates', 'customize', 'blog', 'tags', 'submit'}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode('utf-8')


def text(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s.replace('<!-- -->', ''))).strip()


def parse(slug, page):
    body = re.sub(r'<script(?![^>]*ld\+json).*?</script>', '', page, flags=re.S)
    ld = json.loads(html.unescape(re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S).group(1)))
    prompt = re.search(r'<div id="entry-prompt"[^>]*>(.*?)</div>', body, re.S)
    kind = re.search(r'<h2 class="text-xs font-medium text-muted-foreground">(\w+)</h2>', body)
    src = re.search(r'(?:taken directly from|from)<!-- --> <a href="([^"]+)"', body)
    meta = {text(k): text(v) for k, v in re.findall(r'<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', body, re.S)}
    cr = ld.get('creator') or {}
    kind = kind.group(1) if kind else ''
    if kind == 'Skill':  # 스킬 항목은 프롬프트 대신 설명 + 설치 명령 + repo
        sk = body[body.find('>Skill</h2>'):]
        desc, cmd = re.search(r'<p[^>]*>(.*?)</p>', sk, re.S), re.search(r'<code[^>]*>(.*?)</code>', sk, re.S)
        repo = re.search(r'<a href="([^"]+)"[^>]*>View repo', sk)
        body_txt = '\n'.join(x for x in [text(desc.group(1)) if desc else '', f'설치: {text(cmd.group(1))}' if cmd else '',
                                         f'repo: {repo.group(1)}' if repo else ''] if x)
    else:
        body_txt = html.unescape(prompt.group(1)) if prompt else ''
    return {
        'id': slug, 'title': ld.get('name', ''), 'type': kind,
        'tags': list(dict.fromkeys(re.findall(r'href="/tags/([\w-]+)"', body))),
        'prompt': body_txt,
        'creator': cr.get('name', ''), 'creator_url': cr.get('url', ''), 'source': src.group(1) if src else '',
        'model': meta.get('Model', ''), 'effort': meta.get('Effort', ''), 'iterations': meta.get('Iterations', ''), 'posted': ld.get('uploadDate', ''),
        'url': f'{BASE}/{slug}', 'video': ld.get('contentUrl', ''), 'poster': (ld.get('thumbnailUrl') or [''])[0], 'size': f"{ld.get('width', '')}x{ld.get('height', '')}",
    }


def main():
    urls = [html.unescape(u) for u in re.findall(r'<loc>([^<]+)</loc>', get(BASE + '/sitemap.xml'))]
    slugs = [u.rstrip('/').rsplit('/', 1)[1] for u in urls if u.count('/') == 3 and u.rstrip('/') != BASE]
    slugs = [s for s in slugs if s not in NOT_ENTRY]
    rows, bad = [], []
    for i, s in enumerate(slugs):
        try:
            r = parse(s, get(f'{BASE}/{s}'))
            (rows if r['prompt'] else bad).append(r if r['prompt'] else s)
        except Exception as e:  # 한 항목 실패로 전체를 버리지 않는다 — 끝에서 비율로 판정
            bad.append(f'{s}: {e}')
        if i % 25 == 0: print(f'{i}/{len(slugs)}', file=sys.stderr)
        time.sleep(1)
    assert len(rows) >= 0.9 * len(slugs), f'파싱 {len(rows)}/{len(slugs)} — 사이트 구조가 바뀌었는지 확인: {bad[:5]}'
    rows.sort(key=lambda r: (r['posted'], r['id']), reverse=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'항목 {len(rows)}개 (본문 없음·실패 {len(bad)}개 {bad[:5]}) → {OUT}', file=sys.stderr)


if __name__ == '__main__':
    main()

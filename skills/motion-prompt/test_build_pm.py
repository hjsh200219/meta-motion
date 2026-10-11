#!/usr/bin/env python3
"""build_pm.parse 자체 점검 — 사이트 항목 페이지 모양을 줄인 두 가지(프롬프트·스킬). 실행: python3 test_build_pm.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pm import parse

LD = '<script type="application/ld+json">{"name":"T","uploadDate":"2026-09-26","contentUrl":"https://m/v.mp4","width":1920,"height":1080,"creator":{"name":"A","url":"https://x.com/a"}}</script>'
TAGS = '<a href="/tags/charts">Charts</a><a href="/tags/code">Code</a><a href="/tags/charts">x</a>'
META = '<dl><dt>Model</dt><dd>Opus 5.5</dd><dt>Iterations</dt><dd>One-shot</dd></dl>'

p = parse('a-1', LD + TAGS + '<h2 class="text-xs font-medium text-muted-foreground">Prompt</h2>'
          '<div id="entry-prompt" class="x">Make &lt;inputs&gt; &amp; go</div><script>evil()</script>'
          'taken directly from<!-- --> <a href="https://x.com/a/status/1">post</a>' + META)
assert p['prompt'] == 'Make <inputs> & go' and p['type'] == 'Prompt', p
assert p['tags'] == ['charts', 'code'] and p['source'] == 'https://x.com/a/status/1', p
assert p['model'] == 'Opus 5.5' and p['effort'] == '' and p['iterations'] == 'One-shot' and p['size'] == '1920x1080', p

s = parse('b-1', LD + TAGS + '<h2 class="text-xs font-medium text-muted-foreground">Skill</h2><p class="y">Does &amp; renders.</p>'
          '<div><code class="z">npx skills add o/r</code></div><a href="https://github.com/o/r" class="w">View repo</a>')
assert s['type'] == 'Skill' and s['prompt'] == 'Does & renders.\n설치: npx skills add o/r\nrepo: https://github.com/o/r', s
print('ok')

#!/usr/bin/env python3
"""meta-motion 카탈로그 하나 — 모션(요청 카드·실전 예시·HyperFrames 레지스트리)·표현 기법(cokacmotion)·색·서체 템플릿을
출처 구분 없이 같은 꼴의 항목으로 돌려준다. 원본 자료 파일은 그대로 두고(출처별 갱신·라이선스·KB 내보내기 유지) 여기서 읽어 맞춘다.

항목 꼴: id · aliases(예전 코드·번호) · kind(motion|technique|theme) · title · summary · when · tags · category ·
actions(할 수 있는 동작: show·fields·order·add·recommend·theme) · provenance(source·url·creator·license·commit) ·
brand(남의 제품·계정 흉내) · size(고정 크기, 없으면 None) · search(찾기용 소문자 글)."""
import functools
import animskills, cokac, fonts, hf, motion

KIND_NAME = {'motion': '모션', 'technique': '기법', 'theme': '템플릿'}
SOURCE_NAME = {'card': '요청 카드', 'prompt-motion': '실전 예시', 'hyperframes': '레지스트리', 'animation-skills': '애니메이션 스킬', 'cokacmotion': '기법', 'templates': '템플릿'}


def _search(*parts):
    return ' '.join(str(p) for p in parts if p).lower()


def _motion(c):
    src = c.get('src', 'card')
    prov = {'source': 'card', 'url': 'https://nondev-thinking.web.app/motion/', 'creator': '한국경영교육연구소 AI ACADEMY', 'license': ''}
    size, brand, actions = None, False, ['show', 'fields', 'order', 'recommend']
    if src == 'pm':
        e = motion._EX[c['code']]
        prov = {'source': 'prompt-motion', 'url': e['url'], 'creator': e['creator'], 'license': '만든 사람 소유 — 참고만'}
    elif src == 'hf':
        it = hf.ITEMS[c['code']]
        prov = {'source': 'hyperframes', 'url': f"{hf.REG['source']}/{c['code']}", 'creator': 'HeyGen', 'license': hf.license_of(c['code'])}
        d = it.get('dimensions')
        size, brand, actions = ((d['width'], d['height']) if d else None), hf.brand_of(c['code']), actions + ['add']
    elif src == 'as':  # 원본 스킬이 1080x1920 고정으로 렌더한다
        idx = animskills.load()
        prov = {'source': 'animation-skills', 'url': f"{idx['source']}/tree/{idx['commit'][:7]}/skills/{c['skill']}", 'creator': idx['creator'], 'license': idx['license'], 'commit': idx['commit']}
        size = tuple(idx['size'])
    return {'id': c['code'], 'aliases': [], 'kind': 'motion', 'title': c['name'], 'summary': c['plain'], 'when': c['when'],
            'tags': list(c.get('inds') or []), 'category': c['cat'], 'actions': actions, 'provenance': prov, 'brand': brand, 'size': size,
            'search': _search(c['code'], c['name'], c.get('en'), c['plain'], c['when'], c['cat'], *(c.get('inds') or []), prov['creator']), 'src': src}


def _technique(d, idx):
    return {'id': d['id'], 'aliases': [str(d['number'])], 'kind': 'technique', 'title': d['title'], 'summary': d['tech'], 'when': d['scene'],
            'tags': list(d['libraries']), 'category': d['group'], 'actions': ['show'], 'brand': False, 'size': None,
            'provenance': {'source': 'cokacmotion', 'url': f"{idx['source']}/demos/{d['id']}", 'creator': 'kstost', 'license': idx['license'], 'commit': idx['commit']},
            'search': _search(d['id'], d['title'], d['tech'], d['group'], d['scene'], *d['points'], *d['libraries'], '기법')}


def _theme(k, t):
    return {'id': k, 'aliases': [], 'kind': 'theme', 'title': t['name'], 'summary': t['color'], 'when': t.get('criteria', ''),
            'tags': [t['tone']], 'category': t['tone'], 'actions': ['show', 'theme'], 'brand': False, 'size': None,
            'provenance': {'source': 'templates', 'url': '', 'creator': 'meta-motion', 'license': '', 'basis': t.get('source', '')},
            'search': _search(k, t['name'], t['color'], t['tone'], t.get('criteria'), '템플릿 색 서체')}


@functools.lru_cache(maxsize=1)
def _all():
    idx = cokac.load()
    out = [_motion(c) for c in motion.everything()] + [_technique(d, idx) for d in idx['items']] + [_theme(k, t) for k, t in fonts.TEMPLATES.items()]
    seen = {}
    for i in out:  # id·별칭이 겹치면 찾기가 모호해진다 — 만들 때 막는다
        for key in [i['id'], *i['aliases']]:
            assert key not in seen, f'카탈로그 id 겹침: {key} ({seen[key]} · {i["kind"]})'
            seen[key] = i['kind']
    return tuple(out)


def items(kind=None):
    return [i for i in _all() if not kind or i['kind'] == kind]


def search(words, kind=None):
    qs = [w.lower() for w in words]
    return [i for i in items(kind) if all(q in i['search'] for q in qs)]


def find(key):
    return next((i for i in _all() if key == i['id'] or key in i['aliases']), None)


def label(i):
    """한 줄 꼬리표 — 목록·찾기에서 종류와 출처를 보인다(사용자는 출처를 몰라도 되지만 표기는 남긴다)."""
    p = i['provenance']
    tail = {'prompt-motion': f" · {p['creator']}", 'hyperframes': f" · {p['license']}", 'animation-skills': ' · MIT'}.get(p['source'], '')
    return f"[{KIND_NAME[i['kind']]} · {SOURCE_NAME[p['source']]}{tail}{' · ⚠브랜드 흉내' if i['brand'] else ''}]"


def line(i):
    return f"{i['id']}\t{i['title']}\t{i['category']}\t{i['summary'][:70]}\t{label(i)}"

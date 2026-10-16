#!/usr/bin/env python3
"""fonts.py 점검(네트워크 없음) — 템플릿 글자 대비·서체 파일·라이선스·키워드 대체 경로. 실행: python3 test_fonts.py"""
import os
import tempfile
TMP = tempfile.mkdtemp()
os.environ["META_MOTION_HISTORY"] = os.path.join(TMP, "history.jsonl")   # 사용자 실제 이력을 건드리지 않는다
from fonts import (CATALOG, FONT_DIR, FONTS, TEMPLATE_MIN_CONF, TEMPLATES, TONE_TEMPLATE, choose_template, load_history,
                   pick, record, series_template)


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def cr(a, b):
    a, b = sorted([lum(a), lum(b)], reverse=True)
    return (a + 0.05) / (b + 0.05)


KEYS = {"name", "tone", "font", "caption_font", "title_scale", "band", "bg", "text", "sub", "accent", "accent_shape", "on_accent",
        "stroke", "chip", "photo", "source", "criteria", "color"}
assert len(TEMPLATES) >= 18
for tid, t in TEMPLATES.items():
    assert set(t) == KEYS, (tid, set(t) ^ KEYS)
    assert t["font"] in CATALOG and t["caption_font"] in CATALOG and t["tone"] in FONTS, tid
    assert t["caption_font"] not in ("gasoek-one", "black-han-sans", "nanum-brush"), (tid, "장식 서체는 자막에서 뭉개진다")
    # 제목 글자는 그 글자가 실제로 놓이는 면(상자 > 외곽선 > 띠)과 잰다
    under = t["chip"] or t["stroke"] or t["band"]
    assert under, f"{tid}: 띠·상자·외곽선이 모두 없다"
    assert cr(t["text"], under) >= 7, (tid, "제목", round(cr(t["text"], under), 2))
    assert cr(t["accent"], under) >= 4.5, (tid, "강조 글자", round(cr(t["accent"], under), 2))
    assert cr(t["on_accent"], t["accent_shape"]) >= 3, (tid, "강조 면 위 글자", round(cr(t["on_accent"], t["accent_shape"]), 2))
    if not t["photo"]:
        assert cr(t["sub"], t["bg"]) >= 4.5, (tid, "보조 글자", round(cr(t["sub"], t["bg"]), 2))
    else:
        assert t["stroke"], f"{tid}: 사진 위 글자는 외곽선이 필요하다"
assert set(TONE_TEMPLATE) == set(FONTS) and set(TONE_TEMPLATE.values()) <= set(TEMPLATES)
assert len({t["font"] for t in TEMPLATES.values()}) >= 10                 # 템플릿마다 서체도 다양하게

# 서체 파일과 라이선스 파일이 모두 있다
for fid, f in CATALOG.items():
    assert os.path.exists(os.path.join(FONT_DIR, f["file"])), (fid, f["file"])
    family = f["file"].split("-")[0]                                     # Pretendard-Black.otf → OFL-Pretendard.txt
    assert os.path.exists(os.path.join(FONT_DIR, f"OFL-{family}.txt")), (fid, family)

# 템플릿 결정: 지정 > Jev(확신 ≥ 문턱) > 분위기 기본 · 기본이 제외 목록이면 Jev 답 유지
assert TEMPLATE_MIN_CONF == 0.6
assert choose_template("white-red", "navy-lime", 0.99, "info") == ("white-red", "user")
assert choose_template(None, "navy-lime", 0.6, "info") == ("navy-lime", "jev")
assert choose_template(None, "navy-lime", 0.59, "info") == ("light-teal", "low-confidence")
assert choose_template(None, "navy-lime", 0.3, "info", exclude=("light-teal",)) == ("navy-lime", "jev")
assert choose_template(None, None, 0.0, "casual") == ("yellow-black", "tone-default")

# Jev 없이(키워드 판정) 분위기 기본 템플릿으로 떨어진다 · 지정이 판정보다 우선한다
r = pick("신고 절차와 수수료 안내", use_jev=False)
assert r["judge"] == "keyword" and r["template"] == TONE_TEMPLATE[r["tone"]] and r["palette"] == TEMPLATES[r["template"]]
r = pick("아무 글", use_jev=False, template_id="navy-lime")
assert r["template"] == "navy-lime" and r["file"] == CATALOG[TEMPLATES["navy-lime"]["font"]]["file"]
r = pick("아무 글", use_jev=False, template_id="navy-lime", font_id="jua")
assert r["template"] == "navy-lime" and r["file"] == CATALOG["jua"]["file"] and r["caption_font"]["file"] == CATALOG["jua"]["file"]
with tempfile.TemporaryDirectory() as d:                                  # 제목·자막 서체가 모두 작업 폴더로 복사된다
    r = pick("성수에서 줄 서는 신상", use_jev=False, template_id="black-neon", copy_to=d)
    assert os.path.exists(r["file_path"]) and os.path.exists(r["caption_font"]["file_path"])
    assert r["file"] != r["caption_font"]["file"]

# 이력: 시리즈 일치 > 비슷한 이전 영상(확신 ≥ 문턱) > Jev 템플릿 · 사용자 제외는 이력보다 앞선다
assert choose_template(None, "navy-lime", 0.99, "info", series_hit=("ai-daily-1", "black-red")) == ("black-red", "series:ai-daily-1")
assert choose_template(None, "navy-lime", 0.99, "info", similar=("pc-1", "white-red", 0.6)) == ("white-red", "similar:pc-1")
assert choose_template(None, "navy-lime", 0.99, "info", similar=("pc-1", "white-red", 0.59)) == ("navy-lime", "jev")
assert choose_template(None, "navy-lime", 0.99, "info", exclude=("black-red",), series_hit=("a", "black-red")) == ("navy-lime", "jev")
assert choose_template("light-teal", None, 0, "info", series_hit=("a", "black-red")) == ("light-teal", "user")
assert load_history() == []                                                # 원장이 없으면 빈 이력 · 기존 동작 그대로
record("ai-daily-1", "black-red", "오늘의 AI 소식 첫째", title="AI 데일리 1", series="ai-daily")
record("pc-1", "white-red", "필첵 복약 알림 소개", title="필첵 알림")
record("ai-daily-1", "navy-lime", "다시 렌더", title="AI 데일리 1", series="ai-daily")   # 같은 slug 는 마지막 기록
h = load_history()
assert [r["slug"] for r in h] == ["pc-1", "ai-daily-1"] and h[-1]["template"] == "navy-lime"
assert series_template("ai-daily", h) == ("ai-daily-1", "navy-lime") and series_template("other", h) is None
r = pick("오늘의 AI 소식 둘째", use_jev=False, series="ai-daily")      # 시리즈 일치는 Jev 없이 정해진다
assert r["template"] == "navy-lime" and r["template_how"] == "series:ai-daily-1"
print('ok')

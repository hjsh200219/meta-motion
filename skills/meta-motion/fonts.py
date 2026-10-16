#!/usr/bin/env python3
"""스크립트 분위기에 맞는 한글 폰트와 색 팔레트를 고른다(표준 라이브러리만 사용).

분위기 네 가지와 서체(모두 무료 OFL, 저장소 `data/fonts/`):
- info     : 정보·안내·절차·규정·숫자 중심 → Noto Sans KR (가변, 기본값)
- casual   : 밝고 짧은 쇼츠·이벤트·홍보 톤 → Do Hyeon 도현 (굵은 고딕)
- emotional: 감성·에세이·추억·위로 톤 → Nanum Myeongjo 나눔명조 (명조)
- playful  : 일상·친구·간식·귀여운 톤 → Gaegu 개구 (손글씨체)

글꼴 파일 경로는 이 스크립트 위치 기준이다(`data/fonts/`). 렌더러가 file:// 로 읽을 수 있게
영상 작업 폴더에 복사해서 쓴다(`copy_to` 인자 — 아래 `pick` 결과의 `file` 참고).

사용:
  python3 fonts.py pick script.txt        # 스크립트 파일의 분위기와 폰트 JSON
  python3 fonts.py pick - < script.txt    # 표준입력
  python3 fonts.py list                    # 분위기별 폰트 표
  python3 fonts.py pick script.txt --tone emotional   # 분위기 직접 지정(자동 판정 무시)

규칙: 분위기는 Jev choice 로 판정하고, 실패하면 키워드 출현 횟수가 가장 많은 분위기(동점·0건이면 info).
같은 분위기로 색 팔레트(PALETTES)도 정해 결과의 `palette` 에 담는다 — `palette.color` 를 motion.py `--color` 로 넘긴다.
사용자가 폰트를 직접 지정하면 그 지정이 자동 판정보다 우선한다.
"""
import json
import os
import shutil
import sys

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fonts")

FONTS = {
    "info": {"family": "MMInfo", "name": "Noto Sans KR", "weight": 700, "file": "NotoSansKR-VF.ttf", "weight_range": "100 900"},
    "casual": {"family": "MMCasual", "name": "Do Hyeon (도현)", "weight": 400, "file": "DoHyeon-Regular.ttf", "weight_range": "400 400"},
    "emotional": {"family": "MMEmotional", "name": "Nanum Myeongjo (나눔명조)", "weight": 400, "file": "NanumMyeongjo-Regular.ttf", "weight_range": "400 400"},
    "playful": {"family": "MMPlayful", "name": "Gaegu (개구)", "weight": 400, "file": "Gaegu-Regular.ttf", "weight_range": "400 400"},
}

# 대체 서체 카탈로그(무료 OFL). --font <id> 로 분위기 기본값 대신 고른다.
CATALOG = {
    "noto-sans-kr": {"tone": "info", "family": "MMNotoSansKR", "name": "Noto Sans KR", "weight": 700, "file": "NotoSansKR-VF.ttf", "weight_range": "100 900"},
    "ibm-plex-kr": {"tone": "info", "family": "MMIBMPlexKR", "name": "IBM Plex Sans KR", "weight": 400, "file": "IBMPlexSansKR-Regular.ttf", "weight_range": "400 400"},
    "do-hyeon": {"tone": "casual", "family": "MMDoHyeon", "name": "Do Hyeon (도현)", "weight": 400, "file": "DoHyeon-Regular.ttf", "weight_range": "400 400"},
    "bagel-fat-one": {"tone": "casual", "family": "MMBagel", "name": "Bagel Fat One (베이글)", "weight": 400, "file": "BagelFatOne-Regular.ttf", "weight_range": "400 400"},
    "nanum-myeongjo": {"tone": "emotional", "family": "MMNanumMyeongjo", "name": "Nanum Myeongjo (나눔명조)", "weight": 400, "file": "NanumMyeongjo-Regular.ttf", "weight_range": "400 400"},
    "song-myung": {"tone": "emotional", "family": "MMSongMyung", "name": "Song Myung (송명)", "weight": 400, "file": "SongMyung-Regular.ttf", "weight_range": "400 400"},
    "hahmlet": {"tone": "emotional", "family": "MMHahmlet", "name": "Hahmlet (함렛)", "weight": 400, "file": "Hahmlet-VF.ttf", "weight_range": "100 900"},
    "nanum-gothic": {"tone": "info", "family": "MMNanumGothic", "name": "Nanum Gothic (나눔고딕, 네이버)", "weight": 400, "file": "NanumGothic-Regular.ttf", "weight_range": "400 400"},
    "nanum-pen": {"tone": "playful", "family": "MMNanumPen", "name": "Nanum Pen Script (나눔펜, 네이버)", "weight": 400, "file": "NanumPenScript-Regular.ttf", "weight_range": "400 400"},
    "gaegu": {"tone": "playful", "family": "MMGaegu", "name": "Gaegu (개구)", "weight": 400, "file": "Gaegu-Regular.ttf", "weight_range": "400 400"},
    "single-day": {"tone": "playful", "family": "MMSingleDay", "name": "Single Day (싱글데이)", "weight": 400, "file": "SingleDay-Regular.ttf", "weight_range": "400 400"},
    "poor-story": {"tone": "playful", "family": "MMPoorStory", "name": "Poor Story (푸어스토리)", "weight": 400, "file": "PoorStory-Regular.ttf", "weight_range": "400 400"},
    "stylish": {"tone": "playful", "family": "MMStylish", "name": "Stylish (스타일리시)", "weight": 400, "file": "Stylish-Regular.ttf", "weight_range": "400 400"},
}

KEYWORDS = {
    "info": ["신고", "절차", "수수료", "서류", "규정", "법", "조건", "기준", "안내", "시설", "등록",
             "기간", "이내", "원", "번호", "신청", "확인", "요건", "의무", "조항", "%"],
    "casual": ["신나", "할인", "이벤트", "오픈", "축제", "꿀팁", "필수", "대박", "최고", "지금", "!",
               "쇼츠", "무료", "혜택", "특가", "런칭"],
    "emotional": ["마음", "사랑", "추억", "따뜻", "감사", "이야기", "여행", "계절", "그리움", "위로",
                  "감성", "행복", "기억", "함께", "노을", "바람", "안녕"],
    "playful": ["귀여", "친구", "놀이", "웃음", "재밌", "강아지", "고양이", "아이", "동네", "일상",
                "오늘은", "빵", "간식", "그림", "낙서", "냠냠"],
}


TONE_CRITERIA = {
    "info": "정보·안내·절차·규정·수치 중심. 설명서, 신고 방법, 조건과 금액을 차분히 전달하는 대본",
    "casual": "짧고 밝은 홍보·이벤트·쇼츠 톤. 힘 있는 훅, 혜택, 굵고 빠른 전달",
    "emotional": "감성·에세이·추억·위로 톤. 천천히 읽는 서정적 문장, 사람과 장소의 이야기",
    "playful": "일상·친구·간식·귀여운 톤. 가볍고 유쾌한 말투, 손글씨 느낌이 어울리는 대본",
}
JEV_PATH = os.path.expanduser("~/workspace/shared/jev.py")

# 분위기별 색 팔레트 — 서체와 같은 분위기 판정(Jev 한 번)으로 함께 고른다. 영상 하나에 팔레트 하나.
# 색을 정하지 않으면 매번 짙은 남색(#1d3557 등)으로 굳던 문제(2026-10-17)를 막는 기본값이다.
# bg 배경 · surface 카드·상자 · text 본문 글자 · sub 보조 글자 · accent 강조 면·선(화살표·버튼·밑줄·큰 숫자)
# on_accent 강조 면 위 글자. 글자 대비(2026-10-17 계산): text/bg 10.8~13.7 · sub/bg 4.1~6.3 · on_accent/accent 3.4~5.3.
# accent/bg 는 2.1~3.5 라 강조색으로 본문 글자를 쓰지 않는다(면·선·굵은 큰 숫자만).
PALETTES = {
    "info": {"name": "밝은 회백", "bg": "#F5F7FA", "surface": "#FFFFFF", "text": "#1F2937", "sub": "#6B7280", "accent": "#0D9488", "on_accent": "#FFFFFF",
             "color": "밝은 회백 바탕에 짙은 회색 글자, 청록 포인트"},
    "casual": {"name": "선명한 노랑", "bg": "#FFD84D", "surface": "#FFFFFF", "text": "#1A1A1A", "sub": "#4B4B4B", "accent": "#FF4D2E", "on_accent": "#1A1A1A",
               "color": "선명한 노랑 바탕에 검정 글자, 주홍 포인트"},
    "emotional": {"name": "따뜻한 베이지", "bg": "#F3E9DC", "surface": "#FFF8EE", "text": "#3B2F2A", "sub": "#7A6A5F", "accent": "#C2794D", "on_accent": "#FFFFFF",
                  "color": "따뜻한 베이지 바탕에 진갈색 글자, 테라코타 포인트"},
    "playful": {"name": "연분홍 파스텔", "bg": "#FFE4EC", "surface": "#FFFFFF", "text": "#3A2E39", "sub": "#7D6B7A", "accent": "#2BB5A0", "on_accent": "#3A2E39",
                "color": "연분홍 파스텔 바탕에 진보라 회색 글자, 민트 포인트"},
}


def judge_tone_jev(text):
    """Jev choice 로 분위기를 고른다. (tone, confidence) 를 돌려주고, 실패하면 None 을 돌려준다.
    API 키는 jev.py 가 환경변수·workspace .env 에서 스스로 읽는다(이 파일은 키를 다루지 않는다)."""
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("jev_client", JEV_PATH)
        jev = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(jev)
        questions = {"tone": jev.choice(
            "이 영상 대본(장면 제목과 내레이션)의 전달 분위기를 하나만 고른다. 대본 내용과 말투로 판단한다.",
            TONE_CRITERIA)}
        answers = jev.ask(text, questions, timeout_s=60)
        tone, conf = jev.choice_of(answers, "tone")
        if tone in FONTS:
            return tone, conf
    except Exception as e:  # 네트워크·키·import 실패는 키워드 판정으로 물러난다
        sys.stderr.write(f"fonts.py: Jev 판정 실패, 키워드 판정으로 대체 ({type(e).__name__})\n")
    return None


def judge_tone(text):
    """키워드 출현 횟수가 가장 많은 분위기. 동점·0건이면 info."""
    scores = {tone: sum(text.count(k) for k in words) for tone, words in KEYWORDS.items()}
    best = max(scores.values())
    if best == 0:
        return "info", scores
    winners = [t for t, s in scores.items() if s == best]
    if "info" in winners:
        return "info", scores
    return winners[0], scores


USER_FONT_DIR = os.path.expanduser("~/Library/Fonts")
HF_INLINE_LIMIT = 2 * 1024 * 1024  # HyperFrames 는 2MB 넘는 글꼴을 묶음에 넣지 않아 기본 서체로 대체된다(2026-10-16 실측)
SUBSET_BASE = "0123456789.,:;!?()[]-~·•✓%/+& ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def subset_font(src, dst, text):
    """영상에 쓰는 글자만 남긴 부분 글꼴을 만든다(fontTools 필요). 만든 파일 크기를 돌려준다."""
    from fontTools import subset
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    font = subset.load_font(src, opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=text + SUBSET_BASE)
    sub.subset(font)
    subset.save_font(font, dst, opts)
    return os.path.getsize(dst)


def ensure_installed(files=None):
    """data/fonts 의 서체를 ~/Library/Fonts 에 설치한다(없거나 크기가 다르면 복사). 설치한 파일 목록을 돌려준다."""
    names = files or sorted({f["file"] for f in FONTS.values()} | {f["file"] for f in CATALOG.values()})
    os.makedirs(USER_FONT_DIR, exist_ok=True)
    installed = []
    for name in names:
        src = os.path.join(FONT_DIR, name)
        dst = os.path.join(USER_FONT_DIR, name)
        if not os.path.exists(src):
            raise SystemExit(f"글꼴 원본이 없습니다: {src}")
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
            shutil.copyfile(src, dst)
            installed.append(name)
    return installed


def pick(text, tone=None, copy_to=None, font_id=None, use_jev=True):
    """분위기와 서체 정보. font_id 를 주면 카탈로그에서 그 서체를 쓴다(분위기는 서체의 분위기로 정한다).
    분위기 자동 판정은 Jev(choice)가 맡고, 실패하거나 use_jev=False 면 키워드 판정을 쓴다.
    copy_to 디렉터리를 주면 글꼴 파일을 거기로 복사하고 file_path 를 돌려준다."""
    judge, confidence = "keyword", None
    jev_result = judge_tone_jev(text) if use_jev and not tone and not font_id else None
    if jev_result:
        auto_tone, confidence = jev_result
        judge = "jev"
        scores = {}
    else:
        auto_tone, scores = judge_tone(text)
    if font_id:
        if font_id not in CATALOG:
            raise SystemExit(f"알 수 없는 서체: {font_id} (python3 fonts.py list 로 확인)")
        font = CATALOG[font_id]
        chosen = font["tone"]
    else:
        chosen = tone or auto_tone
        if chosen not in FONTS:
            raise SystemExit(f"알 수 없는 분위기: {chosen} (info | casual | emotional | playful)")
        font = FONTS[chosen]
    src = os.path.join(FONT_DIR, font["file"])
    if not os.path.exists(src):
        raise SystemExit(f"글꼴 파일이 없습니다: {src}")
    newly = ensure_installed([font["file"]])  # 서체가 사용자 폰트 폴더에 없으면 설치
    out = {"tone": chosen, "auto_tone": auto_tone, "judge": judge, "confidence": confidence, "installed_now": newly,
           "scores": scores, **font, "src": src, "palette": PALETTES[chosen]}
    if copy_to:
        os.makedirs(copy_to, exist_ok=True)
        dst = os.path.join(copy_to, font["file"])
        shutil.copyfile(src, dst)
        if os.path.getsize(dst) > HF_INLINE_LIMIT:
            # 2MB 를 넘으면 HyperFrames 가 묶지 않는다 → 대본 글자만 남긴 부분 글꼴로 바꾼다
            stem = os.path.splitext(font["file"])[0]
            sub = os.path.join(copy_to, f"{stem}-subset.ttf")
            size = subset_font(src, sub, text)
            if size > HF_INLINE_LIMIT:
                raise SystemExit(f"부분 글꼴도 2MB 를 넘습니다({size} bytes): {sub}")
            os.remove(dst)
            dst = sub
        out["file_path"] = dst
    return out


def main(argv):
    if len(argv) < 2 or argv[1] not in ("pick", "list", "install"):
        print(__doc__)
        return 2
    if argv[1] == "install":
        done = ensure_installed()
        print(json.dumps({"dir": USER_FONT_DIR, "installed": done, "total": len(set(f["file"] for f in CATALOG.values()) | set(f["file"] for f in FONTS.values()))}, ensure_ascii=False))
        return 0
    if argv[1] == "list":
        print("분위기 기본값:")
        for tone, f in FONTS.items():
            c = PALETTES[tone]
            print(f"  {tone:10s} {f['name']} · 색 {c['name']} (bg {c['bg']} · 글자 {c['text']} · 강조 {c['accent']})")
        print("카탈로그 (--font 로 지정):")
        for fid, f in CATALOG.items():
            print(f"  {fid:15s} [{f['tone']}] {f['name']}")
        return 0
    tone = None
    font_id = None
    if "--tone" in argv:
        tone = argv[argv.index("--tone") + 1]
    if "--font" in argv:
        font_id = argv[argv.index("--font") + 1]
    use_jev = "--keyword" not in argv
    flags = {"--tone", "--font"}
    args = [a for i, a in enumerate(argv[2:], 2)
            if a not in flags and a != "--keyword" and argv[i - 1] not in flags]
    src = args[0] if args else "-"
    text = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    print(json.dumps(pick(text, tone, font_id=font_id, use_jev=use_jev), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

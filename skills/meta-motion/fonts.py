#!/usr/bin/env python3
"""스크립트에 맞는 한글 서체와 색 조합 템플릿을 고른다(표준 라이브러리만 사용, Jev 는 선택).

분위기 네 가지 기본 서체(모두 무료 OFL, 저장소 `data/fonts/` · 라이선스 `OFL-*.txt`):
- info     : 정보·안내·절차·규정·숫자 중심 → Noto Sans KR (가변, 기본값)
- casual   : 밝고 짧은 쇼츠·이벤트·홍보 톤 → Do Hyeon 도현 (굵은 고딕)
- emotional: 감성·에세이·추억·위로 톤 → Nanum Myeongjo 나눔명조 (명조)
- playful  : 일상·친구·간식·귀여운 톤 → Gaegu 개구 (손글씨체)

색·서체 템플릿 18종(TEMPLATES): 조회 수 높은 국내 쇼츠·릴스의 제목 띠·글자·강조색을 실측해 만든 조합.
템플릿마다 서체가 정해져 있어 영상마다 색과 서체가 함께 바뀐다(`python3 fonts.py list`).

글꼴 파일 경로는 이 스크립트 위치 기준이다(`data/fonts/`). 렌더러가 file:// 로 읽을 수 있게
영상 작업 폴더에 복사해서 쓴다(`copy_to` 인자 — 아래 `pick` 결과의 `file` 참고).

사용:
  python3 fonts.py pick script.txt        # 분위기·템플릿·서체 JSON (palette = 고른 템플릿의 색)
  python3 fonts.py pick - < script.txt    # 표준입력
  python3 fonts.py list                    # 분위기 기본값·템플릿·서체 카탈로그
  python3 fonts.py pick script.txt --tone emotional          # 분위기 지정(Jev 안 부르고 그 분위기 기본 템플릿)
  python3 fonts.py pick script.txt --template navy-lime      # 템플릿 지정
  python3 fonts.py pick script.txt --series ai-daily         # 같은 시리즈 이력이 있으면 그 템플릿(Jev 안 부름)
  python3 fonts.py pick script.txt --exclude black-yellow    # 특정 템플릿을 후보에서 뺀다(쉼표로 여러 개)
  python3 fonts.py record script.txt --slug <id> --template <id> [--title 제목] [--series 시리즈] [--published URL]
                                                              # 렌더가 끝난 영상을 템플릿 이력에 남긴다
  python3 fonts.py history [N]                               # 최근 이력(기본 200건) · --history <파일> 로 원장 바꾸기
  python3 fonts.py pick script.txt --font jua                # 서체만 바꾼다

규칙: 같은 시리즈 이력이 있으면 그 템플릿을 그대로 쓴다. 없으면 Jev 한 번(choice 세 문항 — 분위기·템플릿·비슷한 이전 영상)으로
고르고, 비슷한 이전 영상이 확신 0.6 이상이면 그 영상의 템플릿을 쓴다. Jev 가 실패하면 키워드로 분위기를 정하고
(동점·0건이면 info) 그 분위기의 기본 템플릿을 쓴다. 사용자가 템플릿·서체를 지정하면 그 지정이 우선한다.
"""
import json
import os
import shutil
import sys
import time

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
    # 2026-10-17 추가 — 인기 쇼츠 제목의 굵은 고딕·붓글씨 계열(모두 OFL, 라이선스 data/fonts/OFL-*.txt)
    "pretendard-black": {"tone": "casual", "family": "MMPretendardBlack", "name": "Pretendard Black (프리텐다드)", "weight": 900, "file": "Pretendard-Black.otf", "weight_range": "900 900"},
    "pretendard-extrabold": {"tone": "info", "family": "MMPretendardXB", "name": "Pretendard ExtraBold (프리텐다드)", "weight": 800, "file": "Pretendard-ExtraBold.otf", "weight_range": "800 800"},
    "gothic-a1-black": {"tone": "casual", "family": "MMGothicA1", "name": "Gothic A1 Black (고딕 A1)", "weight": 900, "file": "GothicA1-Black.ttf", "weight_range": "900 900"},
    "black-han-sans": {"tone": "casual", "family": "MMBlackHanSans", "name": "Black Han Sans (검은고딕)", "weight": 400, "file": "BlackHanSans-Regular.ttf", "weight_range": "400 400"},
    "gasoek-one": {"tone": "casual", "family": "MMGasoek", "name": "Gasoek One (가석)", "weight": 400, "file": "GasoekOne-Regular.ttf", "weight_range": "400 400"},
    "jua": {"tone": "playful", "family": "MMJua", "name": "Jua (주아)", "weight": 400, "file": "Jua-Regular.ttf", "weight_range": "400 400"},
    "sunflower": {"tone": "info", "family": "MMSunflower", "name": "Sunflower Bold (해바라기)", "weight": 700, "file": "Sunflower-Bold.ttf", "weight_range": "700 700"},
    "nanum-brush": {"tone": "emotional", "family": "MMNanumBrush", "name": "Nanum Brush Script (나눔손글씨 붓)", "weight": 400, "file": "NanumBrushScript-Regular.ttf", "weight_range": "400 400"},
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

# 색·서체 조합 템플릿 — 조회 수 높은 국내 쇼츠·릴스의 제목 띠·자막을 실측해 만든 것(2026-10-17).
# 실측: 유튜브 17개 채널 쇼츠 탭 조회 수 상위 3개 + 주제 검색 16개(90초 이하 한국어) 53편의 50% 지점 프레임에서
#       위 띠(높이 3~24%)·가운데·아래 띠(76~97%)의 최빈 색 중앙값과 채도 높은 강조색을 쟀다. 인스타그램은
#       스브스뉴스 릴스 격자·탐색 탭 화면을 눈으로 본 정성 자료다(조회 수 순위 아님).
# 키: band 제목 띠 · bg 화면 바탕 · text 제목·자막 글자 · sub 보조 글자 · accent 강조 단어 글자
#     · accent_shape 강조 면(알약·밑줄·화살표·번호) · on_accent 강조 면 위 글자 · stroke 글자 외곽선(사진 위 글자일 때)
#     · chip 제목을 담는 상자(없으면 띠 위에 바로) · font 제목 서체 · caption_font 자막·보조 서체(CATALOG id)
#     · title_scale 제목 글자 크기 배율(획이 가는 붓글씨는 키운다) · photo 사진·영상이 바탕인지
# 가석·검은고딕처럼 획이 꽉 찬 장식 서체는 자막 크기에서 뭉개진다(2026-10-17 시안 렌더 확인) → 자막은 본문용 서체로 둔다.
# 대비 기준(test_fonts.py 가 검사): 제목 글자/띠 ≥ 7 · 강조 글자/띠 ≥ 4.5 · 보조 글자/바탕 ≥ 4.5 · 강조 면 위 글자 ≥ 3
#   (외곽선이 있으면 띠 대신 외곽선 색과 잰다 · chip 이 있으면 chip 과 잰다).
# 영상 하나에 템플릿 하나. 장면마다 바꾸지 않는다.
TEMPLATES = {
    "black-yellow": {"name": "검정 띠 · 노랑 강조", "tone": "casual", "font": "pretendard-black", "caption_font": "pretendard-black", "title_scale": 1.0,
                     "band": "#000000", "bg": "#0B0B0B", "text": "#FFFFFF", "sub": "#D4D4D4", "accent": "#FCCB00",
                     "accent_shape": "#FCCB00", "on_accent": "#000000", "stroke": None, "chip": None, "photo": False,
                     "source": "MMTG 문명특급(220만·170만) 위 띠 #000000·강조 #FCCB00 · 14F 일사에프 #FBDD6F · 닥터프렌즈 #FDEE02",
                     "criteria": "토크·인터뷰·연예·교양 이야기, 질문으로 여는 훅, 사람 이야기를 빠르게 전하는 대본",
                     "color": "검정 제목 띠에 흰 글자, 강조 단어는 노랑"},
    "black-red": {"name": "검정 띠 · 빨강 강조", "tone": "casual", "font": "gothic-a1-black", "caption_font": "gothic-a1-black", "title_scale": 1.0,
                  "band": "#000000", "bg": "#0B0B0B", "text": "#FFFFFF", "sub": "#D4D4D4", "accent": "#FF3B30",
                  "accent_shape": "#FF3B30", "on_accent": "#FFFFFF", "stroke": None, "chip": None, "photo": False,
                  "source": "슈카월드(410만·180만·170만) 위 띠 #000000 · 강조 빨강·노랑 #FBF96F",
                  "criteria": "경제·주식·돈·업계 비밀처럼 놀라운 사실을 폭로하듯 전하는 대본, 금액과 숫자가 핵심",
                  "color": "검정 제목 띠에 흰 글자, 강조 단어는 빨강"},
    "navy-lime": {"name": "남색 띠 · 라임 강조", "tone": "info", "font": "pretendard-extrabold", "caption_font": "pretendard-extrabold", "title_scale": 1.0,
                  "band": "#020238", "bg": "#08125C", "text": "#FFFFFF", "sub": "#C7CCF0", "accent": "#C9FE3A",
                  "accent_shape": "#8FD3FF", "on_accent": "#020238", "stroke": None, "chip": None, "photo": False,
                  "source": "스브스뉴스(520만·200만·180만) 위 띠 #020238·아래 #08125C·강조 #C9FE3A · 인스타 릴스 표지 하늘색 강조",
                  "criteria": "뉴스·사회 이슈·시사·세대 이야기, 사건과 현상을 기사처럼 정리하는 대본",
                  "color": "짙은 남색 제목 띠에 흰 글자, 강조 단어는 라임"},
    "deepgreen-mint": {"name": "짙은 초록 · 민트 강조", "tone": "info", "font": "pretendard-extrabold", "caption_font": "pretendard-extrabold", "title_scale": 1.0,
                       "band": "#00302C", "bg": "#00302C", "text": "#FFFFFF", "sub": "#BFE3DA", "accent": "#3BFFC6",
                       "accent_shape": "#3BFFC6", "on_accent": "#00302C", "stroke": None, "chip": None, "photo": False,
                       "source": "닥터딩요(130만) 위·아래 띠 #00302C·강조 #3BFFC6",
                       "criteria": "의학·건강·약·질병 정보, 의사·약사가 알려 주는 증상과 주의점",
                       "color": "짙은 초록 바탕에 흰 글자, 강조 단어는 민트"},
    "forest-yellow": {"name": "숲 초록 · 노랑 강조", "tone": "playful", "font": "jua", "caption_font": "jua", "title_scale": 1.0,
                      "band": "#1E4530", "bg": "#1E4530", "text": "#FFFFFF", "sub": "#D5E8DC", "accent": "#FFEE01",
                      "accent_shape": "#FFEE01", "on_accent": "#1E4530", "stroke": None, "chip": None, "photo": False,
                      "source": "사물궁이 잡학지식(13만) 위·아래 띠 #1E4530·강조 #FFEE01",
                      "criteria": "과학·잡학 궁금증을 그림과 함께 풀어 주는 대본, '~하면 어떻게 될까?' 질문형",
                      "color": "숲 초록 바탕에 흰 글자, 강조 단어는 노랑"},
    "charcoal-orange": {"name": "숯 회색 · 주황 강조", "tone": "info", "font": "black-han-sans", "caption_font": "pretendard-extrabold", "title_scale": 1.0,
                        "band": "#171717", "bg": "#171717", "text": "#FFFFFF", "sub": "#CFCFCF", "accent": "#FF8A3D",
                        "accent_shape": "#FF8A3D", "on_accent": "#171717", "stroke": None, "chip": None, "photo": False,
                        "source": "1분만(140만·110만) 위·아래 띠 #171717 · 본문 강조 #D15311",
                        "criteria": "생활 상식·법·제도·하면 안 되는 것을 1분 안에 짧게 알려 주는 how-to 대본",
                        "color": "숯 회색 띠에 흰 글자, 강조 단어는 주황"},
    "black-neon": {"name": "검정 · 형광 연두", "tone": "casual", "font": "gasoek-one", "caption_font": "pretendard-extrabold", "title_scale": 1.0,
                   "band": "#000000", "bg": "#000000", "text": "#FFFFFF", "sub": "#D4D4D4", "accent": "#A0FE21",
                   "accent_shape": "#A0FE21", "on_accent": "#000000", "stroke": None, "chip": None, "photo": False,
                   "source": "무신사 TV(27만·23만·17만) 위 띠 #000000·강조 #A0FE21",
                   "criteria": "패션·쇼핑·브랜드·트렌드·신상품 소개, 젊고 힙한 말투",
                   "color": "검정 바탕에 흰 글자, 강조 단어는 형광 연두"},
    "night-purple": {"name": "밤 보라 · 붓글씨 노랑", "tone": "playful", "font": "nanum-brush", "caption_font": "sunflower", "title_scale": 1.3,
                     "band": "#1A0647", "bg": "#2A0059", "text": "#FFFFFF", "sub": "#D9CCF2", "accent": "#FFD84D",
                     "accent_shape": "#B454FC", "on_accent": "#FFFFFF", "stroke": None, "chip": None, "photo": False,
                     "source": "피식대학(190만·160만) 보라 조명 #1A0647·#2A0059 · 노랑 붓글씨 자막",
                     "criteria": "코미디·예능·노래·과장된 감정 연기, 웃기거나 오글거리는 이야기",
                     "color": "밤 보라 바탕에 흰 글자, 강조는 노랑 붓글씨"},
    "white-red": {"name": "흰 띠 · 빨강 강조", "tone": "info", "font": "black-han-sans", "caption_font": "pretendard-extrabold", "title_scale": 1.0,
                  "band": "#FFFFFF", "bg": "#FFFFFF", "text": "#111111", "sub": "#555555", "accent": "#E30613",
                  "accent_shape": "#E30613", "on_accent": "#FFFFFF", "stroke": None, "chip": None, "photo": False,
                  "source": "백종원(590만·180만·110만) 위·아래 띠 #FFFFFF·강조 #FD0002(대비 위해 #E30613 으로 낮춤)",
                  "criteria": "요리·레시피·맛집·살림 노하우, 재료와 분량을 또렷이 보여 주는 대본",
                  "color": "흰 제목 띠에 검정 글자, 강조 단어는 빨강"},
    "white-chip-yellow": {"name": "흰 바탕 · 검정 상자 · 노랑 강조", "tone": "playful", "font": "jua", "caption_font": "jua", "title_scale": 1.0,
                          "band": "#FFFFFF", "bg": "#F4F4F4", "text": "#FFFFFF", "sub": "#3C3C3C", "accent": "#FFE500",
                          "accent_shape": "#FFE500", "on_accent": "#2B2B2B", "stroke": None, "chip": "#2B2B2B", "photo": False,
                          "source": "사물궁이 잡학지식(15만·13만) 흰 그림 바탕 #FFFFFF·제목 상자 검정·강조 #FFEE01",
                          "criteria": "그림·도식으로 설명하는 상식, 어린이도 볼 만한 쉬운 과학·사회 설명",
                          "color": "흰 바탕에 검정 둥근 상자 제목, 흰 글자와 노랑 강조"},
    "lavender-coral": {"name": "연보라 · 다홍 강조", "tone": "emotional", "font": "pretendard-extrabold", "caption_font": "pretendard-extrabold", "title_scale": 1.0,
                       "band": "#E8E9F9", "bg": "#F6F7FB", "text": "#1F1F2E", "sub": "#4A4A5E", "accent": "#B5300A",
                       "accent_shape": "#F54105", "on_accent": "#FFFFFF", "stroke": None, "chip": None, "photo": False,
                       "source": "듣똑라(100만·17만) 위 띠 #E8E9F9·#F6F7FB·강조 #F54105(글자용은 #B5300A)",
                       "criteria": "시사 교양 대담, 사회·여성·세대 문제를 차분하게 묻고 답하는 대본",
                       "color": "연보라 바탕에 짙은 남회색 글자, 강조 단어는 다홍"},
    "studio-green-pill": {"name": "스튜디오 회색 · 초록 알약", "tone": "info", "font": "pretendard-extrabold", "caption_font": "pretendard-extrabold", "title_scale": 1.0,
                          "band": "#5A5756", "bg": "#6B6967", "text": "#FFFFFF", "sub": "#EDEDED", "accent": "#9CF0B8",
                          "accent_shape": "#1E9E4F", "on_accent": "#FFFFFF", "stroke": "#1E1E1E", "chip": None, "photo": True,
                          "source": "머니인사이드(290만·220만·190만) 회색 스튜디오 #5A5756 · 자막 초록 #40C46E",
                          "criteria": "전문가·교수 인터뷰, 경제·사회 해설 강의, 말하는 사람 얼굴이 중심인 대본",
                          "color": "회색 스튜디오 바탕, 흰 자막에 초록 알약 강조"},
    "photo-cyan-quiz": {"name": "사진 위 흰 글자 · 하늘 강조", "tone": "casual", "font": "pretendard-black", "caption_font": "pretendard-black", "title_scale": 1.0,
                        "band": None, "bg": "#222222", "text": "#FFFFFF", "sub": "#FFFFFF", "accent": "#34D6FE",
                        "accent_shape": "#00C853", "on_accent": "#0B0B0B", "stroke": "#000000", "chip": None, "photo": True,
                        "source": "토스(610만·280만·200만) 길거리 영상 위 흰 질문 글자·검정 외곽선·강조 #34D6FE",
                        "criteria": "퀴즈·길거리 인터뷰·Q&A, 금융·상식 문제를 내고 맞히는 대본",
                        "color": "영상 위 흰 글자에 검정 외곽선, 강조 단어는 하늘색"},
    "photo-yellow-stroke": {"name": "사진 위 노랑 굵은 글자", "tone": "casual", "font": "black-han-sans", "caption_font": "pretendard-black", "title_scale": 1.0,
                            "band": None, "bg": "#222222", "text": "#FFE500", "sub": "#FFFFFF", "accent": "#FF2A2A",
                            "accent_shape": "#FF2A2A", "on_accent": "#FFFFFF", "stroke": "#000000", "chip": None, "photo": True,
                            "source": "인스타그램 탐색 탭 릴스 표지(2026-10-17 화면) — 사진 위 노랑·빨강 굵은 글자 + 검정 외곽선",
                            "criteria": "화제·연예·충격 사연·TOP 순위, 사진 한 장으로 시선을 끄는 자극적인 훅",
                            "color": "사진 위 노랑 굵은 글자에 검정 외곽선, 강조 단어는 빨강"},
    "light-teal": {"name": "밝은 회백 · 청록", "tone": "info", "font": "noto-sans-kr", "caption_font": "noto-sans-kr", "title_scale": 1.0,
                   "band": "#F5F7FA", "bg": "#F5F7FA", "text": "#1F2937", "sub": "#4B5563", "accent": "#0F766E",
                   "accent_shape": "#0D9488", "on_accent": "#FFFFFF", "stroke": None, "chip": None, "photo": False,
                   "source": "기본 정보형(2026-10-17 초판) — 밝은 바탕 정보 영상용",
                   "criteria": "공공 안내·절차·규정·수수료처럼 차분히 읽어야 하는 정보, 기관·회사 공지",
                   "color": "밝은 회백 바탕에 짙은 회색 글자, 강조는 청록"},
    "yellow-black": {"name": "선명한 노랑 · 검정", "tone": "casual", "font": "do-hyeon", "caption_font": "do-hyeon", "title_scale": 1.0,
                     "band": "#FFD84D", "bg": "#FFD84D", "text": "#1A1A1A", "sub": "#3A3A3A", "accent": "#A50E25",
                     "accent_shape": "#FF4D2E", "on_accent": "#1A1A1A", "stroke": None, "chip": None, "photo": False,
                     "source": "기본 홍보형(2026-10-17 초판)",
                     "criteria": "가게·이벤트·할인·오픈 홍보, 짧고 밝게 혜택을 외치는 대본",
                     "color": "선명한 노랑 바탕에 검정 글자, 강조는 진빨강"},
    "beige-terracotta": {"name": "따뜻한 베이지 · 테라코타", "tone": "emotional", "font": "nanum-myeongjo", "caption_font": "nanum-myeongjo", "title_scale": 1.0,
                         "band": "#F3E9DC", "bg": "#F3E9DC", "text": "#3B2F2A", "sub": "#5E5048", "accent": "#9A4F25",
                         "accent_shape": "#C2794D", "on_accent": "#FFFFFF", "stroke": None, "chip": None, "photo": False,
                         "source": "기본 감성형(2026-10-17 초판)",
                         "criteria": "감성·에세이·추억·위로, 천천히 읽는 서정적 문장과 사람·장소 이야기",
                         "color": "따뜻한 베이지 바탕에 진갈색 글자, 강조는 테라코타"},
    "pastel-pink-mint": {"name": "연분홍 파스텔 · 민트", "tone": "playful", "font": "gaegu", "caption_font": "gaegu", "title_scale": 1.0,
                         "band": "#FFE4EC", "bg": "#FFE4EC", "text": "#3A2E39", "sub": "#5E4E5C", "accent": "#0A6658",
                         "accent_shape": "#2BB5A0", "on_accent": "#3A2E39", "stroke": None, "chip": None, "photo": False,
                         "source": "기본 귀여움형(2026-10-17 초판)",
                         "criteria": "일상·반려동물·간식·친구 이야기, 귀엽고 가벼운 말투",
                         "color": "연분홍 파스텔 바탕에 진보라 회색 글자, 강조는 민트"},
}
TONE_TEMPLATE = {"info": "light-teal", "casual": "yellow-black", "emotional": "beige-terracotta", "playful": "pastel-pink-mint"}


def load_jev():
    import importlib.util
    spec = importlib.util.spec_from_file_location("jev_client", JEV_PATH)
    jev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jev)
    return jev


def judge_jev(text, exclude=(), history=()):
    """Jev 한 번으로 분위기(tone)와 템플릿(template)을 함께 고른다. {"tone": (값, 확신), "template": (값, 확신)} 또는 None.
    exclude 에 든 템플릿은 후보에서 뺀다(사용자가 고른 수동 제외).
    history(이력 레코드 목록)가 있으면 같은 호출에 「비슷한 이전 콘텐츠」 문항을 더해 {"similar": (slug|"none", 확신)} 도 돌려준다.
    API 키는 jev.py 가 환경변수·workspace .env 에서 스스로 읽는다(이 파일은 키를 다루지 않는다)."""
    try:
        jev = load_jev()
        options = {k: v["criteria"] for k, v in TEMPLATES.items() if k not in exclude}
        questions = {
            "tone": jev.choice("이 영상 대본(장면 제목과 내레이션)의 전달 분위기를 하나만 고른다. 대본 내용과 말투로 판단한다.",
                               TONE_CRITERIA),
            "template": jev.choice("이 영상 대본의 주제·장르와 가장 잘 맞는 쇼츠 화면 스타일을 하나만 고른다. 대본이 다루는 분야와 전달 방식으로 판단한다.",
                                   options),
        }
        if history:
            past = {h["slug"]: f'{h.get("title") or ""} — {h.get("summary") or ""}'[:300] for h in history}
            past[NO_SIMILAR] = "비슷한 이전 콘텐츠 없음 — 주제·시리즈·형식이 다른 새 콘텐츠"
            questions["similar"] = jev.choice(
                "이 영상 대본과 주제·시리즈·형식이 같은 이전 영상이 있으면 그 영상을, 없으면 none 을 고른다. 단어 몇 개가 겹치는 정도로는 같다고 보지 않는다.",
                past)
        answers = jev.ask(text, questions, timeout_s=60)
        tone = jev.choice_of(answers, "tone")
        tpl = jev.choice_of(answers, "template")
        sim = jev.choice_of(answers, "similar") if history else (None, 0.0)
        if tone[0] in FONTS:
            return {"tone": tone, "template": tpl if tpl[0] in options else (None, 0.0),
                    "similar": sim if sim[0] in {h["slug"] for h in history} else (None, sim[1])}
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


# 템플릿 이력(2026-10-17 사용자 지시 「유사한 콘텐츠는 동일한 템플릿」 · 「이제부터 이력을 관리」 — 그 전 영상은 소급하지 않는다).
# 렌더가 성공한 영상마다 `fonts.py record` 로 한 줄 남긴다. pick 은 읽기만 한다(중단된 렌더가 이력을 더럽히지 않게).
# 저장소 밖(사용자 홈)에 둔다 — 이 스킬 repo 는 커밋이 곧 원격 게시라 대본 요약을 올리지 않는다. META_MOTION_HISTORY 로 바꾼다.
HISTORY_PATH = os.environ.get("META_MOTION_HISTORY") or os.path.expanduser("~/.local/share/meta-motion/template-history.jsonl")
HISTORY_LIMIT = 200  # Jev choice 옵션 상한 255 안
NO_SIMILAR = "none"


def summarize(text, n=200):
    return " ".join(text.split())[:n]


def load_history(path=None, limit=HISTORY_LIMIT):
    """최근 limit 건(같은 slug 는 마지막 기록만)."""
    path = path or HISTORY_PATH
    if not os.path.exists(path):
        return []
    rows = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            r = json.loads(line)
            rows.pop(r["slug"], None)
            rows[r["slug"]] = r
    return list(rows.values())[-limit:]


def record(slug, template, text="", title="", series=None, font=None, caption_font=None, published=None, path=None):
    """렌더가 끝난 영상 한 편의 템플릿을 이력에 남긴다. 같은 slug 를 다시 기록하면 load_history 가 마지막 것을 쓴다."""
    if template not in TEMPLATES:
        raise SystemExit(f"알 수 없는 템플릿: {template}")
    path = path or HISTORY_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    t = TEMPLATES[template]
    row = {"date": time.strftime("%Y-%m-%d %H:%M"), "slug": slug, "title": title, "series": series,
           "summary": summarize(text), "template": template, "font": font or t["font"],
           "caption_font": caption_font or t["caption_font"], "published": published}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def series_template(series, history):
    """같은 시리즈의 가장 최근 템플릿(결정론 — Jev 를 부르지 않는다)."""
    for h in reversed(history):
        if series and h.get("series") == series:
            return h["slug"], h["template"]
    return None


TEMPLATE_MIN_CONF = 0.6  # Jev 템플릿 확신도가 이보다 낮으면 분위기 기본 템플릿으로 대체(2026-10-17 사용자 지시)


def choose_template(template_id, jev_tpl, jev_conf, tone, exclude=(), series_hit=None, similar=None):
    """(템플릿 id, 고른 경로). 우선순위: 사용자 지정 > 같은 시리즈 이력 > 비슷한 이전 영상(Jev ≥ 문턱) > Jev 템플릿(≥ 문턱) > 분위기 기본.
    경로: user · series:<slug> · similar:<slug> · jev · low-confidence(확신 낮아 대체) · tone-default(Jev 없음).
    series_hit = (slug, 템플릿), similar = (slug, 템플릿, 확신). exclude 는 사용자가 뺀 템플릿이라 이력이 가리켜도 쓰지 않는다.
    대체할 기본 템플릿이 exclude 에 들면 Jev 답을 그대로 쓴다."""
    if template_id:
        return template_id, "user"
    if series_hit and series_hit[1] not in exclude:
        return series_hit[1], f"series:{series_hit[0]}"
    if similar and (similar[2] or 0) >= TEMPLATE_MIN_CONF and similar[1] not in exclude:
        return similar[1], f"similar:{similar[0]}"
    fallback = TONE_TEMPLATE[tone]
    if jev_tpl and (jev_conf or 0) >= TEMPLATE_MIN_CONF:
        return jev_tpl, "jev"
    if jev_tpl and fallback in exclude:
        return jev_tpl, "jev"
    if jev_tpl:
        return fallback, "low-confidence"
    return fallback, "tone-default"


def pick(text, tone=None, copy_to=None, font_id=None, use_jev=True, template_id=None, exclude=(), series=None, history_path=None):
    """분위기·색 템플릿·서체를 고른다.
    - 템플릿: template_id 지정 > Jev 판정(분위기와 같은 호출, 확신 ≥ TEMPLATE_MIN_CONF) > 분위기 기본 템플릿(TONE_TEMPLATE).
      그보다 앞서 이력(HISTORY_PATH)에서 같은 series 가 있으면 그 템플릿, 없으면 Jev 가 비슷하다고 본 이전 영상(확신 ≥ 문턱)의 템플릿.
      결과의 template_how 가 어느 경로였는지(user·series:·similar:·jev·low-confidence·tone-default), jev_template 이 Jev 원래 답이다.
    - 서체: font_id 지정 > 템플릿 서체(제목 `font` · 자막 `caption_font` — 결과의 caption_font 에 담는다).
    - 분위기: tone 지정 > Jev > 키워드 판정. tone 을 지정하면 Jev 를 부르지 않고 그 분위기의 기본 템플릿을 쓴다.
    exclude 에 든 템플릿은 Jev 후보에서 뺀다. copy_to 를 주면 글꼴 파일을 거기로 복사하고 file_path 를 돌려준다."""
    if template_id and template_id not in TEMPLATES:
        raise SystemExit(f"알 수 없는 템플릿: {template_id} (python3 fonts.py list 로 확인)")
    if font_id and font_id not in CATALOG:
        raise SystemExit(f"알 수 없는 서체: {font_id} (python3 fonts.py list 로 확인)")
    if tone and tone not in FONTS:
        raise SystemExit(f"알 수 없는 분위기: {tone} (info | casual | emotional | playful)")
    judge, confidence, tpl_conf = "keyword", None, None
    history = load_history(history_path)
    series_hit = series_template(series, history) if not template_id else None
    ask_similar = history if not series_hit else ()
    jev_result = judge_jev(text, exclude, ask_similar) if use_jev and not tone and not template_id else None
    similar = None
    if jev_result:
        auto_tone, confidence = jev_result["tone"]
        jev_tpl, tpl_conf = jev_result["template"]
        judge, scores = "jev", {}
        sim_slug, sim_conf = jev_result.get("similar", (None, 0.0))
        if sim_slug:
            similar = (sim_slug, next(h["template"] for h in history if h["slug"] == sim_slug), sim_conf)
    else:
        jev_tpl = None
        auto_tone, scores = judge_tone(text)
    chosen = tone or (CATALOG[font_id]["tone"] if font_id else None) or auto_tone
    tpl_id, tpl_how = choose_template(template_id, jev_tpl, tpl_conf, chosen, exclude, series_hit, similar)
    template = TEMPLATES[tpl_id]
    font = CATALOG[font_id or template["font"]]
    caption = CATALOG[font_id or template["caption_font"]]  # 서체를 지정하면 제목·자막 모두 그 서체
    src = font_src(font)
    newly = ensure_installed(sorted({font["file"], caption["file"]}))  # 서체가 사용자 폰트 폴더에 없으면 설치
    out = {"tone": chosen, "auto_tone": auto_tone, "judge": judge, "confidence": confidence,
           "template": tpl_id, "template_confidence": tpl_conf, "template_how": tpl_how, "jev_template": jev_tpl,
           "similar": {"slug": similar[0], "template": similar[1], "confidence": similar[2]} if similar else None,
           "installed_now": newly, "scores": scores,
           **font, "src": src, "palette": template,
           "caption_font": {**caption, "src": font_src(caption)}}
    if copy_to:
        out["file_path"] = copy_font(font, text, copy_to)
        out["caption_font"]["file_path"] = copy_font(caption, text, copy_to)
    return out


def font_src(font):
    src = os.path.join(FONT_DIR, font["file"])
    if not os.path.exists(src):
        raise SystemExit(f"글꼴 파일이 없습니다: {src}")
    return src


def copy_font(font, text, copy_to):
    """글꼴을 영상 작업 폴더로 복사한다. 2MB 를 넘으면 HyperFrames 가 묶지 않으므로 대본 글자만 남긴 부분 글꼴로 바꾼다."""
    src = font_src(font)
    os.makedirs(copy_to, exist_ok=True)
    dst = os.path.join(copy_to, font["file"])
    shutil.copyfile(src, dst)
    if os.path.getsize(dst) > HF_INLINE_LIMIT:
        stem, ext = os.path.splitext(font["file"])
        sub = os.path.join(copy_to, f"{stem}-subset{ext}")
        size = subset_font(src, sub, text)
        if size > HF_INLINE_LIMIT:
            raise SystemExit(f"부분 글꼴도 2MB 를 넘습니다({size} bytes): {sub}")
        os.remove(dst)
        dst = sub
    return dst


def opt(argv, name):
    return argv[argv.index(name) + 1] if name in argv else None


def main(argv):
    if len(argv) < 2 or argv[1] not in ("pick", "list", "install", "record", "history"):
        print(__doc__)
        return 2
    if argv[1] == "install":
        done = ensure_installed()
        print(json.dumps({"dir": USER_FONT_DIR, "installed": done, "total": len(set(f["file"] for f in CATALOG.values()) | set(f["file"] for f in FONTS.values()))}, ensure_ascii=False))
        return 0
    if argv[1] == "list":
        print("분위기 기본 서체·템플릿:")
        for tone, f in FONTS.items():
            print(f"  {tone:10s} {f['name']} · 템플릿 {TONE_TEMPLATE[tone]}")
        print("색·서체 템플릿 (--template 로 지정):")
        for tid, t in TEMPLATES.items():
            print(f"  {tid:20s} [{t['tone']}] {t['name']} · 띠 {t['band'] or '사진'} · 글자 {t['text']} · 강조 {t['accent']} · 서체 {t['font']}")
        print("카탈로그 (--font 로 지정):")
        for fid, f in CATALOG.items():
            print(f"  {fid:15s} [{f['tone']}] {f['name']}")
        return 0
    flags = {"--tone", "--font", "--template", "--exclude", "--series", "--history", "--slug", "--title", "--published", "--caption-font"}
    args = [a for i, a in enumerate(argv[2:], 2)
            if a not in flags and a != "--keyword" and argv[i - 1] not in flags]
    hist = opt(argv, "--history")
    if argv[1] == "history":
        rows = load_history(hist, limit=int(args[0]) if args else HISTORY_LIMIT)
        for r in rows:
            print(f"{r['date']}  {r['template']:20s} {r['slug']}" + (f"  [{r['series']}]" if r.get("series") else "") + f"  {r.get('title') or ''}")
        print(f"({len(rows)}건 · {hist or HISTORY_PATH})")
        return 0
    src = args[0] if args else "-"
    text = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    if argv[1] == "record":
        if not opt(argv, "--slug") or not opt(argv, "--template"):
            raise SystemExit("record 는 --slug 와 --template 이 필요하다")
        row = record(opt(argv, "--slug"), opt(argv, "--template"), text, title=opt(argv, "--title") or "",
                     series=opt(argv, "--series"), font=opt(argv, "--font"), caption_font=opt(argv, "--caption-font"),
                     published=opt(argv, "--published"), path=hist)
        print(json.dumps(row, ensure_ascii=False))
        return 0
    exclude = tuple(opt(argv, "--exclude").split(",")) if "--exclude" in argv else ()
    print(json.dumps(pick(text, opt(argv, "--tone"), font_id=opt(argv, "--font"), use_jev="--keyword" not in argv,
                          template_id=opt(argv, "--template"), exclude=exclude, series=opt(argv, "--series"),
                          history_path=hist), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

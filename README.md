# motion-prompt — 모션그래픽 요청 문장 사전 (Claude Code 플러그인)

영상·쇼츠·인트로를 만들 때 Claude 가 장면마다 맞는 모션그래픽 카드(152종)를 골라
그 «자세히» 사양 — 길이·장면 순서·볼거리 한 번·모양·움직임·하지 말 것 — 을 기준으로 만든다.
자막·장면 전환·로고 인트로·데이터 차트·3D·사진 배경·가게/행사/공지 안내·엔딩·구독 등.

출처: https://nondev-thinking.web.app/motion/ (한국경영교육연구소 AI ACADEMY «모션그래픽 주문 사전»), 2026-10-08 수집. 사내 참고용.
실전 예시: https://prompt-motion.com — Claude 로 만든 모션 영상의 프롬프트 230여 개(영어, 만든 사람·원문 링크 포함), 2026-10-11 수집. 사내 참고용 — 영상·프롬프트는 만든 사람 소유.

## 설치

```
claude plugin marketplace add hjsh200219/motion-prompt
claude plugin install motion-prompt@motion-prompt
```

- 비공개 repo — hjsh200219/motion-prompt 협업자(collaborator) 권한과 GitHub 로그인된 git 이 필요하다(확인: `git ls-remote https://github.com/hjsh200219/motion-prompt.git`).
- 필요한 것: Python 3 (표준 라이브러리만).
- 떠 있는 세션은 `/reload-plugins`. 업데이트: `claude plugin update motion-prompt@motion-prompt`

## 쓰는 법

- 그냥 «필첵 소개 쇼츠 만들어줘»처럼 영상을 요청하면 Claude 가 스킬을 불러 장면별 카드를 고르고, 쓴 카드 코드를 알려 준다.
- 프롬프트만 원하면 «로고 인트로 프롬프트 줘», «/motion-prompt:motion-prompt 켄 번스».
- 실전 예시: «prompt-motion 에서 차트 예시 보여줘» · 직접 `motion.py examples chart` → `example <id>`
- 화면으로 고르기: `skills/motion-prompt/preview.html` — 요청 카드 152개와 실전 예시(한국어 카드로 정리, 실제 영상의 한 장면 위에서 재생)를 한 목록에서 고르고, 장면 순서 재생·칸 채우기·요청 문장 복사. 같은 폴더의 `data/motion.json`·`prompt_motion.json`·`prompt_motion_ko.json`·`posters/` 를 읽는다 — Artifact 로 게시할 때는 이 파일들을 페이지 옆(`posters/` 포함)에 함께 올리고, 로컬에서는 `skills/motion-prompt` 에서 `python3 -m http.server` 를 띄워 `/preview.html` 을 연다(파일로 직접 열면 자료를 못 읽는다). 예시 정리는 `build_pm_ko.py`(edb-p 로 한국어 카드 변환, 영어 8단어 연속 베끼기 검사), 그림은 `fetch_posters.py`, Artifact 용 줄인 영상은 `fetch_posters.py --clips`(둘 다 git 제외 — Artifact 는 CSP 가 외부 영상을 막는다). 요청 카드 샘플은 `build_card_anim.py`(edb-p 가 카드 사양대로 HTML+CSS 애니메이션을 만들고, 스크립트·외부 주소 금지 검사 — 페이지가 격리 iframe 에 띄워 진행표 시각에 맞춘다, `data/anim/`, 검사·목록 그림은 `check_card_anim.mjs` → `data/anim/thumb/`). 사내 KB 페이지(https://kb.pilldoc.co.kr/motion/)는 `export_kb.py <PillDocKb>/site/motion` 으로 내보내며 원본 영상을 바로 연다. 보는 곳은 사내 KB https://kb.pilldoc.co.kr/motion/ (2026-10-12 결정 — 예전 비공개 Artifact https://claude.ai/artifact/8wfwMfKyM3HrRY92r3csFb 는 영상·요청 카드 샘플이 없는 옛 판으로 남겨 둠)
- 직접: `python3 skills/motion-prompt/motion.py search 자막` · `show I02 title=필첵 --ratio 세로` (전체 사용법은 인자 없이 실행)

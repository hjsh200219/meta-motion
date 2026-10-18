# meta-motion — 모션그래픽 요청 문장 사전 (Claude Code 플러그인)

> 2026-10-14 이름 변경: 옛 `motion-prompt`(repo·플러그인·스킬·폴더) → `meta-motion`. 옛 GitHub 주소는 자동 이동된다.

영상·쇼츠·인트로를 만들 때 Claude 가 장면마다 맞는 모션그래픽 카드(152종)를 골라
그 «자세히» 사양 — 길이·장면 순서·볼거리 한 번·모양·움직임·하지 말 것 — 을 기준으로 만든다.
자막·장면 전환·로고 인트로·데이터 차트·3D·사진 배경·가게/행사/공지 안내·엔딩·구독 등.

출처: https://nondev-thinking.web.app/motion/ (한국경영교육연구소 AI ACADEMY «모션그래픽 주문 사전»), 2026-10-08 수집. 사내 참고용.
실전 예시: https://prompt-motion.com — Claude 로 만든 모션 영상의 프롬프트 230여 개(영어, 만든 사람·원문 링크 포함), 2026-10-11 수집. 사내 참고용 — 영상·프롬프트는 만든 사람 소유.
HyperFrames 레지스트리: 렌더 엔진과 같은 repo(heygen-com/hyperframes, Apache-2.0)의 공식 블록·컴포넌트 444개(`data/hf_registry.json`). 444개 모두 요청 카드 분류 16개로 나누고(Jev) 같은 모양의 한국어 카드를 붙여(`data/hf_registry_ko.json`) `list`·`search`·`show`·`recommend`·미리보기 화면에 요청 카드·실전 예시와 한 목록으로 섞인다. 목록 그림은 항목마다 직접 렌더한 한 장면(`data/hf_thumb/`). `motion.py registry-add` 로 받으면 lint 를 통과하는 연결 조각과 세로·한글 서체로 고칠 곳을 알려 준다. 출처 미확인 자산이 든 3개는 뺐다.
색·서체 템플릿: 조회 수 높은 국내 쇼츠·릴스의 제목 띠·글자색·강조색을 실측한 조합 18종(`skills/meta-motion/fonts.py`) — 대본 주제로 Jev 가 하나를 고르고, 제목·자막 서체(무료 SIL OFL 21종, `data/fonts/`)가 함께 정해진다. 플러그인을 켜면 세션 시작 훅이 서체를 `~/Library/Fonts` 에 설치한다.

Claude Motion 과 합쳐 쓰기(2026-10-18): 렌더·MP4·내레이션은 HyperFrames 그대로, 검토는 claude.ai «Motion» 필름(렌더 클립을 장면마다 올려 긁어 보고 시각에 댓글)으로, 맞는 카드가 없는 장면(추천 1위 적합도 0.5 미만)만 Motion 안에서 `kit.scene` 으로 직접 그린 뒤 `data/motion_kit.js` 로 HyperFrames 하위 컴포지션에 옮긴다. 필름 기록은 `python3 skills/meta-motion/motion.py film rec.json --durs … --out film/` 이 만든다(SKILL.md 「Claude Motion 과 합쳐 쓰기」).

## 설치

```
claude plugin marketplace add hjsh200219/meta-motion
claude plugin install meta-motion@meta-motion
```

- 비공개 repo — hjsh200219/meta-motion 협업자(collaborator) 권한과 GitHub 로그인된 git 이 필요하다(확인: `git ls-remote https://github.com/hjsh200219/meta-motion.git`).
- 필요한 것: Python 3 (표준 라이브러리만).
- 떠 있는 세션은 `/reload-plugins`. 업데이트: `claude plugin update meta-motion@meta-motion`

## 쓰는 법

- 그냥 «필첵 소개 쇼츠 만들어줘»처럼 영상을 요청하면 Claude 가 스킬을 불러 장면별 카드를 고르고(첫 장면 인트로·마지막 장면 아웃트로는 항상 넣는다), 쓴 카드 코드를 알려 준다.
- 프롬프트만 원하면 «로고 인트로 프롬프트 줘», «/meta-motion:meta-motion 켄 번스».
- 비율 깃발: «/meta-motion -v 필첵 소개 쇼츠» = 세로 9:16, «/meta-motion -h 회사 소개 영상» = 가로 16:9. CLI 도 같다(`python3 skills/meta-motion/motion.py show I02 -v`).
- 실전 예시: «prompt-motion 에서 차트 예시 보여줘» · 직접 `motion.py examples chart` → `example <id>`
- 화면으로 고르기: `skills/meta-motion/preview.html` — 요청 카드 152개·실전 예시 233개(한국어 카드로 정리, 실제 영상의 한 장면 위에서 재생)·HyperFrames 레지스트리 444개(직접 렌더한 그림, KB 에서는 공식 미리보기 영상)를 분류별로 섞은 한 목록에서 고르고, 장면 순서 재생·칸 채우기·요청 문장 복사. 같은 폴더의 `data/motion.json`·`prompt_motion.json`·`prompt_motion_ko.json`·`hf_registry.json`·`hf_registry_ko.json`·`hf_thumb/`·`posters/` 를 읽는다 — Artifact 로 게시할 때는 이 파일들을 페이지 옆(`posters/` 포함)에 함께 올리고, 로컬에서는 `skills/meta-motion` 에서 `python3 -m http.server` 를 띄워 `/preview.html` 을 연다(파일로 직접 열면 자료를 못 읽는다). 예시 정리는 `build_pm_ko.py`(edb-p 로 한국어 카드 변환, 영어 8단어 연속 베끼기 검사), 그림은 `fetch_posters.py`, Artifact 용 줄인 영상은 `fetch_posters.py --clips`(둘 다 git 제외 — Artifact 는 CSP 가 외부 영상을 막는다). 스크립트 추천: `python3 skills/meta-motion/motion.py recommend 대본.txt` — 빈 줄로 나눈 장면마다 영상 비율에 못 쓰는 항목(세로면 가로 고정 레지스트리)을 빼고, 남은 후보 전체(요청 카드·실전 예시·레지스트리 섞어서)를 255개 이하 묶음별 결승으로 Jev 가 골라 3개씩 «적합도»(Jev 가 «이 장면을 이 모션으로 잘 보여 주나»에 답한 예 확률, 1위 0.5 미만은 확신 낮음)와 함께 보여 준다(기본 세로, `-h` 가로, `--json`). 2026-10-17 분류를 먼저 고르던 두 단계를 바꿔 게시된 릴스 대본 75장면 검증에서 심판(edb-p) 1위 평균 2.84 → 4.00 — 다시 재기는 `eval_recommend.py`(글이 api.typesafe.ai 로 나감, 필요: workspace `shared/jev.py`·`JEV_API_KEY`). 요청 카드 샘플은 `build_card_anim.py`(edb-p 가 카드 사양대로 HTML+CSS 애니메이션을 만들고, 스크립트·외부 주소 금지 검사 — 페이지가 격리 iframe 에 띄워 진행표 시각에 맞춘다, `data/anim/`, 검사·목록 그림은 `check_card_anim.mjs` → `data/anim/thumb/`). 사내 KB 페이지(https://kb.pilldoc.co.kr/motion/)는 `export_kb.py <PillDocKb>/site/motion` 으로 내보내며 원본 영상을 바로 연다. 보는 곳은 사내 KB https://kb.pilldoc.co.kr/motion/ (2026-10-12 결정 — 예전 비공개 Artifact https://claude.ai/artifact/8wfwMfKyM3HrRY92r3csFb 는 영상·요청 카드 샘플이 없는 옛 판으로 남겨 둠)
- 레지스트리: `python3 skills/meta-motion/motion.py registry 자막` → `show caption-pill-karaoke`(자세히 사양) → `registry-add caption-pill-karaoke --dir <HyperFrames 프로젝트>` (npx 필요 · 갱신 `build_hf.py` → `build_hf_ko.py` → `build_hf_thumbs.py`)
- 직접: `python3 skills/meta-motion/motion.py search 자막` · `show I02 title=필첵 --ratio 세로` (전체 사용법은 인자 없이 실행)

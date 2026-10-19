# meta-motion

영상·쇼츠·인트로를 만들 때 장면마다 맞는 모션그래픽을 골라 주는 Claude Code 플러그인입니다.
모션 829개를 같은 한국어 카드·같은 분류 16개로 한 목록에 모아 두고, 대본을 주면 장면별로 추천합니다.

```bash
python3 skills/meta-motion/motion.py     # 인자 없이 → 사내 KB 모션 메뉴를 로컬 브라우저로 연다
```

> 비공개 repo · 사내 참고용입니다. 수집 자료의 영상·프롬프트 저작권은 만든 사람에게 있습니다.

## 목차

- [설치](#설치)
- [빠른 시작](#빠른-시작)
- [명령 모음](#명령-모음)
- [들어 있는 자료](#들어-있는-자료)
- [Claude Motion 과 합쳐 쓰기](#claude-motion-과-합쳐-쓰기)
- [자료 다시 만들기](#자료-다시-만들기)

## 설치

```bash
claude plugin marketplace add hjsh200219/meta-motion
claude plugin install meta-motion@meta-motion
```

- 필요한 것: Python 3(표준 라이브러리만), 이 repo 협업자(collaborator) 권한, GitHub 로그인된 git
- 권한 확인: `git ls-remote https://github.com/hjsh200219/meta-motion.git`
- 업데이트: `claude plugin update meta-motion@meta-motion` → 떠 있는 세션은 `/reload-plugins`
- 플러그인을 켜면 세션 시작 훅이 영상용 무료 서체(SIL OFL 21종)를 `~/Library/Fonts` 에 설치합니다.

## 빠른 시작

| 하고 싶은 일 | 이렇게 |
|---|---|
| 화면에서 모션 둘러보기 | `python3 skills/meta-motion/motion.py` (또는 `/meta-motion` 을 인자 없이) |
| 영상 만들기 | 「필첵 소개 쇼츠 만들어줘」 — 장면별 카드를 골라 만들고 쓴 카드 코드를 알려 줍니다 |
| 요청 문장만 받기 | 「로고 인트로 프롬프트 줘」 · `/meta-motion:meta-motion 켄 번스` |
| 세로·가로 지정 | `/meta-motion -v …` = 세로 9:16 · `/meta-motion -h …` = 가로 16:9 |
| 대본에 맞는 모션 추천 | `python3 skills/meta-motion/motion.py recommend 대본.txt` |

영상에는 첫 장면 인트로와 마지막 장면 아웃트로가 항상 들어갑니다.

### 로컬 화면(인자 없이 실행)

- 사내 KB(https://kb.pilldoc.co.kr/motion/)와 같은 페이지를 `http://127.0.0.1:8765/motion/` 에 띄우고 브라우저를 엽니다.
- 끄기 `Ctrl-C` · 다른 포트 `--port 9000` · 브라우저 안 열기 `--no-open`
- 실행할 때마다 `~/.cache/meta-motion/kb/motion/` 에 페이지를 새로 만들어서, 자료를 고친 직후에도 바로 반영됩니다.
- 실전 예시 영상은 원본 주소에서 재생하므로 인터넷이 필요합니다.

## 명령 모음

`M=skills/meta-motion/motion.py` 기준입니다. 전체 사용법은 `python3 $M help`.

| 명령 | 하는 일 |
|---|---|
| `python3 $M` | 로컬 화면 띄우기 |
| `list [분류]` | 분류별 전체 목록(`--cards` 면 요청 카드 152개만) |
| `search <단어…>` | 이름·영문·설명·업종으로 찾기(여러 단어는 AND) |
| `fields <코드>` | 채울 칸 보기 |
| `show <코드> [칸=값…]` | 요청 문장(기본 «자세히», `--simple` 이면 간단) |
| `order <코드…>` | 여러 카드를 한 요청으로(주문서) |
| `recommend <대본.txt>` | 장면별 추천 3개씩과 적합도(Jev) |
| `examples <영어 단어>` → `example <id>` | prompt-motion.com 실전 예시 찾기 → 프롬프트 전문 |
| `registry <단어>` → `registry-add <이름> --dir <프로젝트>` | HyperFrames 레지스트리 찾기 → 프로젝트에 넣기(npx) |
| `film <recommend.json> --durs …` | Claude Motion 검토 필름 기록 |

공통 옵션: `-v` 세로 · `-h` 가로 · `--ratio 가로|세로|정사각|없음` · `--color "남색과 노랑"` · `--file video.mp4` · `--tool auto|claude|codex`

예:

```bash
python3 $M search 자막
python3 $M show I02 title=필첵 --ratio 세로 --color "민트와 흰색"
python3 $M registry caption karaoke && python3 $M show caption-pill-karaoke -v
```

> `recommend` 는 대본 글이 api.typesafe.ai(Jev)로 나갑니다. workspace `shared/jev.py` 와 `JEV_API_KEY` 가 필요합니다.

## 들어 있는 자료

| 자료 | 개수 | 출처 | 파일 |
|---|---|---|---|
| 요청 카드 | 152 | [모션그래픽 주문 사전](https://nondev-thinking.web.app/motion/)(한국경영교육연구소 AI ACADEMY), 2026-10-08 수집 | `data/motion.json` |
| 실전 예시 | 233 | [prompt-motion.com](https://prompt-motion.com) — Claude 로 만든 영상의 프롬프트(영어, 만든 사람·원문 링크 포함), 2026-10-11 수집 | `data/prompt_motion.json`, 한국어 카드 `prompt_motion_ko.json` |
| HyperFrames 레지스트리 | 444 | heygen-com/hyperframes 공식 블록·컴포넌트(Apache-2.0). 출처 미확인 자산이 든 3개는 뺐음 | `data/hf_registry.json`, 한국어 카드 `hf_registry_ko.json`, 그림 `data/hf_thumb/` |
| 색·서체 템플릿 | 18 | 조회 수 높은 국내 쇼츠·릴스 실측 조합 | `fonts.py`, 서체 `data/fonts/` |

- 세 출처를 나누지 않고 같은 분류 16개·같은 모양의 한국어 카드로 섞어 `list`·`search`·`show`·`recommend`·화면에서 한 목록으로 씁니다.
- 실전 예시를 참고했으면 예시 id 와 만든 사람을 밝힙니다. 프롬프트 문장을 그대로 베끼지 않습니다.

## Claude Motion 과 합쳐 쓰기

- 렌더·MP4·내레이션: 단독 영상은 HyperFrames, 릴스 발행은 Playwright render(t)+ffmpeg
- 검토: claude.ai «Motion» 필름에 렌더 클립을 장면마다 올려 긁어 보고 시각에 댓글을 답니다.
- 맞는 카드가 없는 장면(추천 1위 적합도 0.5 미만)만 Motion 안에서 `kit.scene` 으로 그린 뒤 `data/motion_kit.js` 로 HyperFrames 하위 컴포지션에 옮깁니다.
- 필름 기록: `python3 $M film rec.json --durs … --out film/` (상세는 SKILL.md 「Claude Motion 과 합쳐 쓰기」)

## 자료 다시 만들기

| 무엇 | 스크립트 |
|---|---|
| 실전 예시 → 한국어 카드 | `build_pm_ko.py`(edb-p, 영어 8단어 연속 베끼기 검사) |
| 요청 카드 샘플 애니메이션 | `build_card_anim.py` → 검사·목록 그림 `check_card_anim.mjs`(`data/anim/`) |
| 레지스트리 | `build_hf.py` → `build_hf_ko.py` → `build_hf_thumbs.py` |
| 예시 대표 그림·Artifact 용 영상 | `fetch_posters.py`, `fetch_posters.py --clips`(둘 다 git 제외) |
| 사내 KB 페이지 | `export_kb.py <PillDocKb>/site/motion` |
| 추천 품질 다시 재기 | `eval_recommend.py` |

- 화면 정본은 `skills/meta-motion/preview.html` 하나입니다. KB 페이지와 로컬 화면은 `export_kb.py` 가 여기서 만듭니다.
- Artifact 로 올릴 때는 `data/` 의 자료 파일과 `posters/` 를 페이지 옆에 함께 올립니다(Artifact CSP 가 외부 영상을 막음).
- 테스트: `skills/meta-motion` 에서 `for t in test_*.py; do python3 $t; done` · `node test_motion_kit.mjs`

<sub>2026-10-14 이름 변경: 옛 `motion-prompt`(repo·플러그인·스킬·폴더) → `meta-motion`. 옛 GitHub 주소는 자동으로 이동합니다.</sub>

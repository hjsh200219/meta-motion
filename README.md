# meta-motion

영상·쇼츠·인트로를 만들 때 장면마다 맞는 모션그래픽을 골라 주는 Claude Code 플러그인입니다.
모션 829개를 같은 한국어 카드·같은 분류 16개로 한 목록에 모아 두고, 대본을 주면 장면별로 추천합니다.

```bash
python3 skills/meta-motion/motion.py           # 인자 없이 → 사내 KB 모션 메뉴를 로컬 브라우저로 연다
python3 skills/meta-motion/motion.py --local   # SSH 로 붙은 원격 컴퓨터에서 띄우고 내 PC 브라우저로 본다
```

> 공개 repo입니다(2026-11-10 공개 전환). 수집 자료의 영상·프롬프트 저작권은 만든 사람에게 있습니다.

## 목차

- [설치](#설치)
- [처음 한 번 — 키 저장](#처음-한-번--키-저장)
- [빠른 시작](#빠른-시작)
- [명령 모음](#명령-모음)
- [들어 있는 자료](#들어-있는-자료)
- [Claude Motion 과 합쳐 쓰기](#claude-motion-과-합쳐-쓰기)
- [Windows 에서 쓰기](#windows-에서-쓰기)
- [자료 다시 만들기](#자료-다시-만들기)

## 설치

```bash
claude plugin marketplace add hjsh200219/meta-motion
claude plugin install meta-motion@meta-motion
```

| 필요한 것 | 어디에 | 없으면 |
|---|---|---|
| Python 3.9 이상(표준 라이브러리) | 전부 | 동작 안 함 |
| git(공개 repo라 GitHub 로그인·협업자 권한 불필요) | 설치 | `git ls-remote https://github.com/hjsh200219/meta-motion.git` 로 확인 |
| Jev(TypeSafe) API 키 | `recommend`(대본 → 장면별 추천) · 색·서체 템플릿 고르기 | 그 둘만 안 됨(템플릿은 분위기 기본값) — [키 저장](#처음-한-번--키-저장) |
| Fish Audio API 키 | `narrate`(장면별 내레이션 — 영상 기본값은 음성 있음) | 내레이션 없는 영상만 — [키 저장](#처음-한-번--키-저장) |
| Node.js 18+ · ffmpeg | 영상 렌더(HyperFrames `npx`)·`narrate`·`registry-add`·자르기 | 카드 찾기·요청 문장은 그대로 됨 |
| fontTools | 2MB 넘는 글꼴을 영상용으로 줄일 때 | `python3 -m pip install --user fonttools` |
| Tailscale | `--local`(내 PC 에서 화면 보기) | `--local` 만 안 됨 |

- 업데이트: `claude plugin update meta-motion@meta-motion` → 떠 있는 세션은 `/reload-plugins`
- 플러그인을 켜면 세션 시작 훅이 영상용 무료 서체(SIL OFL 21종)를 사용자 서체 폴더에 설치합니다(macOS `~/Library/Fonts` · Windows `%LOCALAPPDATA%\Microsoft\Windows\Fonts` + 사용자 서체 등록 · Linux `~/.local/share/fonts`, 관리자 권한 불필요).

## 처음 한 번 — 키 저장

Claude Code 에서 `/meta-motion:setup`, 또는 터미널에서:

```bash
python3 skills/meta-motion/motion.py setup              # Jev·Fish Audio 키를 차례로 입력(화면에 안 보임) → 확인 → 저장
python3 skills/meta-motion/motion.py setup --check      # 어디서 읽는지만(값은 안 찍음) · --force 바꾸기 · --forget 지우기
python3 skills/meta-motion/motion.py setup --only fish  # 하나만(jev · fish)
```

| 키 | 쓰는 곳 | 확인 방법 | 발급 |
|---|---|---|---|
| Jev `JEV_API_KEY` | `recommend`·색·서체 템플릿 | Jev 에 짧은 질문 1번 | https://typesafe.ai |
| Fish Audio `FISH_AUDIO_API_KEY` | `narrate` 내레이션 | 잔액 조회(과금 없음 · 잔액도 보여 줌) | https://fish.audio → API Keys(API 크레딧은 웹 크레딧과 따로 충전) |

- 저장 위치: macOS 키체인(서비스 `typesafe-jev`·`fish-audio`) · Windows 자격 증명 관리자 · 그 밖 `~/.config/<서비스>/key`(0600).
- 읽는 순서: 환경변수 → 위 저장소 → `~/workspace/.env`. Jev 클라이언트는 repo 에 든 사본(`skills/meta-motion/jev.py`)을 씁니다.
- Fish 키는 선택입니다. 비워 두면 건너뛰고, 나중에 `--only fish` 로 넣을 수 있습니다.
- **meta-slide 와 같은 저장소**라 한 번 저장하면 두 플러그인 모두 씁니다.
- 키는 채팅에 붙여 넣지 마세요. Claude 가 실행하면 OS 입력 창이 뜹니다. SSH 로 붙어 있으면 창이 원격 화면에 뜨므로 그 SSH 터미널에서 직접 실행하세요.
- 사내는 관리자에게 키를 받습니다.

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
- **`--local`**: 원격 컴퓨터에 SSH 로 붙어 쓰는 경우, 그 컴퓨터의 Tailscale 주소(`http://<컴퓨터>.<tailnet>.ts.net:8765/motion/`)에도 띄워 내 PC 브라우저에서 엽니다.
  - 들어올 수 있는 것은 **같은 Tailscale 계정의 기기**(내 PC·폰)뿐입니다. 같은 tailnet 의 다른 사람 기기는 403 입니다.
  - 2시간 동안 요청이 없으면 스스로 꺼집니다. 포트를 다른 프로그램이 쓰고 있으면 다음 포트로 옮깁니다.
  - 마지막 줄 `LOCAL_URL=` 이 열 주소입니다. Claude Code 에서는 Claude 가 내 PC 크롬(claude-in-chrome)에서 열어 줍니다.

## 명령 모음

`M=skills/meta-motion/motion.py` 기준입니다. 전체 사용법은 `python3 $M help`.

| 명령 | 하는 일 |
|---|---|
| `python3 $M [--local]` | 로컬 화면 띄우기(`--local` 은 내 PC 브라우저용) |
| `setup [--check] [--only jev\|fish]` | 키 저장·확인 |
| `narrate 대본.txt --out vo/ [--dry-run]` | 장면별 내레이션 → `track.wav` · `segments.json` · `--durs`(숫자는 한글 발음으로 · 캐시라 다시 돌리면 과금 0) |
| `list [분류]` | 한 목록 — 모션 분류 16개, 이어서 표현 기법·색·서체 템플릿(`--cards` 면 요청 카드 152개만) |
| `search <단어…> [--kind …]` | 모든 종류를 한 번에 찾기(여러 단어는 AND) — 줄 끝 꼬리표가 종류·출처·라이선스·만든 사람 |
| `show <id> [칸=값…] [--template <id>]` | 어느 종류든 자세히 — 모션은 요청 문장(+ 템플릿 색·서체 토큰), 기법은 노트 전문, 템플릿은 최종 토큰 |
| `fields <id>` | 채울 칸 보기 |
| `order <id…>` | 여러 모션을 한 요청으로(주문서) |
| `add <id> --dir <프로젝트>` | 받을 수 있는 항목(레지스트리) 프로젝트에 넣기(npx) |
| `theme [<id>]` | 색·서체 템플릿 목록 / 최종 토큰 |
| `recommend <대본.txt>` | 장면별 추천 3개씩과 적합도(Jev) |
| 옛 명령 `examples`·`example`·`registry`·`registry-add`·`technique` | 그대로 동작(실전 예시 원문은 `example <id>`) |
| `film <recommend.json> --durs …` | Claude Motion 검토 필름 기록 |
| `check <프로젝트>` | 렌더 전 검사 — lint 가 놓치는 비결정 코드 + 세로 영상 쇼츠 UI 띠의 글자 |
| `technique <단어>` → `technique <번호>` | 표현 기법 참고서(cokacmotion) 찾기 → 노트 전문·소스 경로(기술만 가져간다) |

공통 옵션: `-v` 세로 · `-h` 가로 · `--ratio 가로|세로|정사각|없음` · `--color "남색과 노랑"` · `--file video.mp4` · `--tool auto|claude|codex`

예:

```bash
python3 $M search 자막
python3 $M show I02 title=필첵 --ratio 세로 --color "민트와 흰색"
python3 $M registry caption karaoke && python3 $M show caption-pill-karaoke -v
```

> `recommend` 는 대본 글이 api.typesafe.ai(Jev)로, `narrate` 는 대본 글이 api.fish.audio 로 나갑니다. 먼저 [키 저장](#처음-한-번--키-저장)을 한 번 하세요.

## 들어 있는 자료

| 자료 | 개수 | 출처 | 파일 |
|---|---|---|---|
| 요청 카드 | 152 | [모션그래픽 주문 사전](https://nondev-thinking.web.app/motion/)(한국경영교육연구소 AI ACADEMY), 2026-10-08 수집 | `data/motion.json` |
| 실전 예시 | 233 | [prompt-motion.com](https://prompt-motion.com) — Claude 로 만든 영상의 프롬프트(영어, 만든 사람·원문 링크 포함), 2026-10-11 수집 | `data/prompt_motion.json`, 한국어 카드 `prompt_motion_ko.json` |
| HyperFrames 레지스트리 | 444 | heygen-com/hyperframes 공식 블록·컴포넌트(Apache-2.0). 출처 미확인 자산이 든 3개는 뺐음 | `data/hf_registry.json`, 한국어 카드 `hf_registry_ko.json`, 그림 `data/hf_thumb/` |
| 표현 기법 참고서 | 166 | [cokacmotion](https://github.com/kstost/cokacmotion)(MIT © 2026 kstost) — 기법 하나당 데모 하나. 목록만 싣고 노트·소스는 쓸 때 캐시로 받음 | `data/cokac.json` |
| 색·서체 템플릿 | 18 | 조회 수 높은 국내 쇼츠·릴스 실측 조합 | `fonts.py`, 서체 `data/fonts/` |

- 출처를 나누지 않습니다. 모션 829·기법 166·템플릿 18 을 `catalog.py` 가 같은 꼴의 항목(id·종류·분류·출처·라이선스·브랜드 흉내·크기)으로 맞춰 `list`·`search`·`show`·`recommend`·화면에서 한 목록으로 씁니다. 원본 자료 파일은 출처별로 그대로 두어 갱신·라이선스·KB 내보내기가 바뀌지 않습니다.
- 대본 점검(`references/script-check.md`)·미술감독 채점(`references/art-director.md`)·`check.py` 는 [script-to-motion](https://github.com/kstost/script-to-motion)(MIT © 2026 kstost)에서 착안해 다시 썼습니다.
- 실전 예시를 참고했으면 예시 id 와 만든 사람을 밝힙니다. 프롬프트 문장을 그대로 베끼지 않습니다.

## Claude Motion 과 합쳐 쓰기

- 렌더·MP4·내레이션: 단독 영상은 HyperFrames, 릴스 발행은 Playwright render(t)+ffmpeg
- 검토: claude.ai «Motion» 필름에 렌더 클립을 장면마다 올려 긁어 보고 시각에 댓글을 답니다.
- 맞는 카드가 없는 장면(추천 1위 적합도 0.5 미만)만 Motion 안에서 `kit.scene` 으로 그린 뒤 `data/motion_kit.js` 로 HyperFrames 하위 컴포지션에 옮깁니다.
- 필름 기록: `python3 $M film rec.json --durs … --out film/` (상세는 SKILL.md 「Claude Motion 과 합쳐 쓰기」)

## Windows 에서 쓰기

- 명령은 같고 `python3` 대신 `python`(또는 `py`)을 씁니다. 예: `python skills\meta-motion\motion.py search 자막`.
- 키는 Windows 자격 증명 관리자에 저장합니다(SSH 로 붙은 세션처럼 자격 증명 관리자를 못 쓰면 `%APPDATA%\typesafe-jev\key`).
- 세션 시작 훅은 `python3` 가 없으면 `python` 으로 서체를 설치합니다. 콘솔 출력은 UTF-8 로 맞춥니다.
- `--local` 은 Windows 용 Tailscale(`C:\Program Files\Tailscale\tailscale.exe`)이 있으면 같게 동작합니다.

## 자료 다시 만들기

| 무엇 | 스크립트 |
|---|---|
| 실전 예시 → 한국어 카드 | `build_pm_ko.py`(edb-p, 영어 8단어 연속 베끼기 검사) |
| 요청 카드 샘플 애니메이션 | `build_card_anim.py` → 검사·목록 그림 `check_card_anim.mjs`(`data/anim/`) |
| 레지스트리 | `build_hf.py` → `build_hf_ko.py` → `build_hf_thumbs.py` |
| 예시 대표 그림·Artifact 용 영상 | `fetch_posters.py`, `fetch_posters.py --clips`(둘 다 git 제외) |
| 사내 KB 페이지 | `export_kb.py <PillDocKb>/site/motion` |
| 추천 품질 다시 재기 | `eval_recommend.py` |
| 표현 기법 참고서 | `build_cokac.py` |

- 화면 정본은 `skills/meta-motion/preview.html` 하나입니다. KB 페이지와 로컬 화면은 `export_kb.py` 가 여기서 만듭니다.
- Artifact 로 올릴 때는 `data/` 의 자료 파일과 `posters/` 를 페이지 옆에 함께 올립니다(Artifact CSP 가 외부 영상을 막음).
- 테스트: `skills/meta-motion` 에서 `for t in test_*.py; do python3 $t; done` · `node test_motion_kit.mjs`

<sub>2026-10-14 이름 변경: 옛 `motion-prompt`(repo·플러그인·스킬·폴더) → `meta-motion`. 옛 GitHub 주소는 자동으로 이동합니다.</sub>

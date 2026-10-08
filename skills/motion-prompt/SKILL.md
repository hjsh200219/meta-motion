---
name: motion-prompt
description: 모션그래픽 요청 문장 사전(152종) — 영상·쇼츠·인트로·광고·안내 영상을 만들거나 고칠 때 장면마다 맞는 카드(자막·장면 전환·로고 인트로·데이터 차트·3D·사진 배경·가게/행사/공지 안내·엔딩)를 찾아 그 «자세히» 문장(길이·장면 순서·볼거리·모양·움직임·하지 말 것)을 장면 사양으로 쓴다. HyperFrames·Remotion·HTML 애니메이션 어느 도구든 적용. 트리거 — "/motion-prompt", "모션그래픽", "모션 그래픽", "모션 템플릿", "영상 만들어", "영상 제작", "영상 만들기", "쇼츠 만들어", "숏폼", "인트로 영상", "로고 인트로", "오프닝 타이틀", "엔딩 화면", "구독 버튼", "자막 애니메이션", "자막 효과", "키네틱 타이포", "장면 전환", "트랜지션", "켄 번스", "하이퍼프레임", "hyperframes", "remotion", "리모션", "nondev motion".
---

# motion-prompt

출처: https://nondev-thinking.web.app/motion/ (한국경영교육연구소 AI ACADEMY «모션그래픽 주문 사전»). 2026-10-08 수집.
`motion.py` 는 사이트 원본 조립 코드(`data/compose.mjs`)를 표준 라이브러리 Python 으로 옮긴 것 — 원본과 913개 경우 대조 일치(수집일 실측). Python 3 만 있으면 된다.

## 쓰는 법

```bash
M="<이 스킬 폴더>/motion.py"   # 스킬을 부르면 표시되는 Base directory (개인 설치는 ~/.claude/skills/motion-prompt)
python3 $M search 로고                 # 찾기(이름·영문·설명·업종, 여러 단어는 AND)
python3 $M list 자막                   # 카테고리별 목록(인자 없으면 16개 전체)
python3 $M fields I02                  # 채울 칸
python3 $M show I02 img=a.jpg title=필첵 --ratio 세로 --color "민트와 흰색"   # 🔍자세히(기본)
python3 $M show I02 --simple           # 간단
python3 $M order T01 I02 --ratio 세로   # 여러 카드를 한 요청으로(사이트 «주문서»)
```

- 비운 필수 칸은 사이트 예시값이, 비운 선택 칸은 그 구절이 통째로 빠진다.
- `--tool auto|claude|codex` → 문장 머리 `하이퍼프레임(HyperFrames)으로` / `/hyperframes 로` / `$hyperframes 로`.
- `--ratio` 기본 가로 16:9(사이트 기본값). 쇼츠면 `세로`.

## 영상 제작 중 자동 사용 (이 스킬이 불렸으면 먼저 이것)

영상·쇼츠·인트로를 만들거나 장면을 고치는 작업이면 사용자가 카드를 지정하지 않아도 아래를 한다.

1. 영상을 장면 단위로 나눈다(오프닝·본문 설명·데이터·전환·자막·엔딩 등).
2. 장면마다 `python3 $M list` 전체 목록(152줄)에서 맞는 카드를 1개씩 고른다 — 키워드가 분명하면 `search`. 맞는 카드가 없으면 그 장면은 건너뛴다(억지로 끼우지 않는다).
3. 고른 카드마다 `fields` 로 칸을 보고 실제 값(제목·파일·숫자·길이)과 영상 비율(`--ratio`)·색(`--color`)으로 `show`(자세히)를 뽑는다.
4. 그 문장을 장면 사양으로 삼아 구현한다 — `[장면 순서]` 타이밍·`[볼거리 한 번]`·`[하지 말 것]` 을 지킨다. 대상이 HyperFrames 가 아니면(Remotion·HTML 등) 첫 줄 도구 이름만 무시하고 본문을 따른다.
5. 사용자에게 장면별로 쓴 카드 코드·이름을 한 줄씩 밝힌다(예: 「오프닝 T01 입자 로고 인트로」).

## 사용자에게 줄 때 (프롬프트 자체를 원할 때)

1. 원하는 장면을 `search` 로 찾아 후보 2~3개를 코드·이름·한 줄 설명으로 보여 준다.
2. 고르면 `fields` 로 칸을 확인하고 사용자 값으로 `show` — 결과 문장을 그대로 전달한다(요약·의역 금지).
3. 대상 도구가 HyperFrames 가 아니면(예: Remotion repo) 첫 줄의 도구 이름만 바꾸고, `[장면 순서]` 등 6절 본문은 그대로 쓴다.

## 갱신

사이트가 바뀌면 `python3 <이 스킬 폴더>/build.py` — data/motion.json·compose.mjs 를 다시 받는다.
카드 150개 미만이면 중단하고, 조립 규칙이 바뀌었거나 간단 문장이 사이트와 다르면 경고한다(그때는 motion.py 를 compose.mjs 에 맞춰 고친다).

## 파일

- `data/motion.json` — 카드 152개: code·cat·name·en·plain·len·when·inds·fields·tpl·dx(자세히 재료)
- `data/compose.mjs` — 사이트 원본 조립 코드(참조용 · 수정 금지, build.py 가 덮어씀)
- `motion.py` — CLI(Python 3, 의존성 없음) · `build.py` — 재수집·대조

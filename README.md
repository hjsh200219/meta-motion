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
- 화면으로 고르기: `skills/motion-prompt/preview.html` — 카드 152개의 장면 순서 재생·칸 채우기·요청 문장 복사 + 실전 예시 233개 찾기. 같은 폴더의 `data/*.json` 을 읽으므로 Artifact 로 게시하거나(`motion.json`·`prompt_motion.json` 을 함께 올림) 그 폴더를 웹 서버로 연다. 비공개 Artifact: https://claude.ai/artifact/8wfwMfKyM3HrRY92r3csFb
- 직접: `python3 skills/motion-prompt/motion.py search 자막` · `show I02 title=필첵 --ratio 세로` (전체 사용법은 인자 없이 실행)

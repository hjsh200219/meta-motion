# 수치 규칙 — GitHub 모션 키트에서 가져온 것 (2026-11-22)

쇼츠 «10 GitHub Repos That Level Up HyperFrames Videos»(https://www.youtube.com/shorts/Dx6c5isxnN0)가 소개한 키트를 읽고, meta-motion 에 없던 수치 규칙만 옮겼다. 코드는 옮기지 않았다(렌더 뒤 검사 `verify.py` 는 기준만 가져와 다시 썼다).
원본은 모두 MIT 또는 Apache-2.0 이고, 각 절 끝에 출처 파일을 적었다. 렌더러·버전이 달라 이 스킬(HyperFrames 0.8.162)에서 재현되지 않은 주장은 맨 끝 「옮기지 않은 것」에 적었다.

## 1. 화면 글 읽기 시간

- **필요 읽기 시간 = 0.5초 + 화면 글자 수 ÷ 12**(한국어 기준, 공백 제외)로 잡는다. 예를 들어 18자 제목은 2.0초다.
- **장면 길이에서 읽기 시간을 뺀 값이 0.8초 미만이면** 움직임을 줄인다(페이드만 남긴다). 글이 움직이는 동안에는 읽히지 않기 때문이다.
- 제목이 20자를 넘거나 읽을 덩어리가 5개를 넘으면 다음 순서로 고친다.
  1. 문구를 줄인다.
  2. 그래도 안 되면 장면을 나눈다.
  3. 그래도 안 되면 움직임을 줄인다.
- 42자를 넘는 제목은 다시 쓴다.
- **UI 애니메이션 시간을 영상 시간으로 바꾸는 표**
  - 등장 200~300ms → 0.5~0.9초
  - 퇴장 150~200ms → 0.3~0.5초
  - 순차 간격(stagger) 20~40ms → 60~150ms
  - 작은 반응 100ms → 0.25~0.35초
  - 화면 UI 수치를 그대로 쓰면 영상에서는 너무 빨라 보이지 않는다.

출처: reelforge `skills/reelforge/references/design-direction.md` §4·§4-2 (Apache-2.0)

## 2. 아마추어 티 — 수치로 거르는 것

아래는 미술감독 채점(`art-director.md`)의 모션 축에서 감점하는 근거다.

- 등장한 뒤 그대로 굳는 장면. 말이 이어지는데 그림이 멈추면 `verify` 가 2초 이상 정지를 경고한다.
- 모든 요소가 같은 이징을 쓰거나 한꺼번에 등장한다.
- 등장에 ease-in(가속)을 쓴다. 등장은 감속(out)으로 한다.
- 튕김(오버슈트)이 과하다.
  - `back.out` 은 1.7 이하로 쓴다.
  - 글자·차트에는 elastic 을 쓰지 않는다.
  - 튕김은 모양에만 주고, 투명도에는 주지 않는다.
- 30초에 컷이 12개를 넘는다.
- 글을 1초에 20자 넘게 읽혀야 하거나, 0.83초 안에 사라진다.
- 프레임마다 움직이는 요소에 box-shadow·filter 를 트윈한다(렌더가 느리고 번진다).
- 강조색이 한 장면에 두 곳 이상이다.
- 0.5초 넘는 크로스페이드를 쓴다.
- 어두운 배경 위에 drop-shadow 를 쓴다.
- 서로 경쟁하는 움직임이 3개 이상이다.
- 첫 1.8초 안에 훅(볼거리·질문)이 없다.
- 같은 레이아웃이 3장면 연속 나온다.

출처: reelforge `skills/reelforge/references/strip-qc.md`·`design-direction.md` 부록 (Apache-2.0)

## 3. 카메라 예산

- **카메라 이동 간격**
  - 이동과 이동 사이는 2.6~3.0초 이상 둔다.
  - 15초 안에 4~5번 이하, 1분에 6컷 이하로 움직인다.
  - 노드·요소가 6개 이하인 화면은 카메라를 움직이지 않는다.
- **줌 크기**
  - 1.25배 미만 줌은 쓰지 않는다. 미세하게 밀어 들어가는 1.06배 시작 푸시만 예외다.
  - 줌 단계는 1.06 · 1.3 · 1.45 · 1.8 · 2.3배를 쓰고, 최대 2.2배(권장 1.6배)를 넘기지 않는다.
- **줌 길이 = 0.55 × |ln(목표 배율 ÷ 현재 배율)| ÷ ln2** 초로 계산하고, 0.30~0.94초 범위로 자른다. 이징은 `power3.inOut` 이다.
- **리그 구조**: `#viewport > #camera > #world` 로 짜고 HUD·자막은 `#camera` 밖(형제)에 둔다. 카메라 상태는 타임라인 시간에서만 나와야 한다(seek-safe).
- **시차(패럴랙스)**: 층 속도 계수는 0.35 / 0.7 / 1.4 로 하고, 이웃 층은 2배 이상 차이 나게, 층은 4개 이하로 둔다.
- **가짜 돌리 줌**(주체는 고정하고 배경만 2~2.5배로 확대)은 1.2초 이상으로, 영상당 1번만 쓴다.
- 줌을 다 보여준 뒤에는 전체를 보여주고(`camFitAll`) 1.2초 이상 머문다. 말이 쉬는 곳에 이동을 맞추되, 가장 가까운 쉼으로 최대 0.8초까지 당긴다.
- 카드: `hs-camera-rig`.

출처: huashu-design `references/camera-language.md` §3·§4·§8·§9 · `references/gsap-recipes.md` §9 (MIT) · animated-diagrams-skill `references/camera-large-flows.md` (Apache-2.0)

## 4. 전환 다양성 — 영상 한 편 기준

- 같은 전환을 연달아 쓰지 않는다.
- 같은 전환은 60초 미만 영상이면 2번까지, 60초 이상이면 3번까지 쓴다.
- 컷이 5개 이상이면 전환 계열을 3가지 이상 섞고, 그중 하나는 이야기를 잇는 계열(컷·요소 운반·카메라·마스크)이어야 한다.
- 소리 없는 하드컷이 기본 리듬이다. 화려한 전환은 아껴 쓴다.
- **반복 금지**
  - 같은 등장 효과를 3번 연속 쓰지 않는다.
  - 이징은 3가지 이상 쓰고, 한 이징이 절반을 넘지 않게 한다.
  - 같은 방향 이동을 3번 연속 쓰지 않는다.
  - 같은 길이 샷이 60%를 넘지 않게 한다.
- **15초마다 놀람이 하나** 있어야 한다. 처음 보는 요소나 예상을 뒤집는 움직임이면 된다.
- **톤에 맞지 않는 것**
  - 차분한·고급스러운 톤: `back`·`elastic` 이징, 0.7초 미만 샷
  - 급한 톤: 2초 넘는 정지
  - 믿음직한 톤: 글리치·VHS·색번짐·일그러짐 전환
- 카드: `tr-*` 전환 24종(saas-motion-kit 아틀라스).

출처: saas-motion-kit `tools/variety_audit.py`·`creative/variety-rules.md`·`creative/tone-matrix.md` (MIT)

## 5. 소리 — 효과음·배경음·음량

- **효과음은 보이는 동작에만 붙인다**(손가락으로 짚을 수 있는 움직임 하나에 소리 하나).
  - 컷마다 휙 소리를 넣지 않는다.
  - 같은 시각에 효과음은 2개까지만 겹친다.
  - 같은 종류의 소리도 파일을 바꿔 가며 변주한다.
  - 큐를 30~50% 빼면 오히려 더 극적이다.
- **맞추는 시각은 접점 프레임이다.** 트윈 시작이 아니라 감속 이징이 거의 멈추는 시점(시작 + 길이의 약 85%)에 맞춘다.
  - 소리는 그림보다 늦는 것은 괜찮지만 앞서면 안 된다(목표 0~30ms 지연, 2프레임 넘게 어긋나면 실패).
  - 클릭은 0ms, 휙 소리는 −33ms, 충격음은 +33ms 로 맞춘다.
  - 근거: ITU-R BT.1359-1 기준으로 소리가 앞서면 +45ms 부터, 뒤처지면 −125ms 부터 사람이 알아챈다.
- **움직임에서 소리값을 정한다**
  - 음높이: 크기(√면적 px)에서 `f0 = 5200 × (60 ÷ 크기)^0.75` Hz 로 구한다. 작은 것은 높고 짧게, 큰 것은 낮고 길게 들린다.
  - 여운: `0.1 + 크기 ÷ 460 × 0.5` 초
  - 좌우 팬: `(x ÷ 화면폭 − 0.5) × 1.4` 를 ±0.7 로 자른다.
  - 레벨: 크기가 2배가 될 때마다 +6dB
  - 같은 큐 시트면 같은 소리가 나와야 한다. 큐 id 로 시드를 고정한다.
- **배경음과 음성**
  - 배경음은 음성보다 약 11dB(9~14dB) 낮게 깔고, 말하는 동안 3~4dB 더 내린다(덕킹).
  - 배경음에는 lowpass 4kHz, 효과음에는 highpass 800Hz 를 걸고 `amix normalize=0` 으로 섞는다.
  - 배경음 페이드는 인 0.3초, 아웃 1.5초다.
- **마스터 음량**
  - 쇼츠 납품 기준은 −14 LUFS, true peak −1~−1.5 dBTP 다. 측정은 최종 인코딩 파일로 한다.
  - `ffmpeg -af loudnorm=I=-14:TP=-1.5:LRA=11` 로 맞춘다.
  - 2패스 `linear=true` 는 새 트랜지언트에 물러서지 않아 클리핑이 날 수 있다.
  - `alimiter` 는 `level=disabled` 를 줘야 메이크업 게인으로 음량이 뜨지 않는다.
  - `motion.py verify` 가 −18~−10 LUFS 밖, −1 dBTP 초과를 경고한다.
- **효과음 파일**
  - 라이선스는 CC0·CC BY 만 쓴다. NC·ND·SA·「개인 사용」은 쓰지 않는다.
  - 파일마다 출처 페이지·읽은 날짜·크레딧 줄을 남긴다.
  - huashu-design 의 BGM(Suno 생성)·효과음(ElevenLabs 생성)은 repo 안에 권리 근거가 없어 쓰지 않는다.

출처: design-engineering `references/sound/sound-from-motion.md`·`sound-motion-sync.md`·`sound-licensing.md` (MIT) · huashu-design `references/audio-design-rules.md` (MIT) · herk-edit-kit 플레이북(MIT) · product-launch-motion `legacy/references/07-sound.md`·`legacy/scripts/master.sh` (MIT) · saas-motion-kit `tools/deliver.sh` (MIT)

## 6. 렌더 뒤 검사 — `motion.py verify <영상.mp4>`

- 렌더 전 검사(`check`)는 코드를 보고, `verify` 는 다 만든 파일을 본다. 미술감독 채점 전에 먼저 돌린다.
- **오류**
  - 빈 화면: 프레임 80% 넘게 거의 검정·흰색
  - 처음부터 끝까지 정지
  - 크기가 다름
  - 길이가 ±max(2%, 0.2초) 밖
- **경고**
  - 중간 2초 이상 정지, 또는 마지막 정지가 3초 초과
  - 처음·끝 0.3초가 통째로 검정
  - 소리 트랙 없음
  - 음량이 기준 밖
- **멈춤 판정**: 초당 10장에서 이웃 프레임 차이의 최댓값이 5 이하이면 멈춘 것으로 본다.
  - ffmpeg `freezedetect`(평균 차이)는 손글씨·얇은 선 다이어그램처럼 화면 일부만 움직이는 영상을 멈춤으로 잘못 본다(2026-11-22 실측: 정지 0, 손글씨·다이어그램·숨 쉬는 밝기 변화 6 이상).
- **밝기**: mp4(yuv420p)는 제한 범위라 검정이 16으로 나온다. 0~255 전체 범위로 바꿔 잰다.

출처(기준): reelforge `scripts/gallery-verify.mjs` · huashu-design `scripts/verify-video.sh` · design-engineering `references/launch-video/launch-video-review.md` · product-launch-motion `legacy/references/04-motion-grammar.md`

## 7. 손글씨·외부 라이브러리를 시간에 묶기

외부 애니메이션 라이브러리(tegaki 손글씨 등)는 자체 시계로 돌리지 않는다. 일시정지 GSAP 타임라인의 `onUpdate` 에서 라이브러리의 시간 제어 모드로 그 시각을 넘긴다.

- tegaki 의 경우 `engine.update({time:{mode:'controlled', value:초, unit:'seconds'}})` 를 쓴다.
- 이렇게 하면 seek 렌더와 같은 그림이 나온다(2026-11-22 HyperFrames 0.8.162 에서 한글 손글씨로 확인).
- 라이브러리가 쓰는 글꼴은 측정 전에 로드가 끝나야 한다(`document.fonts.ready`).

출처: tegaki `packages/renderer/src/core/engine.ts` (MIT) · huashu-design `references/animation-pitfalls.md` §6 (MIT)

## 옮기지 않은 것 — 이 스킬 환경에서 재현되지 않았거나 이미 있는 것

- **「`<audio>` 에 id 가 없으면 렌더가 무음」**(animated-diagrams-skill)
  - HyperFrames 0.8.162 에서는 lint 가 `media_missing_id` 오류로 이미 잡는다.
  - 렌더한 결과도 무음이 아니었다(id 있음·없음 둘 다 평균 −24.1 dB, 2026-11-22 실측).
- **「한글 컨테이너에 `line-height<1` + `overflow:hidden` 이면 글자 윗부분이 잘림」**(reelforge)
  - 0.86, Pretendard 800, 150px 에서는 재현되지 않았다(2026-11-22 실측).
- **CSS transition·`@keyframes` 금지**(huashu-design)
  - reelforge 는 반대로 씬 시작 뒤 CSS 숨쉬기를 쓰고, 0.8.162 에서 렌더된다. 금지 규칙으로 넣지 않았다.
- **결정성(시계·난수 금지)** 은 `check.py` 에 이미 있다.
- **herk-edit-kit 의 카드 406장**(Vox·Kallaway 스타일)은 넣지 않았다.
  - 두 스타일의 `tokens.css` 가 AIS 브랜드 색을 쓰고, LICENSE 의 「Note on brand assets」가 이 브랜드 토큰의 재사용을 허락하지 않는다.
  - 무음 자르기·말실수 자르기 같은 편집 도구는 이 스킬(모션 카드) 범위 밖이다.
- **openai/plugins 의 hyperframes 스킬**은 HeyGen 공식 스킬의 Codex 사본이다. 이 컴퓨터에 설치된 판(HeyGen 원본)과 해시가 달라 옛 판이므로 넣지 않았다.

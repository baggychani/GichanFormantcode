# Desktop Visual Key (메인 창 재설계 기준)

이 문서는 Tauri/React 메인 창의 **비주얼 정체성**을 고정한다.
UI 컴포넌트를 예쁘게 만들기 전에 여기 규칙을 통과해야 한다.

관련 자산: `assets/gichanformant.png` (블랙 위 cyan mesh)

---

## 1. 제품이 보여줘야 하는 것

GichanFormant는 소비자 랜딩페이지가 아니라 **분석 워크벤치**다.

| 키워드 | 의미 |
| --- | --- |
| Precision | 축·단위·스케일이 도구처럼 또렷해야 한다 |
| Density | 한 화면에 파일·미리보기·핵심 설정이 군더더기 없이 |
| Quiet chrome | 장식보다 데이터(미리보기/파일)가 주인공 |
| Brand signal | cyan mesh / 딥 블랙 계열이 “이 앱”임을 말함 |

**하지 않을 것**

- PySide Element UI(`#409EFF` 카드 스택)를 웹으로 복붙
- 보라 그라데이션, 크림+세리프, 대시보드 카드 잔치
- “AI 툴 느낌”만 나는 과장된 glow를 화면 전체에 깔기

---

## 2. Visual Key (한 줄)

> **Deep charcoal workbench + cyan instrument accent.**
> 사이드바는 어두운 도구함, 본문은 데이터가 읽는 작업면, accent는 브랜드 cyan만 절제해서.

브랜드 PNG의 메시는 **스플래시/빈 상태/로딩**에만 쓰고, 일상 UI에는 얇은 accent line·focus ring 정도로만 남긴다.

---

## 3. 색 시스템 (semantic tokens)

이름은 역할 기준. hex는 `desktop/src/styles/tokens.css`가 소스다.

### Surfaces
- `surface-shell` — 앱 외곽 (거의 블랙)
- `surface-sidebar` — 사이드바
- `surface-stage` — 메인 작업면 (딥 그레이, 순백 금지)
- `surface-panel` — inspector / 팝오버
- `surface-elevated` — 드롭다운·모달

### Text
- `text-primary` / `text-secondary` / `text-tertiary` / `text-invert`

### Accent (브랜드)
- `accent` — cyan instrument (`≈ #5CE1E6` 계열, PNG와 맞춤)
- `accent-muted` — 선택/호버 배경
- `accent-border` — 포커스·활성 테두리

### State
- `danger` / `success` / `warning`
  CTA “플롯 생성”은 success 초록이 아니라 **accent 기반 primary**로 통일한다.
  (PySide 초록 CTA는 레거시. 새 셸에서는 accent가 행동 색.)

### Borders
- `border-subtle` / `border-strong` — 헤어라인 위주, 두꺼운 카드 테두리 지양

---

## 4. 타이포 / 밀도

| 역할 | 규칙 |
| --- | --- |
| UI sans | 시스템 우선: Windows `Segoe UI`, 한글 `Malgun Gothic` 폴백. 장식 세리프 금지 |
| Mono | 로그·경로·수치: `Consolas` / `ui-monospace` |
| 밀도 | 사이드바 행 높이 ≈ 32–36px. 카드 마진으로 화면을 먹지 말 것 |
| 제목 | 사이드바 섹션은 11–12px caps/tracking. 히어로 카피 남발 금지 |

---

## 5. 레이아웃 원칙 (비주얼과 결합)

1. **Sidebar = 항해** (파일, 프로젝트, 가이드) — 항상 보임
2. **Stage = 결과** (LIVE 미리보기) — 가장 큰 면적
3. **Inspector = 조정** (분석 설정) — 기본 요약, 펼쳐서 편집
4. **Log = 보조** — 상시 115px 블랙박스가 아니라 상태바 + 필요할 때 패널

시각적 무게: `Stage > Sidebar ≥ Inspector > chrome`

---

## 6. 모션

- 150–200ms ease, opacity/transform만
- glow 펄스·파티클·배경 애니메이션 상시 금지
- 패널 열림, 파일 선택, preview 교체만 짧게

---

## 7. 합격 테스트 (디자인 리뷰용)

새 메인 창 스크린샷에서:

1. 브랜드 PNG를 옆에 두면 **같은 제품**으로 보이는가? (cyan + deep dark)
2. 그룹박스 제목만 지워도 구조가 읽히는가? (장식 카드에 의존하지 않는가?)
3. 파일 0개 / 파일 있음 두 상태에서 Stage가 주인공인가?
4. PySide 메인과 나란히 놓고 “웹 복붙”이 아니라 “다음 세대 셸”로 보이는가?
5. 설정이 기본 상태에서 과하게 많은가? (많으면 Inspector가 실패한 것)

---

## 8. 적용 순서

1. 이 Visual Key 합의 (본 문서)
2. `tokens.css`만 먼저 반영·스토리/빈 셸에 색만 검증
3. 그다음 Sidebar / Stage / Inspector 구조 이식
4. 마지막에 마이크로 카피·단축키·커맨드 팔레트

예쁜 화면 한 방이 아니라, **키 → 토큰 → 셸 → 기능** 순서를 지킨다.

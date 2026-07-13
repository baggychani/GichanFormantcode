# Desktop Visual Key

이 문서는 Tauri/React 메인 창의 시각 언어와 정보 구조를 고정한다. 정식 PySide 진입점인
`main.py`에는 적용하지 않으며, 파일럿 진입점 `desktop_main.py`의 셸을 대상으로 한다.

## 1. 제품 인상

GichanFormant는 설정 폼이나 대시보드가 아니라 **정밀한 음향 분석 스튜디오**처럼 보여야 한다.

| 원칙 | 의미 |
| --- | --- |
| Editorial hierarchy | 제목, 상태, 다음 행동의 순서가 명확해야 한다 |
| Instrument precision | 수치와 설정은 조밀하되 읽기 쉬워야 한다 |
| Quiet depth | 색면, 선, 미세한 광원으로 깊이를 만들고 장식은 절제한다 |
| Visual evidence | 빈 화면에도 포먼트 궤적 등 제품 성격을 보여 주는 시각 요소가 있어야 한다 |
| Progressive control | 자주 쓰는 흐름은 전면에, 세부 설정은 우측 레일에 둔다 |

피해야 할 것:

- 같은 크기의 버튼을 한곳에 모은 실행 패널
- 라이브 미리보기가 화면 대부분을 차지하는 모니터형 배치
- 의미 없는 카드 반복, 과도한 glow, 여러 종류의 강조색 경쟁
- 상시 노출되는 큰 로그 패널

## 2. Visual Key와 테마

> **Deep charcoal analysis studio + mint instrument signal + restrained spectral color**

어두운 테마는 차콜 계열을 기본으로 한다. 밝은 테마는 청회색 작업면과 흰색 패널을 사용하되
정보 구조와 강조색의 의미는 동일하게 유지한다. mint는 주요 행동과 연결 상태에, blue와 violet은
데이터 시각화와 공간감을 만드는 데만 제한적으로 쓴다.

앱과 헤더의 브랜드 아이콘은 기존 PySide 앱과 같은 `assets/icon.ico`를 사용한다. 별도의 심볼을
새로 그리거나 Tauri 기본 아이콘으로 대체하지 않는다.

토큰의 단일 소스는 `desktop/src/styles/tokens.css`다. 컴포넌트에서 색상과 반경을 임의로
늘리기보다 semantic token을 먼저 추가한다.

## 3. 정보 구조

```text
Header       제품 정체성 / 현재 작업 공간 / 주요 행동
Source rail  데이터 추가 / 소스 목록 / 프로젝트 동작
Workspace    분석 개요 / 핵심 상태 / 보조 미리보기 / 다음 행동
Settings     분석 모델 / 축 / 처리 옵션
Status line  연결 및 현재 상태 한 줄
Toast        실패와 주의가 필요할 때만 일시 노출
```

시각적 무게는 `Workspace overview > analysis flow ≈ preview > side rails > chrome` 순서다.
미리보기는 결과를 빠르게 확인하는 보조 증거이며 화면의 주인공이 아니다.

## 4. 컴포넌트 원칙

- 헤더의 primary action은 하나만 둔다.
- 소스 추가는 버튼이 아니라 drag-and-drop 가능한 입력 영역처럼 보이게 한다.
- 플롯 유형은 이름, 수식, 요구 데이터가 함께 보이는 선택 행으로 표현한다.
- 분석 설정은 번호가 붙은 짧은 섹션으로 나누고 우측 레일을 접을 수 있게 한다.
- 빈 상태는 단순 문장 대신 제품 고유의 포먼트 시각화와 다음 행동을 함께 보여 준다.
- 오류는 7초 후 사라지는 toast로 전달하고, 지속 상태는 하단 한 줄에만 남긴다.

## 5. 타입과 밀도

- UI sans: `Pretendard`, `Noto Sans KR`, `Malgun Gothic`, `Segoe UI` 순서로 사용한다.
- 수치와 상태: `Cascadia Code` 또는 `Cascadia Mono`를 사용한다.
- 한국어 UI 문구를 기본으로 하며 영문 직역투 대신 실제 작업 흐름에 맞는 표현을 쓴다.
- 한국어에 대문자 스타일이나 넓은 자간을 적용하지 않는다. 기본 자간은 0으로 둔다.
- 설정 이름과 설명은 11px 미만으로 낮추지 않고, 핵심 설정 제목은 13px 이상으로 유지한다.
- 사이드 레일은 고정 폭, 중앙 작업 영역은 유동 폭으로 구성한다.

## 6. 상태와 모션

- 상태 의미는 색만으로 전달하지 않고 아이콘이나 텍스트를 함께 쓴다.
- hover와 패널 전환은 180ms 안팎의 opacity/transform/border 변화로 제한한다.
- 처리 중에는 레이아웃을 밀지 않는 상단 progress line을 사용한다.
- `prefers-reduced-motion`에서 애니메이션을 제거한다.
- 실제 앱 콘텐츠가 로드된 뒤에도 빈 상태와 동일한 레이아웃 크기를 유지한다.

## 7. 반응형 기준

- 넓은 화면: source rail / workspace / settings rail의 3열 구조.
- 중간 화면: workspace 내부 preview와 recipe를 세로 또는 압축 가로 배치.
- 좁은 화면: source rail + workspace의 2열, settings는 workspace 아래 전체 폭.
- 어떤 폭에서도 primary action, 데이터 추가, 설정 접근이 사라지면 안 된다.

## 8. 검수 질문

1. 첫 시선이 라이브 모니터가 아니라 현재 분석의 맥락과 다음 행동으로 향하는가?
2. 버튼의 수가 아니라 배치, 타이포그래피, 시각적 증거가 제품을 설명하는가?
3. 파일이 0개여도 완성된 분석 도구처럼 보이는가?
4. 설정을 접어도 핵심 흐름을 이해하고 실행할 수 있는가?
5. 오류가 없을 때 로그나 진단 UI가 시각적 공간을 차지하지 않는가?
6. `main.py`의 PySide 화면과 독립적으로 `desktop_main.py`에서만 실행되는가?

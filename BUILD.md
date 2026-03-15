# GichanFormant 빌드 안내

## PyInstaller 빌드

- 사용: `pyinstaller GichanFormant.spec`
- 결과: `dist/GichanFormant` (실행 파일)

## 아이콘 (macOS)

- **런타임(창 아이콘)**: macOS에서 `.icns`를 쓰려면 다음 중 한 곳에 두면 됩니다.
  - `resources/icon.icns`
  - 프로젝트 루트 `icon.icns`
- **.app 번들 아이콘**: `resources/icon.icns`가 있으면 spec 빌드 시 EXE(앱) 아이콘으로 자동 지정됩니다.

## 폰트 (플롯)

- `assets/fonts` 폴더가 있으면 빌드 시 번들에 포함됩니다 (Noto Sans 등 플롯용 폰트).
- 폴더가 없으면 spec이 해당 항목을 건너뜁니다.

# GichanFormant 빌드 안내

## PyInstaller 빌드

- 사용: `pyinstaller GichanFormant.spec`
- 결과: `dist/GichanFormant` (실행 파일)

## 배포 (Deployment)

1. 빌드된 `.exe` 파일을 [GichanFormant 배포용 레포지토리](https://github.com/baggychani/GichanFormant)의 **Releases** 섹션에 업로드합니다.
2. `config.py`의 `APP_VERSION`과 GitHub의 Tag 이름을 일치시켜야 업데이트 알림이 정상적으로 작동합니다.

## 아이콘 (macOS)

- **런타임(창 아이콘)**: macOS에서 `.icns`를 쓰려면 다음 중 한 곳에 두면 됩니다.
  - `resources/icon.icns`
  - 프로젝트 루트 `icon.icns`
- **.app 번들 아이콘**: `resources/icon.icns`가 있으면 spec 빌드 시 EXE(앱) 아이콘으로 자동 지정됩니다.

## 폰트 (플롯)

- `assets/fonts` 폴더가 있으면 빌드 시 번들에 포함됩니다 (Noto Sans 등 플롯용 폰트).
- 폴더가 없으면 spec이 해당 항목을 건너뜁니다.

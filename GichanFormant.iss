; ==============================================================================
; [환경 변수 정의] 
; ==============================================================================
#define MyAppName "GichanFormant"
#define MyAppVersion "2.3.4"
#define MyAppPublisher "Bae Gichan"

#define MyAppExeName "GichanFormant.exe" 
#define MyBasePath SourcePath
#define MyOutputDir GetEnv("USERPROFILE") + "\Desktop"
#define MyBuildDir "dist\GichanFormant"
; ==============================================================================

[Setup]
AppId={{F199E4AB-BB95-4C52-BF2D-B799E62A30E5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

InfoAfterFile={#MyOutputDir}\complete.txt

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir={#MyOutputDir}
OutputBaseFilename={#MyAppName}_v{#MyAppVersion}_Setup
SetupIconFile={#MyBasePath}\icon.ico

; === UI 및 에셋 설정 ===
WizardStyle=modern
DisableWelcomePage=no
DisableProgramGroupPage=yes
WizardImageFile={#MyBasePath}\assets\WizardImageFile.bmp
WizardSmallImageFile={#MyBasePath}\assets\WizardSmallImageFile.bmp

Compression=lzma2/ultra64
SolidCompression=yes
AppMutex={#MyAppName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
Type: files; Name: "{app}\sentry_opt_in.config"

[Files]
; 메인 프로그램 및 데이터
Source: "{#MyBasePath}\{#MyBuildDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyBasePath}\{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Sentry 설정 파일 (체크박스 동의 시에만 설치 폴더로 복사)
Source: "{#MyBasePath}\sentry_opt_in.config"; DestDir: "{app}"; Check: IsSentryAgreed; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; ==============================================================================
; [Code] 섹션: Sentry 동의 UI 구성 (플러그인 관련 내용 제거)
; ==============================================================================
[Code]
var
  SentryPage: TWizardPage;
  SentryMemo: TNewMemo;
  SentryCheckBox: TNewCheckBox;

procedure InitializeWizard;
begin
  // 1. 커스텀 페이지 생성
  SentryPage := CreateCustomPage(wpSelectTasks, '데이터 수집 동의', '프로그램 개선을 위한 오류 로그 전송에 동의해 주세요.');

  // 2. 안내 내용을 담을 글상자(Memo) 생성
  SentryMemo := TNewMemo.Create(WizardForm);
  SentryMemo.Parent := SentryPage.Surface;
  SentryMemo.Left := 0;
  SentryMemo.Top := 0;
  SentryMemo.Width := SentryPage.SurfaceWidth;
  SentryMemo.Height := SentryPage.SurfaceHeight - 35; // 체크박스 공간 확보
  SentryMemo.ScrollBars := ssVertical;
  SentryMemo.ReadOnly := True;
  SentryMemo.Color := clWindow;
  SentryMemo.Text := 'GichanFormant는 프로그램의 버그 수정 및 품질 개선을 위해' + #13#10 +
                     '오류 발생 시 익명의 크래시 로그를 자동 전송합니다.' + #13#10 + #13#10 +
                     '- 수집되는 정보: 오류 발생 시점의 스택 트레이스 등' + #13#10 +
                     '- 개인 식별 정보는 일절 수집되지 않습니다.' + #13#10 + #13#10 +
                     '동의를 거부하셔도 포먼트 분석 등의 핵심 기능은' + #13#10 +
                     '정상적으로 이용하실 수 있습니다.';

  // 3. 동의 체크박스 생성
  SentryCheckBox := TNewCheckBox.Create(WizardForm);
  SentryCheckBox.Parent := SentryPage.Surface;
  SentryCheckBox.Left := 0;
  SentryCheckBox.Top := SentryPage.SurfaceHeight - 20;
  SentryCheckBox.Width := SentryPage.SurfaceWidth;
  SentryCheckBox.Caption := '프로그램 개선을 위한 오류 로그 자동 전송에 동의합니다.';
  SentryCheckBox.Checked := True; // 기본값으로 체크
end;

function IsSentryAgreed: Boolean;
begin
  Result := SentryCheckBox.Checked;
end;
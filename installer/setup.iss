; ─────────────────────────────────────────────────────────────────────────────
;  Evony Bot — Inno Setup Installer Script
;
;  Requires Inno Setup 6+  https://jrsoftware.org/isinfo.php
;  Build via:  python build.py --installer
; ─────────────────────────────────────────────────────────────────────────────

[Setup]
AppName=Evony Bot
AppVersion=1.0.0
AppVerName=Evony Bot 1.0.0
AppPublisher=Evony Bot
AppPublisherURL=https://github.com/manicmanatee/testbot
DefaultDirName={autopf}\EvonyBot
DefaultGroupName=Evony Bot
AllowNoIcons=yes
; Output goes to installer/output/
OutputDir=output
OutputBaseFilename=EvonyBot_Setup_v1.0.0
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Require admin only when installing to Program Files
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
; Minimum Windows 10
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; ── Main application (built by PyInstaller) ──────────────────────────────
Source: "..\dist\evony_bot\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; ── Default config — only copy if user doesn't already have one ──────────
; (preserves edits on upgrade/reinstall)
Source: "..\config.yaml"; \
    DestDir: "{app}"; \
    Flags: onlyifdoesntexist

; ── Empty template directories so the folder structure is ready ──────────
Source: "..\templates\ui\.gitkeep";       DestDir: "{app}\templates\ui";       Flags: ignoreversion
Source: "..\templates\shields\.gitkeep";  DestDir: "{app}\templates\shields";   Flags: ignoreversion
Source: "..\templates\monsters\.gitkeep"; DestDir: "{app}\templates\monsters";  Flags: ignoreversion
Source: "..\templates\rally\.gitkeep";    DestDir: "{app}\templates\rally";     Flags: ignoreversion

[Dirs]
; Make sure the logs folder exists after install
Name: "{app}\logs"

[Icons]
; Start Menu
Name: "{group}\Evony Bot (Run)";              Filename: "{app}\evony_bot.exe"
Name: "{group}\Evony Bot (Capture Templates)"; Filename: "{app}\capture_templates.exe"
Name: "{group}\Edit Config";                   Filename: "{win}\notepad.exe"; Parameters: """{app}\config.yaml"""
Name: "{group}\{cm:UninstallProgram,Evony Bot}"; Filename: "{uninstallexe}"

; Optional desktop icon
Name: "{autodesktop}\Evony Bot"; Filename: "{app}\evony_bot.exe"; Tasks: desktopicon

[Run]
; Offer to open config after install
Filename: "{win}\notepad.exe"; \
    Parameters: """{app}\config.yaml"""; \
    Description: "Review config.yaml (set your emulator ADB address)"; \
    Flags: postinstall shellexec skipifsilent unchecked

; Offer to run the template capture tool
Filename: "{app}\capture_templates.exe"; \
    Description: "Capture UI templates now (required before running the bot)"; \
    Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove logs on uninstall (templates and config are user data — leave them)
Type: filesandordirs; Name: "{app}\logs"

[Code]
// Show a reminder page about Tesseract OCR and ADB requirements
procedure InitializeWizard;
var
  Page: TWizardPage;
  Memo: TNewMemo;
begin
  Page := CreateCustomPage(wpWelcome, 'Before You Begin', 'Prerequisites for Evony Bot');
  Memo := TNewMemo.Create(Page);
  Memo.Parent := Page.Surface;
  Memo.SetBounds(0, 0, Page.SurfaceWidth, Page.SurfaceHeight);
  Memo.ScrollBars := ssVertical;
  Memo.ReadOnly := True;
  Memo.Text :=
    'Evony Bot requires two external tools that are NOT bundled:' + #13#10 + #13#10 +
    '1. Android Platform Tools (ADB)' + #13#10 +
    '   Download: https://developer.android.com/tools/releases/platform-tools' + #13#10 +
    '   Add the extracted folder to your system PATH.' + #13#10 + #13#10 +
    '2. Tesseract OCR (needed for reading shield timers and coordinates)' + #13#10 +
    '   Download: https://github.com/UB-Mannheim/tesseract/wiki' + #13#10 +
    '   Install to C:\Program Files\Tesseract-OCR (default).' + #13#10 + #13#10 +
    'After installing:' + #13#10 +
    '  a) Edit config.yaml to set your emulator ADB address.' + #13#10 +
    '  b) Run capture_templates.exe to teach the bot your game UI.' + #13#10 +
    '  c) Run evony_bot.exe to start the automation.';
end;

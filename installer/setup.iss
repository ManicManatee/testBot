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
; config.yaml is excluded from the wildcard so an upgrade never overwrites
; the user's edited settings — it is installed separately below.
Source: "..\dist\evony_bot\*"; \
    DestDir: "{app}"; \
    Excludes: "config.yaml"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; ── Default config — only copy if user doesn't already have one ──────────
; (preserves edits on upgrade/reinstall)
Source: "..\config.yaml"; \
    DestDir: "{app}"; \
    Flags: onlyifdoesntexist

; ── Empty template directories so the folder structure is ready ──────────
Source: "..\templates\ui\.gitkeep";        DestDir: "{app}\templates\ui";        Flags: ignoreversion
Source: "..\templates\shields\.gitkeep";   DestDir: "{app}\templates\shields";    Flags: ignoreversion
Source: "..\templates\monsters\.gitkeep";  DestDir: "{app}\templates\monsters";   Flags: ignoreversion
Source: "..\templates\rally\.gitkeep";     DestDir: "{app}\templates\rally";      Flags: ignoreversion
Source: "..\templates\resources\.gitkeep"; DestDir: "{app}\templates\resources";  Flags: ignoreversion
Source: "..\templates\items\.gitkeep";     DestDir: "{app}\templates\items";      Flags: ignoreversion

[Dirs]
; Make sure the logs folder exists after install
Name: "{app}\logs"

[Icons]
; Start Menu
Name: "{group}\Evony Bot";                     Filename: "{app}\EvonyBot.exe"
Name: "{group}\Evony Bot (Capture Templates)"; Filename: "{app}\capture_templates.exe"
Name: "{group}\Evony Bot (CLI)";               Filename: "{app}\evony_bot.exe"
Name: "{group}\Edit Config";                   Filename: "{win}\notepad.exe"; Parameters: """{app}\config.yaml"""
Name: "{group}\{cm:UninstallProgram,Evony Bot}"; Filename: "{uninstallexe}"

; Optional desktop icon — points to the GUI
Name: "{autodesktop}\Evony Bot"; Filename: "{app}\EvonyBot.exe"; Tasks: desktopicon

[Run]
; Automated requirement setup — downloads adb + Tesseract into {app}\tools
; and configures the bot to use them.  Checked by default.
Filename: "{app}\deploy.exe"; \
    Description: "Run automated setup (installs ADB + Tesseract OCR)"; \
    Flags: postinstall skipifsilent

; Offer to launch the GUI after install
Filename: "{app}\EvonyBot.exe"; \
    Description: "Launch Evony Bot Manager (GUI)"; \
    Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Remove logs and auto-deployed tools on uninstall
; (templates and config are user data — leave them)
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\tools"

[Code]
// Explain what the automated setup will do
procedure InitializeWizard;
var
  Page: TWizardPage;
  Memo: TNewMemo;
begin
  Page := CreateCustomPage(wpWelcome, 'Before You Begin', 'How Evony Bot gets its requirements');
  Memo := TNewMemo.Create(Page);
  Memo.Parent := Page.Surface;
  Memo.SetBounds(0, 0, Page.SurfaceWidth, Page.SurfaceHeight);
  Memo.ScrollBars := ssVertical;
  Memo.ReadOnly := True;
  Memo.Text :=
    'Evony Bot needs two external tools — both are installed FOR YOU:' + #13#10 + #13#10 +
    '1. Android Platform Tools (ADB) — talks to your emulator' + #13#10 +
    '2. Tesseract OCR — reads timers and coordinates from the screen' + #13#10 + #13#10 +
    'On the final page, leave "Run automated setup" ticked and both tools' + #13#10 +
    'are downloaded and configured automatically (internet required).' + #13#10 +
    'You can re-run this any time from the GUI: Setup tab -> Run Auto-Deploy.' + #13#10 + #13#10 +
    'After setup:' + #13#10 +
    '  a) Edit config.yaml (or use the Settings tab) to set your emulator address.' + #13#10 +
    '  b) Run capture_templates.exe to teach the bot your game UI.' + #13#10 +
    '  c) Start the bot from EvonyBot.exe (GUI) or evony_bot.exe (CLI).' + #13#10 + #13#10 +
    'You provide the Android emulator (BlueStacks, LDPlayer, MuMu, Nox).';
end;

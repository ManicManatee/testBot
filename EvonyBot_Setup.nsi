; ============================================================================
;  Evony Bot  —  Windows Installer
;  NSIS 3.x + MUI2
;  Produced by:  makensis EvonyBot_Setup.nsi
; ============================================================================

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"

; ── Metadata ──────────────────────────────────────────────────────────────────
!define APP_NAME       "Evony Bot"
!define APP_VERSION    "1.1.0"
!define APP_PUBLISHER  "EvonyBot"
!define REG_APP        "Software\EvonyBot"
!define REG_UNINSTALL  "Software\Microsoft\Windows\CurrentVersion\Uninstall\EvonyBot"

Name          "${APP_NAME} ${APP_VERSION}"
OutFile       "EvonyBot_Setup_v${APP_VERSION}.exe"
InstallDir    "$PROGRAMFILES64\EvonyBot"
InstallDirRegKey HKLM "${REG_APP}" "InstallDir"
RequestExecutionLevel admin
Unicode True
ShowInstDetails show
ShowUninstDetails show

; ── Version block (visible in Windows → Properties → Details) ─────────────────
VIProductVersion "1.1.0.0"
VIAddVersionKey /LANG=0 "ProductName"     "${APP_NAME}"
VIAddVersionKey /LANG=0 "ProductVersion"  "${APP_VERSION}"
VIAddVersionKey /LANG=0 "FileVersion"     "${APP_VERSION}"
VIAddVersionKey /LANG=0 "CompanyName"     "${APP_PUBLISHER}"
VIAddVersionKey /LANG=0 "FileDescription"  "${APP_NAME} Installer"
VIAddVersionKey /LANG=0 "LegalCopyright"   "© 2026 ${APP_PUBLISHER}"

; ── MUI settings ──────────────────────────────────────────────────────────────
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── Helpers ───────────────────────────────────────────────────────────────────

; FindPython: searches registry + common paths.
; Sets $R0 = full path to python.exe, or "" if not found.
Function FindPython
  ; 1. Try registry (all-users install)
  ${ForEach} $9 3 12 + 1       ; Python versions 3.x
    ReadRegStr $R0 HKLM "SOFTWARE\Python\PythonCore\3.$9\InstallPath" ""
    ${If} $R0 != ""
      StrCpy $R0 "$R0python.exe"
      ${If} ${FileExists} $R0
        Return
      ${EndIf}
    ${EndIf}
  ${Next}

  ; 2. Try registry (current-user install)
  ${ForEach} $9 3 12 + 1
    ReadRegStr $R0 HKCU "SOFTWARE\Python\PythonCore\3.$9\InstallPath" ""
    ${If} $R0 != ""
      StrCpy $R0 "$R0python.exe"
      ${If} ${FileExists} $R0
        Return
      ${EndIf}
    ${EndIf}
  ${Next}

  ; 3. Common user-local install paths
  ${ForEach} $9 8 14 + 1
    StrCpy $R0 "$LOCALAPPDATA\Programs\Python\Python3$9\python.exe"
    ${If} ${FileExists} $R0
      Return
    ${EndIf}
  ${Next}

  ; 4. Ask cmd where python is (PATH lookup)
  nsExec::ExecToStack 'cmd /C "where python 2>nul"'
  Pop $0   ; return code
  Pop $R0  ; stdout
  ${If} $0 == 0
    ; Strip trailing whitespace / newline from the first line
    StrCpy $R0 $R0 -2
    ${If} ${FileExists} $R0
      Return
    ${EndIf}
  ${EndIf}

  StrCpy $R0 ""
FunctionEnd

; ── Installer sections ────────────────────────────────────────────────────────

Section "Core Files" SecCore
  SectionIn RO    ; cannot be deselected

  SetOutPath "$INSTDIR"

  ; ── Python source files ──────────────────────────────────────────────────
  File "main.py"
  File "gui.py"
  File "capture_templates.py"
  File "deploy.py"
  File "requirements.txt"
  File "config.example.yaml"

  ; config.yaml  — only install if absent (preserve edits on reinstall)
  ${IfNot} ${FileExists} "$INSTDIR\config.yaml"
    File "config.yaml"
  ${EndIf}

  ; ── bot package ──────────────────────────────────────────────────────────
  SetOutPath "$INSTDIR\bot"
  File /x "__pycache__" /x "*.pyc" "bot\*.py"

  ; ── Empty template folders (user fills via Capture Templates tool) ────────
  CreateDirectory "$INSTDIR\templates\ui"
  CreateDirectory "$INSTDIR\templates\shields"
  CreateDirectory "$INSTDIR\templates\monsters"
  CreateDirectory "$INSTDIR\templates\rally"
  CreateDirectory "$INSTDIR\templates\resources"
  CreateDirectory "$INSTDIR\templates\items"
  CreateDirectory "$INSTDIR\logs"

  SetOutPath "$INSTDIR"

  ; ── GUI launcher  (VBScript → no black console window) ───────────────────
  ;   Content written at install time so $INSTDIR is baked in.
  FileOpen  $0 "$INSTDIR\launch_gui.vbs" w
  FileWrite $0 "Set oShell = CreateObject($\"WScript.Shell$\")$\r$\n"
  FileWrite $0 "oShell.CurrentDirectory = $\"$INSTDIR$\"$\r$\n"
  FileWrite $0 "oShell.Run $\"pythonw gui.py$\", 0, False$\r$\n"
  FileClose $0

  ; ── CLI launcher  (console window — log output visible) ──────────────────
  FileOpen  $0 "$INSTDIR\launch_cli.bat" w
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "cd /d $\"%~dp0$\"$\r$\n"
  FileWrite $0 "python main.py$\r$\n"
  FileWrite $0 "pause$\r$\n"
  FileClose $0

  ; ── Capture-templates launcher ────────────────────────────────────────────
  FileOpen  $0 "$INSTDIR\capture_templates.bat" w
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "cd /d $\"%~dp0$\"$\r$\n"
  FileWrite $0 "python capture_templates.py$\r$\n"
  FileWrite $0 "pause$\r$\n"
  FileClose $0

  ; ── Re-run setup launcher (auto-deploy requirements again) ────────────────
  FileOpen  $0 "$INSTDIR\run_setup.bat" w
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "cd /d $\"%~dp0$\"$\r$\n"
  FileWrite $0 "python deploy.py$\r$\n"
  FileWrite $0 "pause$\r$\n"
  FileClose $0

  ; ── Auto-deploy all requirements ──────────────────────────────────────────
  ;   deploy.py installs the Python packages, downloads Android Platform
  ;   Tools (adb) into tools\, silently installs Tesseract OCR, and records
  ;   the resolved paths in tools\tools.json.  The installer runs elevated,
  ;   so the Tesseract child installer inherits admin rights.
  DetailPrint "Searching for Python..."
  Call FindPython

  ${If} $R0 == ""
    DetailPrint "Python not found — skipping automatic requirement deployment."
    MessageBox MB_OK|MB_ICONEXCLAMATION \
      "Python 3.10 or later was not found.$\n$\n\
      Install Python from https://www.python.org/downloads/$\n\
      (tick 'Add Python to PATH'), then run setup:$\n$\n\
      double-click deploy.py in$\n  $INSTDIR$\n\
      or open a terminal there and run:  python deploy.py"
  ${Else}
    DetailPrint "Python: $R0"
    DetailPrint "Running automated requirement deployment (deploy.py)..."
    DetailPrint "This installs pip packages, adb, and Tesseract OCR — please wait."
    nsExec::ExecToLog '"$R0" "$INSTDIR\deploy.py"'
    Pop $0
    ${If} $0 == 0
      DetailPrint "All requirements deployed and configured successfully."
    ${Else}
      DetailPrint "deploy.py returned code $0 — see log above."
      MessageBox MB_OK|MB_ICONEXCLAMATION \
        "Automatic requirement deployment reported a problem (exit $0).$\n$\n\
        You can re-run it any time:$\n\
        • from the GUI:  Setup tab → Run Auto-Deploy$\n\
        • from a terminal in $INSTDIR:  python deploy.py"
    ${EndIf}
  ${EndIf}

  ; ── Registry ─────────────────────────────────────────────────────────────
  WriteRegStr   HKLM "${REG_APP}" "InstallDir" "$INSTDIR"

  WriteRegStr   HKLM "${REG_UNINSTALL}" "DisplayName"     "${APP_NAME}"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "DisplayVersion"  "${APP_VERSION}"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "Publisher"       "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "InstallLocation" "$INSTDIR"
  WriteRegStr   HKLM "${REG_UNINSTALL}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "${REG_UNINSTALL}" "NoModify" 1
  WriteRegDWORD HKLM "${REG_UNINSTALL}" "NoRepair"  1

  ; ── Uninstaller ───────────────────────────────────────────────────────────
  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; ── Start Menu ────────────────────────────────────────────────────────────
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"

  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                 "wscript.exe" '"$INSTDIR\launch_gui.vbs"'

  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Capture Templates.lnk" \
                 "$INSTDIR\capture_templates.bat"

  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Evony Bot (CLI).lnk" \
                 "$INSTDIR\launch_cli.bat"

  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Re-run Setup.lnk" \
                 "$INSTDIR\run_setup.bat"

  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Edit Config.lnk" \
                 "notepad.exe" '"$INSTDIR\config.yaml"'

  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
                 "$INSTDIR\uninstall.exe"
SectionEnd

; ── Optional desktop shortcut ─────────────────────────────────────────────────
Section /o "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
                 "wscript.exe" '"$INSTDIR\launch_gui.vbs"'
SectionEnd

; ── Uninstall ─────────────────────────────────────────────────────────────────
Section "Uninstall"
  ; Source files
  Delete "$INSTDIR\main.py"
  Delete "$INSTDIR\gui.py"
  Delete "$INSTDIR\capture_templates.py"
  Delete "$INSTDIR\deploy.py"
  Delete "$INSTDIR\requirements.txt"
  Delete "$INSTDIR\config.example.yaml"

  ; Launchers
  Delete "$INSTDIR\launch_gui.vbs"
  Delete "$INSTDIR\launch_cli.bat"
  Delete "$INSTDIR\capture_templates.bat"
  Delete "$INSTDIR\run_setup.bat"
  Delete "$INSTDIR\uninstall.exe"

  ; Directories (bot + logs + auto-deployed tools —
  ;              user's templates + config are preserved)
  RMDir /r "$INSTDIR\bot"
  RMDir /r "$INSTDIR\logs"
  RMDir /r "$INSTDIR\tools"
  RMDir    "$INSTDIR"       ; only removes if empty

  ; Shortcuts
  RMDir /r "$SMPROGRAMS\${APP_NAME}"
  Delete   "$DESKTOP\${APP_NAME}.lnk"

  ; Registry
  DeleteRegKey HKLM "${REG_UNINSTALL}"
  DeleteRegKey HKLM "${REG_APP}"
SectionEnd

@echo off
REM ─────────────────────────────────────────────────────────────
REM  Evony Bot — One-click setup for Windows
REM  Downloads and configures every requirement, then you're done.
REM ─────────────────────────────────────────────────────────────
setlocal

echo.
echo  ============================================================
echo    Evony Bot - Automated Setup
echo  ============================================================
echo.

REM Find a Python launcher
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
    goto :run
)
where python >nul 2>nul
if %errorlevel%==0 (
    set "PY=python"
    goto :run
)

echo  [X] Python was not found on this machine.
echo      Install Python 3.10+ from https://www.python.org/downloads/
echo      (tick "Add Python to PATH" during install), then run setup.bat again.
echo.
pause
exit /b 1

:run
echo  Using: %PY%
echo.
%PY% deploy.py %*
set "RC=%errorlevel%"
echo.
if "%RC%"=="0" (
    echo  Setup complete. Launch the bot with:  %PY% gui.py
) else (
    echo  Setup reported problems (exit %RC%). See the messages above.
)
echo.
pause
exit /b %RC%

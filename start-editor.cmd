@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if not errorlevel 1 (
    uv run --locked python pipeline/local_editor.py --open-browser %*
    goto finish
)
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    "%USERPROFILE%\.local\bin\uv.exe" run --locked python pipeline/local_editor.py --open-browser %*
    goto finish
)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" pipeline/local_editor.py --open-browser %*
    goto finish
)
echo Bitte zuerst uv installieren. Anleitung: https://docs.astral.sh/uv/getting-started/installation/
pause
exit /b 1
:finish
set "editor_exit=%ERRORLEVEL%"
if not "%editor_exit%"=="0" pause
exit /b %editor_exit%

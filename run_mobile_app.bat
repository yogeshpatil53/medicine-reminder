@echo off
title MedRemind - Mobile PWA Server
cd /d "%~dp0"
echo ========================================================
echo   Starting MedRemind Mobile Web & PWA Server...
echo ========================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" server.py
) else (
    python server.py
)
pause

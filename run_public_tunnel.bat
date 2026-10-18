@echo off
title MedRemind - Public Mobile Link (Anywhere Access)
echo ========================================================
echo   Generating a Public HTTPS Link for MedRemind...
echo   (Works from ANY mobile phone on cellular 4G/5G data)
echo ========================================================
echo.
cmd /c npx -y localtunnel --port 5000
pause

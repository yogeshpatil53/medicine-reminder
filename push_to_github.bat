@echo off
title Push MedRemind to GitHub
echo ========================================================
echo   Push MedRemind to Your GitHub Repository
echo ========================================================
echo.
echo Make sure you have created an empty repository on GitHub:
echo https://github.com/new
echo.
set /p REPO_URL="Enter your GitHub Repository URL (e.g. https://github.com/yogeshpatil53/medicine-reminder.git): "

if "%REPO_URL%"=="" (
    echo Error: No URL entered!
    pause
    exit /b 1
)

echo.
echo Adding remote origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo.
echo Pushing branch 'main' to GitHub...
git push -u origin main

echo.
echo ========================================================
echo Push complete! Check your repository on GitHub.
echo ========================================================
pause

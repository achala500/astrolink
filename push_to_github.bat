@echo off
title Push AstroLink to GitHub
color 0b
echo ========================================================
echo       Pushing AstroLink to GitHub (achala500/astrolink)
echo ========================================================
echo.
cd /d "%~dp0"
git push -u origin main --force
echo.
if %ERRORLEVEL% EQU 0 (
    color 0a
    echo [SUCCESS] Code successfully pushed to GitHub!
    echo Check actions at: https://github.com/achala500/astrolink/actions
) else (
    color 0c
    echo [ERROR] Push failed. If prompted, please authenticate via your browser.
)
echo.
pause

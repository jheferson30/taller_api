@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   SUBIR CAMBIOS A GITHUB
echo ============================================
echo.

git add -A
git status
echo.

set /p MENSAJE="Mensaje del commit: "
if "%MENSAJE%"=="" set MENSAJE=actualizacion

git commit -m "%MENSAJE%"
git push origin main

echo.
echo Listo. Cambios subidos a GitHub.
pause

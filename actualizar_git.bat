@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   ACTUALIZAR DESDE GITHUB
echo ============================================
echo.

git fetch origin
git status
echo.

git pull origin main --allow-unrelated-histories

echo.
echo Listo. Proyecto actualizado desde GitHub.
pause

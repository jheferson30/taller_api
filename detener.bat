@echo off
taskkill /F /IM uvicorn.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
echo Servidor detenido.
timeout /t 2 >nul

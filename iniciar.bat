@echo off
chcp 65001 >nul
echo ============================================
echo   SISTEMA TALLER MECANICO
echo ============================================
echo.

REM Obtener IP local de la maquina
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%

echo IP de esta PC: %LOCAL_IP%
echo.
echo Acceso desde navegador:  http://%LOCAL_IP%:8000
echo Acceso desde celulares:  http://%LOCAL_IP%:8000
echo.
echo IMPORTANTE: Los celulares deben estar en la misma red WiFi.
echo.
echo Iniciando servidor... (no cierres esta ventana)
echo Para detener el servidor presiona Ctrl+C
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000

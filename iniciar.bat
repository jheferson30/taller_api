@echo off
chcp 65001 >nul
echo ============================================
echo   SISTEMA TALLER MECANICO - PULGA Fi
echo ============================================
echo.

REM Ir a la carpeta donde esta este .bat
cd /d "%~dp0"

REM Crear entorno virtual si no existe
if not exist "venv\Scripts\activate.bat" (
    echo Creando entorno virtual...
    python -m venv venv
    echo Instalando dependencias...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Obtener IP local
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo IP de esta PC:           http://%LOCAL_IP%:8000
echo Acceso desde celulares:  http://%LOCAL_IP%:8000
echo.
echo IMPORTANTE: Los celulares deben estar en la misma red WiFi.
echo.
echo Iniciando servidor... (no cierres esta ventana)
echo Para detener el servidor presiona Ctrl+C
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

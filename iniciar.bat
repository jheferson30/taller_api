@echo off
chcp 65001 >nul
echo ============================================
echo   SISTEMA TALLER MECANICO - PULGA Fi
echo ============================================
echo.

REM Ir a la carpeta donde esta este .bat
cd /d "%~dp0"

REM Activar entorno virtual
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Creando entorno virtual...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Instalando dependencias backend...
    pip install -r requirements.txt
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
echo Frontend web:            http://localhost:5173
echo.

REM Iniciar frontend en ventana separada
echo Iniciando frontend...
start "Frontend - Taller" cmd /k "cd /d %~dp0frontend && npm run dev"

REM Esperar un momento
timeout /t 2 /nobreak >nul

echo Iniciando backend...
echo Para detener presiona Ctrl+C
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

@echo off
chcp 65001 >nul
echo ============================================
echo   INSTALADOR - SISTEMA TALLER MECANICO
echo ============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado.
    echo Descargalo desde: https://www.python.org/downloads/
    echo Asegurate de marcar "Add Python to PATH" al instalar.
    pause
    exit /b 1
)
echo [OK] Python encontrado.

REM Verificar Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js no esta instalado.
    echo Descargalo desde: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js encontrado.

REM Verificar PostgreSQL
psql --version >nul 2>&1
if errorlevel 1 (
    echo [AVISO] psql no encontrado en PATH. Asegurate de que PostgreSQL este instalado y corriendo.
    echo Si ya esta instalado, continua de todas formas.
    pause
)

echo.
echo [1/4] Instalando dependencias de Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias Python.
    pause
    exit /b 1
)
echo [OK] Dependencias Python instaladas.

echo.
echo [2/4] Compilando el frontend web...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Fallo npm install en frontend.
    cd ..
    pause
    exit /b 1
)
call npm run build
if errorlevel 1 (
    echo [ERROR] Fallo la compilacion del frontend.
    cd ..
    pause
    exit /b 1
)
cd ..
echo [OK] Frontend compilado.

echo.
echo [3/4] Creando archivo de configuracion .env...
if not exist .env (
    echo PDF_PASSWORD=taller2024> .env
    echo ADMIN_PASSWORD=taller2024>> .env
    echo DATABASE_URL=postgresql+psycopg2://postgres:123456@localhost:5432/taller_db?client_encoding=utf8>> .env
    echo [OK] Archivo .env creado con valores por defecto.
    echo IMPORTANTE: Edita el archivo .env para cambiar las contrasenas.
) else (
    echo [OK] Archivo .env ya existe, no se sobreescribe.
)

echo.
echo [4/4] Creando carpetas necesarias...
if not exist uploads mkdir uploads
if not exist uploads\fotos mkdir uploads\fotos
if not exist uploads\compras mkdir uploads\compras
echo [OK] Carpetas creadas.

echo.
echo ============================================
echo   INSTALACION COMPLETADA
echo ============================================
echo.
echo Proximos pasos:
echo  1. Asegurate de que PostgreSQL este corriendo
echo  2. Crea la base de datos: createdb -U postgres taller_db
echo  3. Edita .env si quieres cambiar contrasenas
echo  4. Ejecuta INICIAR.bat para arrancar el sistema
echo.
pause

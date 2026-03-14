@echo off
chcp 65001 >nul
echo ============================================
echo   CONFIGURAR IP Y COMPILAR APK
echo ============================================
echo.

REM Detectar IP local automaticamente
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%

echo IP detectada automaticamente: %LOCAL_IP%
echo.
set /p CONFIRMAR_IP="Presiona Enter para usar esta IP, o escribe otra IP: "
if not "%CONFIRMAR_IP%"=="" set LOCAL_IP=%CONFIRMAR_IP%

echo.
echo Usando IP: %LOCAL_IP%
echo.

REM Reemplazar la IP en api.js
powershell -Command "(Get-Content src\api.js) -replace 'http://[0-9.]+:8000', 'http://%LOCAL_IP%:8000' | Set-Content src\api.js"
echo [OK] IP actualizada en src/api.js

echo.
echo Opciones de compilacion:
echo  1. Build local (necesita Android Studio + JDK)
echo  2. Build en la nube con EAS (necesita cuenta Expo)
echo.
set /p OPCION="Elige opcion (1 o 2): "

if "%OPCION%"=="1" (
    echo.
    echo Compilando APK localmente...
    npx expo run:android --variant release
) else (
    echo.
    echo Compilando APK en la nube con EAS...
    echo Asegurate de estar logueado: eas login
    npx eas build --platform android --profile preview
)

echo.
pause

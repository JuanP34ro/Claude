@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ORELLANA ATLAS - Prueba desde el movil
echo Conecta PC e iPhone a la misma red de confianza.
echo Este modo permite que otros dispositivos de la red abran la app.
echo NO abras puertos del router. Cierra esta ventana al terminar.
echo.
choice /C SN /N /M "Continuar en red local [S/N]? "
if errorlevel 2 exit /b
py -3 --version >nul 2>&1
if %errorlevel%==0 (
    py -3 server.py --lan
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Necesitas Python 3.10 o posterior instalado en el PC.
    ) else (
        python server.py --lan
    )
)
pause

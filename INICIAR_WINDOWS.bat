@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 --version >nul 2>&1
if %errorlevel%==0 (
    py -3 server.py
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo No se encuentra Python 3. Abre index.html directamente para usar el modo sin servidor.
        echo El servidor local necesita Python 3.10 o posterior.
    ) else (
        python server.py
    )
)
pause

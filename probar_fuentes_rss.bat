@echo off
cd /d "%~dp0"
echo Probando fuentes de noticias (tarda 1 o 2 minutos)...
echo.
python probar_fuentes_rss.py
echo.
pause

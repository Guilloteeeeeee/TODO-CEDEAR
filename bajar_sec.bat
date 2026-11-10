@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install requests --quiet
echo.
echo Sumando al archivo historico los datos viejos de la SEC (tarda unos 10 a 15 minutos; no cierres la ventana)...
python bajar_sec.py %*
echo.
pause

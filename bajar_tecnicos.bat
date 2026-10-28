@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install yfinance pandas numpy requests --quiet
echo.
echo Bajando el historial de precios para los parametros tecnicos (tarda unos 2 a 4 minutos; no cierres la ventana)...
python bajar_tecnicos.py %*
echo.
pause

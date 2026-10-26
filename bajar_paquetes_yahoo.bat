@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install yfinance pandas numpy requests --quiet
echo.
echo Bajando los datos de Yahoo de cada empresa (tarda unos 20 a 30 minutos; no cierres la ventana)...
python bajar_paquetes_yahoo.py %*
echo.
pause

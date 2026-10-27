@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install yfinance pandas numpy requests deep-translator --quiet
echo.
echo Bajando los datos de Yahoo de cada ETF (tarda unos 3 a 5 minutos; no cierres la ventana)...
python bajar_etfs_yahoo.py %*
echo.
pause

@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install yfinance pandas numpy --quiet
echo.
echo Bajando la historia completa de precios, dividendos y splits de todas las empresas y ETFs (tarda unos 10 a 20 minutos; no cierres la ventana)...
python bajar_historico.py %*
echo.
pause

@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install yfinance pandas numpy --quiet
echo.
echo Bajando la historia completa de precios, dividendos y splits de todas las empresas y ETFs (tarda unos 10 a 20 minutos; no cierres la ventana)...
python bajar_historico.py %*
echo.
echo Ahora los dividendos de las empresas de afuera en su propia moneda (unos 3 a 5 minutos)...
python bajar_dividendos_locales.py
echo.
pause

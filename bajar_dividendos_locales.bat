@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install yfinance pandas numpy --quiet
echo.
echo Bajando los dividendos de las empresas de afuera en su propia moneda y la historia de las monedas (unos 3 a 5 minutos)...
python bajar_dividendos_locales.py %*
echo.
pause

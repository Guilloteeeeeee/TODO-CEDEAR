@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install yfinance pandas numpy --quiet
echo.
echo Bajando las estimaciones de analistas (una vez por trimestre, despues de los balances; unos 5 a 10 minutos)...
python bajar_estimaciones.py %*
echo.
pause

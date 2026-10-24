@echo off
echo Instalando dependencias...
pip install pandas numpy yfinance deep-translator --quiet
echo.
echo Bajando la ficha de cada empresa de Yahoo Finance (tarda unos minutos, no cierres la ventana)...
python bajar_fichas.py
echo.
pause

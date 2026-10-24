@echo off
echo Instalando dependencias...
pip install pandas numpy yfinance --quiet
echo.
echo Controlando ratios y precios en pesos de los CEDEARs (tarda un minuto)...
python probar_cedears.py
echo.
pause

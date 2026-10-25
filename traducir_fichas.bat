@echo off
echo Instalando dependencias...
pip install pandas numpy yfinance deep-translator --quiet
echo.
echo Traduciendo al castellano las descripciones que faltan en data\fichas.json (no vuelve a bajar nada de Yahoo)...
python bajar_fichas.py
echo.
pause

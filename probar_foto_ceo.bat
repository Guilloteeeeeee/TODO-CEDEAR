@echo off
cd /d "%~dp0"
python -m pip install -q yfinance
python probar_foto_ceo.py %*
echo.
echo Listo: se guardo resultados_foto_ceo.txt
pause

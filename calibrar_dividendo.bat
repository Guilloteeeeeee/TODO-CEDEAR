@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install yfinance pandas numpy --quiet
echo.
echo Calculando el Score de Seguridad del Dividendo y comparandolo con Simply Safe Dividends (unos minutos; no cierres la ventana)...
python calibrar_dividendo.py %*
echo.
pause

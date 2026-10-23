@echo off
echo Instalando dependencias...
pip install pandas numpy requests beautifulsoup4 --quiet
echo.
echo Bajando P/S y multiplos (una pagina por empresa, tarda unos minutos)...
python probar_ps.py
echo.
pause

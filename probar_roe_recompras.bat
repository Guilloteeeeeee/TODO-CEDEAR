@echo off
echo Instalando dependencias...
pip install pandas numpy requests beautifulsoup4 --quiet
echo.
echo Bajando ROE y recompras (una pagina por empresa, tarda unos minutos)...
python probar_roe_recompras.py
echo.
pause

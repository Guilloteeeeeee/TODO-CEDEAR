@echo off
echo Instalando dependencias...
pip install pandas numpy requests beautifulsoup4 --quiet
echo.
echo Bajando ROE y recompras de las empresas de Bancos y seguros (2 o 3 minutos)...
python probar_roe_recompras.py bancos
echo.
pause

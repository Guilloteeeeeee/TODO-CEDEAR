@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install requests --quiet
echo.
python probar_fuentes_noticias.py %*
echo.
pause

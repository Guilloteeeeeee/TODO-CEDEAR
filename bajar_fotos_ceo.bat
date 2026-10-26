@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install requests --quiet
echo.
echo Buscando la foto del CEO de cada empresa en Wikipedia (usa lo ya bajado de Yahoo; tarda unos minutos)...
python bajar_fotos_ceo.py %*
echo.
pause

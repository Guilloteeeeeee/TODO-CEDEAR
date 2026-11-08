@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install requests --quiet
echo.
echo Prueba piloto de la SEC: baja los informes anuales de 10 empresas y los compara con Yahoo (no cambia nada de la app)...
python piloto_sec.py %*
echo.
pause

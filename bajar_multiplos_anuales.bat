@echo off
echo Instalando dependencias...
pip install pandas numpy requests beautifulsoup4 --quiet
echo.
echo Bajando los multiplos de cada anio (una pagina por empresa, tarda unos 10 minutos; no cierres la ventana)...
python bajar_multiplos_anuales.py
echo.
pause

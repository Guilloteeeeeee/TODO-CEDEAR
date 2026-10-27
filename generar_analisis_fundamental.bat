@echo off
cd /d "%~dp0"
echo Instalando dependencias...
pip install anthropic --quiet
echo.
if "%ANTHROPIC_API_KEY%"=="" (
  echo Pegá tu clave de la API de Anthropic ^(empieza con sk-ant-^) y apretá Enter.
  set /p ANTHROPIC_API_KEY=Clave: 
)
echo.
echo Generando el Analisis Fundamental ^(solo las empresas que todavia no lo tienen; usa --todas para rehacer todas^)...
python generar_analisis_fundamental.py %*
echo.
pause

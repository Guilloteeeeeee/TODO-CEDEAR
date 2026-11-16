"""v1.5.70: corre TODAS las pruebas de tests/ y dice «todo verde» o qué falló. Uso: python correr_pruebas.py
Una prueba falla si termina con error o si su última línea dice «MAL n» con n > 0. Termina con error si alguna falló."""
import glob
import os
import re
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
fallas = []
for ruta in sorted(glob.glob(os.path.join(AQUI, "tests", "test_*.py"))):
    nombre = os.path.basename(ruta)
    t0 = time.time()
    p = subprocess.run([sys.executable, ruta], cwd=AQUI, capture_output=True, text=True, timeout=900)
    salida = (p.stdout or "").strip().splitlines()
    ult = salida[-1] if salida else ""
    m = re.search(r"MAL\s+(\d+)", ult)
    mal = int(m.group(1)) if m else None
    ok = p.returncode == 0 and (mal in (None, 0))
    print(f"{'OK ' if ok else 'MAL'}  {nombre:45s} {time.time() - t0:5.1f} s  {ult[:60]}")
    if not ok:
        fallas.append((nombre, [x for x in salida if x.startswith("FALLA")][:5] or (p.stderr or "").strip().splitlines()[-3:]))
print()
if fallas:
    print(f"FALLARON {len(fallas)} archivos:")
    for n, det in fallas:
        print(" -", n)
        for d in det:
            print("     ", d)
    sys.exit(1)
print("Todo verde.")

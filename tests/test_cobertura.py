"""Control de cobertura BYMA: ningun CEDEAR de la lista puede quedar fuera de la app sin motivo. Correr: python tests/test_cobertura.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import control_cobertura as cc

ok = mal = 0
def chk(c, m):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("MAL:", m)

byma, cargadas, motivo, sin_motivo = cc.calcular()
chk(not sin_motivo, f"CEDEARs de BYMA sin motivo: {sin_motivo}")
chk(len(cargadas) + len(motivo) + len(sin_motivo) == len(byma), "las cuentas no cierran")
chk(len(byma) >= 446, "la lista de BYMA quedo corta")
todos = [t for v in cc.PENDIENTES.values() for t in v] + [t for v in cc.EXCLUIDAS.values() for t in v]
chk(len(todos) == len(set(todos)), "un simbolo figura en dos listas")
chk(not (set(todos) & set(cargadas)), f"figuran como pendientes/excluidos pero ya estan cargados: {sorted(set(todos) & set(cargadas))}")
chk(not [t for t in todos if t not in byma], f"simbolos que no estan en la lista de BYMA: {[t for t in todos if t not in byma]}")
for t in ("F", "BIIB", "WFC", "BNG", "SNDK", "AMX", "SPCX", "HOOD", "KB"):
    chk(t in cargadas, f"{t} deberia estar cargado")
chk("AAP" in motivo and motivo["AAP"].startswith("Pendiente"), "AAP (tanda 3 en adelante) debe figurar como pendiente")
print(f"OK {ok} MAL {mal}")
sys.exit(1 if mal else 0)

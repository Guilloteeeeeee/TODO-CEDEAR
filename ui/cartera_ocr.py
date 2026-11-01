"""Lectura de capturas de pantalla de la cartera (v1.4.5). Usa RapidOCR (opcional): si no está instalado, la app sigue funcionando y pide Excel, PDF o texto.
El OCR se equivoca con facilidad (puntos y comas, letras parecidas), por eso lo que se lee SIEMPRE pasa por una tabla que la persona revisa y corrige a mano antes de analizar.
La imagen se procesa en memoria y no se guarda."""
import io

_MOTOR = None


def disponible():
    try:
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _motor():
    global _MOTOR
    if _MOTOR is None:
        from rapidocr_onnxruntime import RapidOCR
        _MOTOR = RapidOCR()
    return _MOTOR


def _renglones(bloques):
    """Agrupa los textos que el OCR encontró en renglones (por altura) y los ordena de izquierda a derecha."""
    items = []
    for b in bloques or []:
        try:
            caja, txt = b[0], str(b[1]).strip()
            ys = [p[1] for p in caja]
            xs = [p[0] for p in caja]
        except Exception:  # noqa: BLE001
            continue
        if txt:
            items.append((sum(ys) / 4.0, max(ys) - min(ys), min(xs), txt))
    items.sort()
    filas, actual, ref, alto = [], [], None, 0
    for yc, h, x, t in items:
        if ref is not None and abs(yc - ref) <= max(8.0, 0.6 * alto):
            actual.append((x, t))
        else:
            if actual:
                filas.append(actual)
            actual, ref, alto = [(x, t)], yc, h
    if actual:
        filas.append(actual)
    return [" ".join(t for _, t in sorted(f)) for f in filas]


def leer_imagen(datos):
    """Lista de renglones de texto de la imagen. Lanza RuntimeError si no se puede leer."""
    if not disponible():
        raise RuntimeError("La lectura de capturas no está disponible en este momento.")
    try:
        import numpy as np
        from PIL import Image
        img = Image.open(io.BytesIO(datos)).convert("RGB")
        if max(img.size) > 2600:
            img.thumbnail((2600, 2600))
        res, _ = _motor()(np.array(img))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("No pude leer esa imagen.") from e
    return _renglones(res)


def posiciones_de_imagen(datos, C):
    """(posiciones, notas) a partir de una captura. Usa el mismo lector que el texto pegado."""
    lineas = leer_imagen(datos)
    if not lineas:
        return [], ["No encontré texto en la imagen."]
    pos, notas = C.leer_texto_info("\n".join(lineas))
    return pos, list(notas)

"""Modo oscuro (v1.4.2). Se prende desde el menú (las 3 rayitas) con el interruptor "Modo oscuro" y vale mientras dure la sesión; con ?tema=oscuro en el link arranca prendido.
Cómo funciona: en vez de reescribir los cientos de colores de la app, se invierte la luminosidad de toda la página (fondo claro -> oscuro, texto oscuro -> claro) manteniendo
los tonos (el verde sigue verde y el rojo, rojo), y se les devuelve su aspecto original a lo que no debe invertirse: imágenes y logos, banderas, íconos y la franja de arriba.
Se apaga igual que se prende: sin el interruptor, la página queda exactamente como estaba."""

CSS_OSCURO = (
    "html{filter:invert(1) hue-rotate(180deg);background:#fff}"
    # lo que NO se invierte: imágenes, logos, banderas, íconos con fondo propio, videos y la franja de arriba con el nombre
    "img,picture,video,svg image,[data-testid='stImage'],.mc-band,.mc-fv,.mc-lg,.mc-flag,[class*='bandera'],[style*='background-image']{filter:invert(1) hue-rotate(180deg)}"
    # una imagen dentro de otra cosa ya revertida no se vuelve a revertir
    ".mc-band img,.mc-band [style*='background-image'],[data-testid='stImage'] img{filter:none}"
    "::selection{background:#93c5fd}"
)


def css_oscuro(activo):
    return f"<style>{CSS_OSCURO}</style>" if activo else ""

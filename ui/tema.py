"""Modo oscuro (v1.4.2). Se prende desde el menú (las 3 rayitas) con el interruptor "Modo oscuro" y vale mientras dure la sesión; con ?tema=oscuro en el link arranca prendido.
Cómo funciona: en vez de reescribir los cientos de colores de la app, se invierte la luminosidad de toda la página (fondo claro -> oscuro, texto oscuro -> claro) manteniendo
los tonos (el verde sigue verde y el rojo, rojo), y se les devuelve su aspecto original a lo que no debe invertirse: imágenes y logos, banderas, íconos y la franja de arriba.
Se apaga igual que se prende: sin el interruptor, la página queda exactamente como estaba."""

CSS_OSCURO = (
    "html.mc-oscuro{filter:invert(1) hue-rotate(180deg);background:#fff}"
    # lo que NO se invierte: imágenes, logos, banderas, íconos con fondo propio, videos y la franja de arriba con el nombre
    "html.mc-oscuro :is(img,picture,video,svg image,[data-testid='stImage'],.mc-band,.mc-fv,.mc-lg,.mc-flag,[class*='bandera'],[style*='background-image']){filter:invert(1) hue-rotate(180deg)}"
    # una imagen dentro de otra cosa ya revertida no se vuelve a revertir
    "html.mc-oscuro :is(.mc-band img,.mc-band [style*='background-image'],[data-testid='stImage'] img){filter:none}"
    "::selection{background:#93c5fd}"
)


# Botón sol / luna de la franja negra (a la izquierda del toro): la luna se ve en modo claro; el sol, en modo oscuro.
CSS_BOTON = (".mc-tema{background:none;border:0;cursor:pointer;color:#e5e7eb;padding:8px;display:flex;align-items:center;flex:none;border-radius:10px}"
             ".mc-tema:hover{background:rgba(255,255,255,.12)}.mc-tema svg{width:22px;height:22px}.mc-tema .sol{display:none}"
             "html.mc-oscuro .mc-tema .sol{display:block}html.mc-oscuro .mc-tema .luna{display:none}")

BOTON_HTML = ('<button type="button" class="mc-tema" title="Modo claro / oscuro" aria-label="Cambiar entre modo claro y modo oscuro">'
              '<svg class="luna" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
              '<svg class="sol" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/>'
              '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>')

# Se guarda la elección en el navegador (localStorage); con ?tema=oscuro en el link arranca en oscuro. El clic se escucha en todo el documento, así sobrevive a que Streamlit redibuje la franja.
SCRIPT_TEMA = ("(function(){if(window.__mcTema)return;window.__mcTema=1;var d=document.documentElement,v=null;try{v=localStorage.getItem('mc-tema')}catch(e){}"
               "if(/[?&]tema=(oscuro|dark)/.test(location.search))v='1';if(v==='1')d.classList.add('mc-oscuro');"
               "document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('.mc-tema');if(!b)return;var o=!d.classList.contains('mc-oscuro');"
               "d.classList.toggle('mc-oscuro',o);try{localStorage.setItem('mc-tema',o?'1':'0')}catch(x){}});})();")


def css_oscuro(activo=True):
    return f"<style>{CSS_OSCURO}{CSS_BOTON}</style>"

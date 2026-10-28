"""Flecha "hay más abajo" (v1.2.71), en TODAS las páginas de la app: un triángulo chico que rebota abajo y al centro de la pantalla mientras falta contenido
por ver, y desaparece cuando se llega al final. Al tocarlo baja casi una pantalla. Streamlit no deja poner JavaScript en st.markdown, así que se carga con un
componente de altura 0 que le pone el script y el estilo a la página (solo si no estaban). Si algo falla (otro navegador, otra versión de Streamlit), no pasa
nada: la flecha simplemente no aparece."""
import streamlit.components.v1 as components

CSS_OCULTAR = ('div[data-testid="stElementContainer"]:has(> iframe[height="0"]),div[data-testid="stElementContainer"]:has(iframe[title="st.iframe"][height="0"]),'
               'div.stCustomComponentV1[height="0"]{position:absolute!important;height:0!important;overflow:hidden!important;margin:0!important;padding:0!important}')

_JS = r"""
<script>
(function(){
  try{
    var d=window.parent.document, w=window.parent;
    if(d.getElementById('tc-flecha-js')) return;
    var s=d.createElement('script'); s.id='tc-flecha-js';
    s.textContent='('+function(){
      var css='#tc-flecha{position:fixed;left:50%;bottom:calc(14px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);z-index:50;width:44px;height:44px;border-radius:50%;'
        +'border:1px solid #cbd5e1;background:rgba(255,255,255,.94);box-shadow:0 4px 14px rgba(15,23,42,.22);cursor:pointer;display:none;align-items:center;justify-content:center;padding:0}'
        +'#tc-flecha.on{display:flex;animation:tcrebote 1.6s ease-in-out infinite}#tc-flecha svg{width:22px;height:22px;stroke:#0f172a;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}'
        +'@keyframes tcrebote{0%,100%{transform:translateX(-50%) translateY(0)}50%{transform:translateX(-50%) translateY(6px)}}'
        +'@media (prefers-reduced-motion:reduce){#tc-flecha.on{animation:none}}';
      var st=document.createElement('style'); st.textContent=css; document.head.appendChild(st);
      var b=document.createElement('button'); b.id='tc-flecha'; b.type='button'; b.setAttribute('aria-label','Hay más contenido más abajo: bajar');
      b.innerHTML='<svg viewBox="0 0 24 24"><polyline points="5 9 12 16 19 9"></polyline></svg>'; document.body.appendChild(b);
      function cont(){ return document.querySelector('[data-testid="stMain"]')||document.querySelector('section.main')||document.scrollingElement||document.documentElement; }
      function falta(){ var c=cont(); return c.scrollHeight-c.scrollTop-c.clientHeight; }
      function ver(){ try{ b.classList.toggle('on', falta()>120); }catch(e){} }
      b.addEventListener('click',function(){ var c=cont(); c.scrollBy({top:Math.round(c.clientHeight*0.85),behavior:'smooth'}); });
      document.addEventListener('scroll',ver,true); window.addEventListener('resize',ver); setInterval(ver,700); ver();
    }.toString()+')();';
    d.head.appendChild(s);
  }catch(e){}
})();
</script>
"""


def poner_flecha():
    """Carga la flecha (una sola vez por sesión del navegador). Nunca rompe la página."""
    try:
        components.html(_JS, height=0)
    except Exception:  # noqa: BLE001
        pass

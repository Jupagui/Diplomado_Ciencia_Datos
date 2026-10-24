import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { useLocation } from 'react-router-dom';
import { useAsesor } from '../hooks/useAsesor';
import { AsesorChat } from './AsesorChat';
import { Sheet } from './Overlays';
import { cls } from './cls';

const TAM = 64;            // px (= 4rem): tamaño del orbe
const ZONA = 160;          // px desde el borde lateral en los que el orbe persigue al puntero
const ANCHO_PAGE = 1280;   // px: ancho máximo del contenido (.page); el resto es banda libre
const TOPBAR = 64;         // px (= --topbar-h)

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

function useMedia(consulta: string) {
  return useSyncExternalStore(
    (cb) => {
      const m = window.matchMedia(consulta);
      m.addEventListener('change', cb);
      return () => m.removeEventListener('change', cb);
    },
    () => window.matchMedia(consulta).matches,
    () => false,
  );
}

/**
 * Orbe flotante del asesor IA. Vive en los costados de la pantalla (donde no hay contenido), deriva suavemente
 * y, cuando el puntero se acerca a un borde lateral, se le acerca para que se pueda hacer clic. El clic abre el chat.
 * En móvil o sin puntero fino queda fijo sobre la barra inferior; con «reducir movimiento» no se anima.
 */
export function AgenteOrbita() {
  const { pathname } = useLocation();
  const asesor = useAsesor();
  const [abierto, setAbierto] = useState(false);
  const boton = useRef<HTMLButtonElement>(null);
  const oculto = pathname.startsWith('/asesor');
  const fijo = useMedia('(max-width: 767.98px), (hover: none)');
  const reducido = useMedia('(prefers-reduced-motion: reduce)');

  useEffect(() => {
    const el = boton.current;
    if (!el || oculto || fijo) return;

    let lado: 1 | -1 = 1;            // 1 = derecha, -1 = izquierda
    let atraido = false;
    let ptr: { x: number; y: number } | null = null;
    let x = 0;
    let y = 0;
    let primero = true;
    let raf = 0;
    let ultimo = performance.now();

    const limitesY = () => [TOPBAR + 16, window.innerHeight - TAM - 16] as const;
    const anclaX = (l: 1 | -1) => {
      const vw = window.innerWidth;
      const banda = Math.max(0, (vw - ANCHO_PAGE) / 2);
      if (banda >= TAM + 16) return l === 1 ? vw - banda / 2 - TAM / 2 : banda / 2 - TAM / 2;   // cabe entero en la banda libre
      return l === 1 ? vw - TAM * 0.55 : -TAM * 0.45;                                          // asoma a medias por el borde
    };
    const objetivo = (t: number) => {
      const vw = window.innerWidth;
      const [ymin, ymax] = limitesY();
      if (atraido && ptr) {
        // junto al puntero, hacia el lado interior de la pantalla, para que el clic quede a un movimiento
        const tx = ptr.x + (lado === 1 ? -1 : 1) * (TAM / 2 + 18) - TAM / 2;
        return { tx: clamp(tx, -TAM * 0.45, vw - TAM * 0.55), ty: clamp(ptr.y - TAM / 2, ymin, ymax) };
      }
      if (reducido) return { tx: anclaX(lado), ty: clamp(window.innerHeight * 0.6, ymin, ymax) };
      const medio = (ymin + ymax) / 2;
      const amp = (ymax - ymin) * 0.3;
      return { tx: anclaX(lado) + Math.sin(t / 1900) * 7, ty: medio + Math.sin(t / 3100) * amp + Math.sin(t / 900) * 6 };
    };

    const dibujar = (now: number) => {
      const dt = Math.min(64, now - ultimo);
      ultimo = now;
      const { tx, ty } = objetivo(now);
      if (primero) { x = tx; y = ty; primero = false; }
      const sobre = ptr && Math.hypot(ptr.x - (x + TAM / 2), ptr.y - (y + TAM / 2)) < TAM / 2 + 4;   // si el puntero está encima, se queda quieto
      if (!sobre) {
        const k = 1 - Math.pow(1 - (atraido ? 0.1 : 0.035), dt / 16.7);
        x += (tx - x) * k;
        y += (ty - y) * k;
      }
      el.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
    };
    const bucle = (now: number) => { dibujar(now); raf = requestAnimationFrame(bucle); };
    const arrancar = () => { if (reducido) { primero = true; dibujar(performance.now()); } else { ultimo = performance.now(); raf = requestAnimationFrame(bucle); } };
    const parar = () => cancelAnimationFrame(raf);

    const alMover = (e: PointerEvent) => {
      if (e.pointerType === 'touch') return;
      ptr = { x: e.clientX, y: e.clientY };
      const vw = window.innerWidth;
      if (ptr.x > vw - ZONA) { lado = 1; atraido = true; }
      else if (ptr.x < ZONA) { lado = -1; atraido = true; }
      else atraido = false;
      el.classList.toggle('atraido', atraido);
      el.dataset.lado = lado === 1 ? 'd' : 'i';
      if (reducido) dibujar(performance.now());
    };
    const alSalir = () => { ptr = null; atraido = false; el.classList.remove('atraido'); };
    const alCambiarVisibilidad = () => { if (document.hidden) parar(); else { parar(); arrancar(); } };
    const alRedimensionar = () => { if (reducido) { primero = true; dibujar(performance.now()); } };

    window.addEventListener('pointermove', alMover, { passive: true });
    document.documentElement.addEventListener('pointerleave', alSalir);
    document.addEventListener('visibilitychange', alCambiarVisibilidad);
    window.addEventListener('resize', alRedimensionar);
    arrancar();
    return () => {
      parar();
      window.removeEventListener('pointermove', alMover);
      document.documentElement.removeEventListener('pointerleave', alSalir);
      document.removeEventListener('visibilitychange', alCambiarVisibilidad);
      window.removeEventListener('resize', alRedimensionar);
      el.style.transform = '';
      el.classList.remove('atraido');
    };
  }, [oculto, fijo, reducido]);

  if (oculto) return null;
  return (
    <>
      <button
        ref={boton}
        type="button"
        className={cls('agente', fijo && 'agente--fijo')}
        data-lado="d"
        aria-label="Abrir el asesor IA"
        aria-haspopup="dialog"
        onClick={() => setAbierto(true)}
      >
        <svg viewBox="0 0 40 40" aria-hidden="true">
          <circle className="a-anillo" cx="20" cy="20" r="10" />
          <circle className="a-nucleo" cx="20" cy="20" r="4" />
          <g className="a-giro">
            <ellipse className="a-orbita" cx="20" cy="20" rx="18" ry="6.5" transform="rotate(-22 20 20)" />
            <circle className="a-luna" cx="36.7" cy="13.3" r="2.2" />
          </g>
        </svg>
        <span className="agente-etq" aria-hidden="true">Pregúntale al asesor</span>
      </button>

      <Sheet abierto={abierto} onCerrar={() => setAbierto(false)} titulo="Asesor IA" descripcion="Cada plan cita datos analíticos y nunca propone descuentos mayores al 30 %.">
        <div className="asesor-chat asesor-panel">
          <AsesorChat asesor={asesor} />
        </div>
      </Sheet>
    </>
  );
}

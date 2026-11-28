import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import { AgenteOrbita } from '../ui/AgenteOrbita';
import { Button } from '../ui/Button';
import { Icon, IconSprite, type IconName } from '../ui/Icon';
import { ThemeSwitch } from '../ui/Inputs';
import { ToastProvider } from '../ui/Toast';
import { OrbitBackdrop } from '../ui/backgrounds/OrbitBackdrop';
import { BlueprintBackdrop } from '../ui/backgrounds/BlueprintBackdrop';
import { Constellation } from '../ui/backgrounds/Constellation';
import { SealTrace } from '../ui/backgrounds/SealTrace';
import { TopoRadar } from '../ui/backgrounds/TopoRadar';
import { cls } from '../ui/cls';

const NAV: { to: string; texto: string; icon: IconName; fin?: boolean }[] = [
  { to: '/', texto: 'Inicio', icon: 'orbita', fin: true },
  { to: '/pos', texto: 'Venta', icon: 'carrito' },
  { to: '/productos', texto: 'Productos', icon: 'caja' },
  { to: '/clientes', texto: 'Clientes', icon: 'usuarios' },
  { to: '/analitica', texto: 'Analítica', icon: 'grafico' },
  { to: '/asesor', texto: 'Asesor IA', icon: 'chispa' },
  { to: '/datos', texto: 'Datos', icon: 'datos' },
];

/** Cada zona de la app tiene su propio fondo animado (cambia con la ruta mediante `key`).
 *  Encima del fondo va `.tinta`: ilustraciones de la marca dibujadas en tiza, distintas por pantalla (ver app.css).
 *  Analítica y Datos no llevan ilustración: son pantallas de lectura y el adorno competía con los números. */
function Fondo({ ruta }: { ruta: string }) {
  if (ruta === '/') return <div className={cls('backdrop', 'is-home')} key="home"><div className="aura a1" /><div className="aura a2" /><OrbitBackdrop /><div className="scrim" /><div className="tinta t-inicio" /></div>;
  if (ruta.startsWith('/pos') || ruta.startsWith('/productos')) return <div className="backdrop" key="bp"><BlueprintBackdrop /><div className="scrim" /><div className={cls('tinta', ruta.startsWith('/pos') ? 't-pos' : 't-productos')} /></div>;
  if (ruta.startsWith('/clientes')) return <div className="backdrop" key="cli"><BlueprintBackdrop /><div className="scrim" /><div className="tinta t-clientes" /></div>;
  if (ruta.startsWith('/analitica')) return <div className="backdrop" key="ana"><Constellation /><div className="scrim" /></div>;
  if (ruta.startsWith('/asesor')) return <div className="backdrop" key="ase"><TopoRadar /><div className="scrim" /><div className="tinta t-asesor" /></div>;
  if (ruta.startsWith('/datos')) return <div className="backdrop" key="dat"><SealTrace /><div className="scrim" /></div>;
  return null;
}

export function Marca() {
  return (
    <NavLink to="/" className="brand" aria-label="Red Rooster, ir al inicio">
      {/* Gallo 3R: isotipo del manual para espacios pequeños y cuando el nombre ya va escrito (mín. 40 px en pantalla) */}
      <img className="brand-mark" src="/marca/gallo-rojo.webp" width={40} height={40} alt="" />
      <span className="brand-word">RED ROOSTER</span>
    </NavLink>
  );
}

export default function AppShell() {
  const { pathname } = useLocation();
  const { usuario, salir } = useAuth();
  return (
    <ToastProvider>
      <div className="shell">
        <IconSprite />
        <a className="skip" href="#contenido">Saltar al contenido</a>
        <Fondo ruta={pathname} />

        <header className="topbar">
          <Marca />
          <nav className="nav-links" aria-label="Principal">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.fin}><Icon name={n.icon} />{n.texto}</NavLink>
            ))}
          </nav>
          <div className="topbar-actions">
            <span className="muted small hide-sm">{usuario}</span>
            <ThemeSwitch />
            <Button variant="ghost" iconOnly icon="salir" aria-label="Cerrar sesión" onClick={salir} />
          </div>
        </header>

        <main id="contenido" className="shell-main" tabIndex={-1}>
          <Outlet />
        </main>

        <AgenteOrbita />

        <nav className="bottom-nav" aria-label="Principal">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.fin}><Icon name={n.icon} />{n.texto}</NavLink>
          ))}
        </nav>
      </div>
    </ToastProvider>
  );
}

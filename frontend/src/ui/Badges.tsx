import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Icon, type IconName } from './Icon';
import { cls } from './cls';

/** Filtro o selección. Usa aria-pressed. */
export function Chip({ icon, pressed, className, children, ...resto }: { icon?: IconName; pressed?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" className={cls('chip', className)} aria-pressed={pressed} {...resto}>
      {icon && <Icon name={icon} />}
      {children}
    </button>
  );
}

/** Metadato que no se pulsa. */
export function Tag({ tone, icon, children }: { tone?: 'gold'; icon?: IconName; children: ReactNode }) {
  return (
    <span className={cls('tag', tone)}>
      {icon && <Icon name={icon} />}
      {children}
    </span>
  );
}

export type Tono = 'ok' | 'warn' | 'danger' | 'info' | 'gold' | 'neutral';

export function Pill({ tone = 'neutral', live, children }: { tone?: Tono; live?: boolean; children: ReactNode }) {
  return <span className={cls('pill', tone, live && 'live')}>{children}</span>;
}

/** Estado de inventario. Siempre lleva texto además del color. */
export function StatusPill({ stock }: { stock: number }) {
  if (stock <= 0) return <Pill tone="danger">Agotado</Pill>;
  if (stock <= 5) return <Pill tone="danger">Crítico</Pill>;
  if (stock <= 15) return <Pill tone="warn">Bajo</Pill>;
  return <Pill tone="ok">Disponible</Pill>;
}

const RUN: Record<string, { tone: Tono; texto: string }> = {
  SUCCESS: { tone: 'ok', texto: 'Exitoso' },
  SIN_CAMBIOS: { tone: 'info', texto: 'Sin cambios' },
  RUNNING: { tone: 'info', texto: 'En curso' },
  FAILED: { tone: 'danger', texto: 'Fallido' },
};

/** Estado de una corrida del ETL. */
export function RunPill({ estado }: { estado: string }) {
  const e = RUN[estado] ?? { tone: 'neutral' as Tono, texto: estado };
  return <Pill tone={e.tone} live={estado === 'RUNNING'}>{e.texto}</Pill>;
}

/** Riesgo de una acción del asesor. */
export function RiesgoPill({ riesgo }: { riesgo: 'bajo' | 'medio' | 'alto' }) {
  const tone: Tono = riesgo === 'alto' ? 'danger' : riesgo === 'medio' ? 'warn' : 'ok';
  return <Pill tone={tone}>Riesgo {riesgo}</Pill>;
}

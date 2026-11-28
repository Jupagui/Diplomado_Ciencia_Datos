import type { Tono } from './Badges';

/** Traduce una métrica técnica a una calificación que entiende el dueño del negocio.
 *  Umbrales de referencia (no son ley; sirven para leer el número de un vistazo):
 *  - R² (demanda): ≥ 0,5 buena · ≥ 0,3 aceptable · menos, débil.
 *  - Silueta (segmentos): ≥ 0,5 buena · ≥ 0,25 aceptable · menos, débil. */
export interface Calificacion { texto: 'Buena' | 'Aceptable' | 'Débil' | 'Sin datos'; tono: Tono }

function calificar(v: number | null | undefined, buena: number, aceptable: number): Calificacion {
  if (v == null || Number.isNaN(v)) return { texto: 'Sin datos', tono: 'neutral' };
  if (v >= buena) return { texto: 'Buena', tono: 'ok' };
  if (v >= aceptable) return { texto: 'Aceptable', tono: 'warn' };
  return { texto: 'Débil', tono: 'danger' };
}

export const calidadDemanda = (r2: number | null | undefined) => calificar(r2, 0.5, 0.3);
export const calidadSegmentos = (silueta: number | null | undefined) => calificar(silueta, 0.5, 0.25);

/** Cuánto mejor es el modelo que la línea base ingenua («lo mismo que hace una semana»), en %. */
export function mejoraSobreBase(mae: number | null | undefined, maeBase: number | null | undefined): number | null {
  if (mae == null || !maeBase) return null;
  return Math.round((1 - mae / maeBase) * 100);
}

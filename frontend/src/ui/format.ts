const cop = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
const num = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 });
const dec = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 });

export const formatoCOP = (v: number | null | undefined) => (v == null ? '—' : cop.format(v));
export const formatoNum = (v: number | null | undefined) => (v == null ? '—' : num.format(v));
export const formatoDec = (v: number | null | undefined) => (v == null ? '—' : dec.format(v));
export const formatoPct = (v: number | null | undefined) => (v == null ? '—' : `${dec.format(v)} %`);

/** Moneda compacta para ejes: 1,2 M / 350 mil. */
export function formatoCompacto(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e6) return `${(v / 1e6).toLocaleString('es-CO', { maximumFractionDigits: 1 })} M`;
  if (a >= 1e3) return `${(v / 1e3).toLocaleString('es-CO', { maximumFractionDigits: 0 })} mil`;
  return String(Math.round(v));
}

/** Tiempo relativo en lenguaje cotidiano: «hace 5 min», «hace 3 h», «hace 2 días». */
export function formatoHace(iso: string | null | undefined): string {
  if (!iso) return 'nunca';
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return 'hace un momento';
  if (min < 60) return `hace ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.round(h / 24);
  return d === 1 ? 'ayer' : `hace ${d} días`;
}

export function formatoFecha(iso: string | null | undefined, conHora = false): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('es-CO', conHora
    ? { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }
    : { day: '2-digit', month: 'short', year: 'numeric' });
}

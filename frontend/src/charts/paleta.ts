import { useMemo } from 'react';
import { leerVar, useTema } from '../ui/theme';

export interface Paleta {
  gold: string; sage: string; info: string; line: string; muted: string; text: string; raised: string; warn: string; danger: string;
  /** Serie categórica: solo colores de la paleta Red Rooster (`--serie-1..6` en tokens.css), distintos por tema. */
  cat: string[];
}

/** Colores de los tokens ya resueltos (Recharts no entiende var()). Se recalcula al cambiar de tema. */
export function usePaleta(): Paleta {
  const tema = useTema();
  return useMemo(() => {
    void tema;
    const v = (n: string) => leerVar(n);
    return {
      gold: v('--gold'), sage: v('--sage'), info: v('--info'), line: v('--line'), muted: v('--muted'), text: v('--text-2'),
      raised: v('--raised'), warn: v('--warn'), danger: v('--danger'),
      cat: [1, 2, 3, 4, 5, 6].map((i) => v(`--serie-${i}`)),
    };
  }, [tema]);
}

export const estiloEje = (p: Paleta) => ({ stroke: p.line, tick: { fill: p.muted, fontSize: 11, fontFamily: 'var(--font-mono)' } });

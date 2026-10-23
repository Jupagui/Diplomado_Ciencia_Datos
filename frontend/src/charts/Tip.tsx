import type { ReactNode } from 'react';

interface Props {
  active?: boolean;
  payload?: { name?: string; value?: number | string; color?: string; payload?: Record<string, unknown> }[];
  label?: string | number;
  formato?: (v: number) => string;
  titulo?: (label: string | number | undefined, p: Record<string, unknown> | undefined) => ReactNode;
}

/** Tooltip de Recharts con el estilo de los tokens. */
export function Tip({ active, payload, label, formato, titulo }: Props) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <b>{titulo ? titulo(label, payload[0].payload) : String(label ?? payload[0].name ?? '')}</b>
      {payload.map((p, i) => (
        <span key={i} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' && formato ? formato(p.value) : String(p.value)}
        </span>
      ))}
    </div>
  );
}

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { estiloEje, usePaleta } from './paleta';
import { Tip } from './Tip';

export interface PuntoDemanda { fecha: string; cantidad: number; total?: number }

/** Pronóstico diario de unidades de uno o todos los productos (suma). */
export function LineaDemanda({ datos }: { datos: PuntoDemanda[] }) {
  const p = usePaleta();
  const eje = estiloEje(p);
  return (
    <div className="chart-box" role="img" aria-label="Gráfico de línea: pronóstico de demanda diaria">
      <ResponsiveContainer>
        <LineChart data={datos} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={p.line} strokeDasharray="3 4" vertical={false} />
          <XAxis dataKey="fecha" {...eje} tickFormatter={(f: string) => f.slice(5)} minTickGap={20} />
          <YAxis {...eje} width={40} />
          <Tooltip content={<Tip formato={(v) => `${v.toLocaleString('es-CO', { maximumFractionDigits: 1 })} u.`} />} cursor={{ stroke: p.line }} />
          <Line type="monotone" dataKey="cantidad" name="Pronóstico" stroke={p.gold} strokeWidth={2} strokeDasharray="5 3" dot={{ r: 2.5, fill: p.gold }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

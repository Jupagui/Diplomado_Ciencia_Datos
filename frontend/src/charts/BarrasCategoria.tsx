import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatoCOP, formatoCompacto } from '../ui/format';
import { estiloEje, usePaleta } from './paleta';
import { Tip } from './Tip';

/** Ingresos por categoría (barras horizontales). */
export function BarrasCategoria({ datos }: { datos: { category: string; ingresos: number }[] }) {
  const p = usePaleta();
  const eje = estiloEje(p);
  return (
    <div className="chart-box" role="img" aria-label="Gráfico de barras: ingresos por categoría">
      <ResponsiveContainer>
        <BarChart data={datos} layout="vertical" margin={{ top: 4, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid stroke={p.line} strokeDasharray="3 4" horizontal={false} />
          <XAxis type="number" {...eje} tickFormatter={formatoCompacto} />
          <YAxis type="category" dataKey="category" {...eje} width={110} />
          <Tooltip content={<Tip formato={formatoCOP} />} cursor={{ fill: p.line, fillOpacity: 0.35 }} />
          <Bar dataKey="ingresos" name="Ingresos" fill={p.sage} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

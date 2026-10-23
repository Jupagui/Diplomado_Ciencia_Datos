import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatoCOP, formatoCompacto } from '../ui/format';
import { estiloEje, usePaleta } from './paleta';
import { Tip } from './Tip';

/** Ventas diarias (COP). */
export function LineaVentas({ datos }: { datos: { fecha: string; total: number; n_ventas: number }[] }) {
  const p = usePaleta();
  const eje = estiloEje(p);
  return (
    <div className="chart-box" role="img" aria-label="Gráfico de línea: ventas diarias">
      <ResponsiveContainer>
        <AreaChart data={datos} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="g-ventas" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={p.gold} stopOpacity={0.35} />
              <stop offset="100%" stopColor={p.gold} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={p.line} strokeDasharray="3 4" vertical={false} />
          <XAxis dataKey="fecha" {...eje} tickFormatter={(f: string) => f.slice(5)} minTickGap={24} />
          <YAxis {...eje} tickFormatter={formatoCompacto} width={52} />
          <Tooltip content={<Tip formato={formatoCOP} />} cursor={{ stroke: p.line }} />
          <Area type="monotone" dataKey="total" name="Ventas" stroke={p.gold} strokeWidth={2} fill="url(#g-ventas)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

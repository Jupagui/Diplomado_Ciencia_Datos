import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { estiloEje, usePaleta } from './paleta';
import { Tip } from './Tip';

export interface PuntoDemanda { fecha: string; cantidad: number; total?: number }

/** «mié 22»: día de la semana + número, para leer el pronóstico como un calendario. */
const diaCorto = (f: string) => {
  const d = new Date(`${f}T12:00:00`);
  return `${d.toLocaleDateString('es-CO', { weekday: 'short' }).replace('.', '')} ${d.getDate()}`;
};

/** Pronóstico diario de unidades de uno o todos los productos (suma).
 *  Hasta 10 días: barras por día (se compara de un vistazo y se nota el martes de descanso).
 *  Más días: línea continua, que muestra mejor la tendencia. */
export function LineaDemanda({ datos }: { datos: PuntoDemanda[] }) {
  const p = usePaleta();
  const eje = estiloEje(p);
  const tip = <Tip formato={(v) => `${v.toLocaleString('es-CO', { maximumFractionDigits: 1 })} u.`} />;
  const pocos = datos.length <= 10;
  return (
    <div className="chart-box" role="img" aria-label={`Gráfico de ${pocos ? 'barras' : 'línea'}: pronóstico de unidades por día`}>
      <ResponsiveContainer>
        {pocos ? (
          <BarChart data={datos} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={p.line} strokeDasharray="3 4" vertical={false} />
            <XAxis dataKey="fecha" {...eje} tickFormatter={diaCorto} interval={0} />
            <YAxis {...eje} width={36} allowDecimals={false} />
            <Tooltip content={tip} cursor={{ fill: p.line, fillOpacity: 0.35 }} />
            <Bar dataKey="cantidad" name="Pronóstico" fill={p.gold} fillOpacity={0.85} radius={[3, 3, 0, 0]} maxBarSize={44} />
          </BarChart>
        ) : (
          <LineChart data={datos} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={p.line} strokeDasharray="3 4" vertical={false} />
            <XAxis dataKey="fecha" {...eje} tickFormatter={diaCorto} minTickGap={24} />
            <YAxis {...eje} width={36} allowDecimals={false} />
            <Tooltip content={tip} cursor={{ stroke: p.line }} />
            <Line type="monotone" dataKey="cantidad" name="Pronóstico" stroke={p.gold} strokeWidth={2} dot={false} />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

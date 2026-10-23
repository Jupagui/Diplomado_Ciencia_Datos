import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts';
import type { ClienteSegmento, ResumenSegmento } from '../services/api';
import { formatoCOP, formatoCompacto } from '../ui/format';
import { estiloEje, usePaleta } from './paleta';
import { Tip } from './Tip';

/** Dispersión Recencia (x) vs Monetario (y), un color por segmento. */
export function DispersionRFM({ clientes, resumen }: { clientes: ClienteSegmento[]; resumen: ResumenSegmento[] }) {
  const p = usePaleta();
  const eje = estiloEje(p);
  return (
    <>
      <div className="chart-box tall" role="img" aria-label="Gráfico de dispersión: recencia contra valor monetario por segmento">
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 8, right: 12, left: 0, bottom: 12 }}>
            <CartesianGrid stroke={p.line} strokeDasharray="3 4" />
            <XAxis type="number" dataKey="recency" name="Recencia" unit=" d" {...eje} label={{ value: 'Recencia (días)', position: 'insideBottom', offset: -6, fill: p.muted, fontSize: 11 }} />
            <YAxis type="number" dataKey="monetary" name="Monetario" {...eje} tickFormatter={formatoCompacto} width={52} />
            <ZAxis range={[36, 36]} />
            <Tooltip
              content={<Tip formato={formatoCOP} titulo={(_l, d) => `${d?.first_name ?? ''} ${d?.last_name ?? ''} · ${d?.segment_label ?? ''}`} />}
              cursor={{ strokeDasharray: '3 3', stroke: p.line }}
            />
            {resumen.map((s, i) => (
              <Scatter key={s.cluster} name={s.segmento} data={clientes.filter((c) => c.cluster === s.cluster)} fill={p.cat[i % p.cat.length]} fillOpacity={0.75} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="legend-row">
        {resumen.map((s, i) => <span key={s.cluster}><i style={{ background: p.cat[i % p.cat.length] }} />{s.segmento}</span>)}
      </div>
    </>
  );
}

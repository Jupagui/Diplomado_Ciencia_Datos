import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { ResumenSegmento } from '../services/api';
import { usePaleta } from './paleta';
import { Tip } from './Tip';

/** Clientes por segmento RFM. */
export function DonaSegmentos({ datos }: { datos: ResumenSegmento[] }) {
  const p = usePaleta();
  return (
    <>
      <div className="chart-box short" role="img" aria-label="Gráfico de dona: clientes por segmento">
        <ResponsiveContainer>
          <PieChart>
            <Tooltip content={<Tip formato={(v) => `${v} clientes`} />} />
            <Pie data={datos} dataKey="n_clientes" nameKey="segmento" innerRadius="58%" outerRadius="88%" paddingAngle={2} stroke={p.raised} strokeWidth={2}>
              {datos.map((d, i) => <Cell key={d.cluster} fill={p.cat[i % p.cat.length]} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="legend-row">
        {datos.map((d, i) => <span key={d.cluster}><i style={{ background: p.cat[i % p.cat.length] }} />{d.segmento} · {d.n_clientes}</span>)}
      </div>
    </>
  );
}

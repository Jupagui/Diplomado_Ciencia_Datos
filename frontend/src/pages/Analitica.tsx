import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { DispersionRFM } from '../charts/DispersionRFM';
import { DonaSegmentos } from '../charts/DonaSegmentos';
import { LineaDemanda } from '../charts/LineaDemanda';
import { getDemanda, getMetricas, getReglas, getSegmentos, mensajeError, type Metricas } from '../services/api';
import { Pill } from '../ui/Badges';
import { Field, Segmented, Select, Tabs } from '../ui/Inputs';
import { Alert, Card, CardHeader, EmptyState, Skeleton } from '../ui/Surfaces';
import { btnClass, vars } from '../ui/cls';
import { formatoCOP, formatoDec, formatoNum } from '../ui/format';

const TABS = [
  { id: 'demanda', texto: 'Demanda' },
  { id: 'cruzada', texto: 'Venta cruzada' },
  { id: 'segmentos', texto: 'Segmentos' },
];

function SinDatos() {
  return (
    <EmptyState icon="datos" title="Aún no hay resultados analíticos" action={<Link className={btnClass('primary')} to="/datos">Ir a Datos y ejecutar el pipeline</Link>}>
      Los pronósticos, reglas y segmentos se generan al ejecutar el ETL.
    </EmptyState>
  );
}

function Demanda({ m }: { m?: Metricas }) {
  const [horizon, setHorizon] = useState<'7' | '30'>('7');
  const [producto, setProducto] = useState('');
  const [q, setQ] = useState('');
  const dem = useQuery({ queryKey: ['demanda', horizon], queryFn: () => getDemanda(Number(horizon) as 7 | 30) });
  const datos = useMemo(() => dem.data ?? [], [dem.data]);

  const serie = useMemo(() => {
    if (producto) return (datos.find((d) => d.product_id === Number(producto))?.diaria ?? []).map((p) => ({ fecha: p.fecha, cantidad: p.cantidad }));
    const acum = new Map<string, number>();
    datos.forEach((d) => d.diaria.forEach((p) => acum.set(p.fecha, (acum.get(p.fecha) ?? 0) + p.cantidad)));
    return [...acum.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([fecha, cantidad]) => ({ fecha, cantidad: Math.round(cantidad * 10) / 10 }));
  }, [datos, producto]);

  const filas = datos.filter((d) => !q || d.name.toLowerCase().includes(q.toLowerCase()));
  const dm = m?.detalle?.demanda;

  return (
    <div className="stack">
      <div className="metrics">
        <Pill tone="gold">MAE {formatoDec(m?.mae)} u.</Pill>
        <Pill tone="gold">R² {formatoDec(m?.r2)}</Pill>
        {dm && <Pill>Línea base lag-7: MAE {formatoDec(dm.mae_baseline_lag7)}</Pill>}
        {dm && <Pill>{formatoNum(dm.n_test)} obs. de prueba (últimos 30 días)</Pill>}
      </div>
      <div className="toolbar">
        <Segmented etiqueta="Horizonte" opciones={[{ valor: '7', texto: '7 días' }, { valor: '30', texto: '30 días' }]} valor={horizon} onChange={setHorizon} />
        <Select label="Producto" value={producto} onChange={(e) => setProducto(e.target.value)}>
          <option value="">Todos los productos (suma)</option>
          {datos.map((d) => <option key={d.product_id} value={d.product_id}>{d.name}</option>)}
        </Select>
      </div>
      {dem.isError && <Alert tone="danger" title="No se pudo cargar el pronóstico" role="alert">{mensajeError(dem.error)}</Alert>}
      {dem.isLoading ? <Skeleton ancho="100%" className="chart-box" /> : !datos.length ? <SinDatos /> : (
        <>
          <Card flat><LineaDemanda datos={serie} /></Card>
          <Field label="Filtrar tabla" hideLabel icon="buscar" placeholder="Filtrar productos…" value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>Producto</th><th className="num-cell">Demanda {horizon} d</th><th className="num-cell">Stock</th><th>Cobertura</th></tr></thead>
              <tbody>
                {filas.slice(0, 40).map((d) => (
                  <tr key={d.product_id}>
                    <td>{d.name}</td>
                    <td className="num-cell">{formatoDec(d.total_predicho)}</td>
                    <td className="num-cell">{formatoNum(d.stock)}</td>
                    <td>{d.stock < d.total_predicho ? <Pill tone="danger">Reponer</Pill> : d.stock < d.total_predicho * 1.5 ? <Pill tone="warn">Ajustada</Pill> : <Pill tone="ok">Suficiente</Pill>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function VentaCruzada({ m }: { m?: Metricas }) {
  const reglas = useQuery({ queryKey: ['reglas'], queryFn: getReglas });
  const datos = reglas.data ?? [];
  const max = Math.max(...datos.map((r) => r.lift), 1);
  const cn = m?.detalle?.canasta;
  return (
    <div className="stack">
      <div className="metrics">
        <Pill tone="gold">{formatoNum(m?.n_reglas)} reglas</Pill>
        {cn && <Pill>Soporte ≥ {cn.min_support}</Pill>}
        {cn && <Pill>Confianza ≥ {cn.min_confidence}</Pill>}
        {cn && <Pill>Lift &gt; {cn.min_lift}</Pill>}
        {cn && <Pill>{formatoNum(cn.n_canastas)} canastas</Pill>}
      </div>
      {reglas.isError && <Alert tone="danger" title="No se pudieron cargar las reglas" role="alert">{mensajeError(reglas.error)}</Alert>}
      {reglas.isLoading ? <Skeleton ancho="100%" /> : !datos.length ? <SinDatos /> : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Si compra…</th><th>…también compra</th><th className="num-cell">Soporte</th><th className="num-cell">Confianza</th><th>Lift</th></tr></thead>
            <tbody>
              {datos.map((r) => (
                <tr key={r.id}>
                  <td>{r.antecedent}</td>
                  <td>{r.consequent}</td>
                  <td className="num-cell">{formatoDec(r.support * 100)} %</td>
                  <td className="num-cell">{formatoDec(r.confidence * 100)} %</td>
                  <td><div className="lift-cell"><b>{formatoDec(r.lift)}</b><div className="lift-bar" role="img" aria-label={`Lift ${formatoDec(r.lift)}`}><i style={{ width: `${(r.lift / max) * 100}%` }} /></div></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Segmentos({ m }: { m?: Metricas }) {
  const seg = useQuery({ queryKey: ['segmentos'], queryFn: getSegmentos });
  const d = seg.data;
  return (
    <div className="stack">
      <div className="metrics">
        <Pill tone="gold">Silueta {formatoDec(m?.silhouette)}</Pill>
        <Pill tone="gold">k = {m?.k ?? '—'}</Pill>
        <Pill>{formatoNum(m?.detalle?.segmentos?.n_clientes)} clientes identificados</Pill>
      </div>
      {seg.isError && <Alert tone="danger" title="No se pudieron cargar los segmentos" role="alert">{mensajeError(seg.error)}</Alert>}
      {seg.isLoading ? <Skeleton ancho="100%" className="chart-box" /> : !d?.resumen.length ? <SinDatos /> : (
        <>
          <div className="grid-2">
            <Card flat><CardHeader level={3} title="Clientes por segmento" /><DonaSegmentos datos={d.resumen} /></Card>
            <Card flat><CardHeader level={3} title="Recencia vs. valor monetario" /><DispersionRFM clientes={d.clientes} resumen={d.resumen} /></Card>
          </div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>Segmento</th><th className="num-cell">Clientes</th><th className="num-cell">Recencia (d)</th><th className="num-cell">Frecuencia</th><th className="num-cell">Monetario medio</th><th className="num-cell">Monetario total</th></tr></thead>
              <tbody>
                {d.resumen.map((s) => (
                  <tr key={s.cluster}>
                    <td>{s.segmento}</td><td className="num-cell">{s.n_clientes}</td><td className="num-cell">{formatoDec(s.recencia_media)}</td>
                    <td className="num-cell">{formatoDec(s.frecuencia_media)}</td><td className="num-cell">{formatoCOP(s.monetario_medio)}</td><td className="num-cell">{formatoCOP(s.monetario_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default function Analitica() {
  const [tab, setTab] = useState('demanda');
  const metricas = useQuery({ queryKey: ['metricas'], queryFn: getMetricas });
  const m = metricas.data;
  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Analítica predictiva</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Lo que <em>viene</em></h1>
        <p className="lead rise" style={vars({ '--i': 2 })}>Demanda con XGBoost, venta cruzada con Apriori y segmentación RFM con K-Means.</p>
      </header>
      <Card className="rise" style={vars({ '--i': 3 })}>
        <Tabs etiqueta="Vistas de analítica" tabs={TABS} valor={tab} onChange={setTab} />
        <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} style={{ paddingTop: 'var(--sp-3)' }}>
          {metricas.isLoading ? <Skeleton ancho="100%" /> : m && !m.disponible ? <SinDatos /> : (
            <>
              {tab === 'demanda' && <Demanda m={m} />}
              {tab === 'cruzada' && <VentaCruzada m={m} />}
              {tab === 'segmentos' && <Segmentos m={m} />}
            </>
          )}
        </div>
      </Card>
    </div>
  );
}

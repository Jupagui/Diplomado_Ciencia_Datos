import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { BarrasCategoria } from '../charts/BarrasCategoria';
import { LineaVentas } from '../charts/LineaVentas';
import { getKpis, getStockBajo, mensajeError } from '../services/api';
import { StatusPill } from '../ui/Badges';
import { Segmented } from '../ui/Inputs';
import { Alert, Card, CardHeader, EmptyState, Skeleton, Stat } from '../ui/Surfaces';
import { btnClass, vars } from '../ui/cls';
import { formatoCOP, formatoDec, formatoNum, formatoPct } from '../ui/format';

const PERIODOS = [
  { valor: '7', texto: '7 días' },
  { valor: '30', texto: '30 días' },
  { valor: '90', texto: '90 días' },
];

export default function Inicio() {
  const [dias, setDias] = useState('30');
  const kpis = useQuery({ queryKey: ['kpis', dias], queryFn: () => getKpis(Number(dias)) });
  const bajo = useQuery({ queryKey: ['stock-bajo'], queryFn: () => getStockBajo(15) });
  const k = kpis.data;

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Panel operativo</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Tu negocio, <em>hoy</em></h1>
        <p className="lead rise" style={vars({ '--i': 2 })}>Ventas, margen e inventario del periodo, calculados directamente sobre las transacciones registradas.</p>
        <Segmented etiqueta="Periodo" opciones={PERIODOS} valor={dias} onChange={setDias} />
      </header>

      {kpis.isError && <Alert tone="danger" title="No se pudieron cargar los indicadores" role="alert">{mensajeError(kpis.error)}</Alert>}

      <div className="kpi-row" aria-busy={kpis.isLoading}>
        {[
          { l: 'Ventas', v: k && formatoCOP(k.total_ventas), s: k && `${formatoNum(k.n_ventas)} ventas · ${formatoNum(k.unidades_vendidas)} unidades` },
          { l: 'Ticket promedio', v: k && formatoCOP(k.ticket_promedio), s: 'Valor medio por venta' },
          { l: 'Margen', v: k && formatoPct(k.margen_pct), s: k && `${formatoCOP(k.margen)} de utilidad bruta` },
          { l: 'Rotación', v: k && `${formatoDec(k.rotacion)}×`, s: k && `${formatoDec(k.rotacion_anual)}× anualizada · inventario ${formatoCOP(k.valor_inventario)}` },
        ].map((x, i) => (
          <Card key={x.l} className="rise" style={vars({ '--i': i + 3 })}>
            {k ? <Stat valor={x.v} etiqueta={x.l} /> : <><Skeleton ancho="60%" /><Skeleton ancho="40%" /></>}
            {k && <small>{x.s}</small>}
          </Card>
        ))}
      </div>

      <div className="grid-2 wide-left">
        <Card className="rise" style={vars({ '--i': 7 })}>
          <CardHeader icon="grafico" title="Ventas diarias" />
          {kpis.isLoading ? <Skeleton ancho="100%" className="chart-box" /> : k && k.serie_diaria.length ? <LineaVentas datos={k.serie_diaria} /> : <EmptyState icon="grafico" title="Sin ventas en el periodo" />}
        </Card>
        <Card className="rise" style={vars({ '--i': 8 })}>
          <CardHeader icon="caja" title="Ingresos por categoría" />
          {kpis.isLoading ? <Skeleton ancho="100%" className="chart-box" /> : k && k.ventas_por_categoria.length ? <BarrasCategoria datos={k.ventas_por_categoria} /> : <EmptyState icon="caja" title="Sin datos" />}
        </Card>
      </div>

      <div className="grid-2">
        <Card className="rise" style={vars({ '--i': 9 })}>
          <CardHeader icon="check" title="Top productos" aside={<span className="muted small">por ingresos</span>} />
          {kpis.isLoading ? <Skeleton ancho="100%" /> : !k?.top_productos.length ? <EmptyState title="Sin ventas en el periodo" /> : (
            <div className="tbl-wrap">
              <table className="tbl">
                <thead><tr><th>Producto</th><th>Categoría</th><th className="num-cell">Unid.</th><th className="num-cell">Ingresos</th></tr></thead>
                <tbody>
                  {k.top_productos.map((p) => (
                    <tr key={p.product_id}><td>{p.name}</td><td className="muted">{p.category ?? '—'}</td><td className="num-cell">{formatoNum(p.unidades)}</td><td className="num-cell">{formatoCOP(p.ingresos)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card className="rise" style={vars({ '--i': 10 })}>
          <CardHeader icon="alerta" title="Stock bajo" aside={<span className="muted small">{k ? `${k.productos_bajo_stock} con ≤ 10 u.` : ''}</span>} />
          {bajo.isLoading ? <Skeleton ancho="100%" /> : !bajo.data?.length ? <EmptyState icon="check" title="Inventario saludable">Ningún producto activo está por debajo del umbral.</EmptyState> : (
            <div className="tbl-wrap">
              <table className="tbl">
                <thead><tr><th>Producto</th><th className="num-cell">Stock</th><th>Estado</th></tr></thead>
                <tbody>
                  {bajo.data.slice(0, 10).map((p) => (
                    <tr key={p.id}><td>{p.name}</td><td className="num-cell">{p.stock}</td><td><StatusPill stock={p.stock} /></td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p style={{ marginTop: 'var(--sp-2)' }}><Link className={btnClass('secondary')} to="/productos">Gestionar inventario</Link></p>
        </Card>
      </div>
    </div>
  );
}

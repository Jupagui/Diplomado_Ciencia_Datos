import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { DispersionRFM } from '../charts/DispersionRFM';
import { LineaDemanda } from '../charts/LineaDemanda';
import { getDemanda, getMetricas, getReglas, getSegmentos, mensajeError, type Metricas, type ResumenSegmento } from '../services/api';
import { Pill } from '../ui/Badges';
import { Field, Segmented, Select, Tabs } from '../ui/Inputs';
import { Alert, Card, EmptyState, Skeleton } from '../ui/Surfaces';
import { calidadDemanda, calidadSegmentos, mejoraSobreBase } from '../ui/calidadModelo';
import { Detalle } from '../ui/Detalle';
import { btnClass, vars } from '../ui/cls';
import { agruparCombos } from '../ui/combos';
import { formatoCOP, formatoDec, formatoNum, formatoPct } from '../ui/format';

/* Principio de esta página (UX): primero la respuesta para el negocio, en palabras simples;
   los números técnicos (MAE, R², soporte, silueta) quedan plegados en «detalles» para quien los necesite. */

const TABS = [
  { id: 'demanda', texto: '¿Qué voy a vender?' },
  { id: 'cruzada', texto: '¿Qué se pide junto?' },
  { id: 'segmentos', texto: '¿Quiénes son mis clientes?' },
];

function SinDatos() {
  return (
    <EmptyState icon="datos" title="Aún no hay predicciones" action={<Link className={btnClass('primary')} to="/datos">Ir a Datos y actualizar</Link>}>
      Las predicciones se calculan desde la página Datos con «Actualizar predicciones».
    </EmptyState>
  );
}


/* ---------------------------------------------------------------- Demanda */
function Demanda({ m }: { m?: Metricas }) {
  const [horizon, setHorizon] = useState<'7' | '30'>('7');
  const [producto, setProducto] = useState('');
  const [q, setQ] = useState('');
  const dem = useQuery({ queryKey: ['demanda', horizon], queryFn: () => getDemanda(Number(horizon) as 7 | 30) });
  const datos = useMemo(() => [...(dem.data ?? [])].sort((a, b) => b.total_predicho - a.total_predicho), [dem.data]);

  const serie = useMemo(() => {
    if (producto) return (datos.find((d) => d.product_id === Number(producto))?.diaria ?? []).map((p) => ({ fecha: p.fecha, cantidad: p.cantidad }));
    const acum = new Map<string, number>();
    datos.forEach((d) => d.diaria.forEach((p) => acum.set(p.fecha, (acum.get(p.fecha) ?? 0) + p.cantidad)));
    return [...acum.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([fecha, cantidad]) => ({ fecha, cantidad: Math.round(cantidad * 10) / 10 }));
  }, [datos, producto]);

  // La cifra grande sigue al selector: todos los productos, o solo el elegido
  const elegido = producto ? datos.find((d) => d.product_id === Number(producto)) : undefined;
  const total = elegido ? elegido.total_predicho : datos.reduce((s, d) => s + d.total_predicho, 0);
  const top = datos.slice(0, 5);
  const maxTop = top[0]?.total_predicho || 1;
  // Si nadie tiene stock cargado, la cobertura diría «Reponer» en todas las filas: ruido, no información.
  const hayStock = datos.some((d) => d.stock > 0);
  const filas = datos.filter((d) => !q || d.name.toLowerCase().includes(q.toLowerCase()));
  const dm = m?.detalle?.demanda;
  const calidad = calidadDemanda(m?.r2);
  const mejora = mejoraSobreBase(m?.mae, dm?.mae_baseline_lag7);

  if (dem.isError) return <Alert tone="danger" title="No se pudo cargar el pronóstico" role="alert">{mensajeError(dem.error)}</Alert>;
  if (dem.isLoading) return <Skeleton ancho="100%" className="chart-box" />;
  if (!datos.length) return <SinDatos />;

  return (
    <div className="stack ux">
      <div className="ux-barra">
        <Segmented etiqueta="Horizonte" opciones={[{ valor: '7', texto: 'Próximos 7 días' }, { valor: '30', texto: 'Próximos 30 días' }]} valor={horizon} onChange={setHorizon} />
        <span className="ux-confianza">Confiabilidad <Pill tone={calidad.tono}>{calidad.texto}</Pill></span>
      </div>

      <div className="grid-2 wide-left">
        <Card>
          <p className="ux-k">Se espera vender{elegido ? ` · ${elegido.name}` : ' · todos los productos'}</p>
          <p className="ux-cifra">{formatoNum(total)} <span>unidades en {horizon} días</span></p>
          <div className="ux-fila">
            <h3 className="ux-h">Por día</h3>
            <Select label="Producto" hideLabel value={producto} onChange={(e) => setProducto(e.target.value)}>
              <option value="">Todos los productos</option>
              {datos.map((d) => <option key={d.product_id} value={d.product_id}>{d.name}</option>)}
            </Select>
          </div>
          <LineaDemanda datos={serie} />
        </Card>

        <Card>
          <h3 className="ux-h">Lo que más se va a pedir</h3>
          <ol className="ux-ranking">
            {top.map((d) => (
              <li key={d.product_id}>
                <span className="nombre">{d.name}</span>
                <span className="barra" aria-hidden="true"><i style={{ width: `${(d.total_predicho / maxTop) * 100}%` }} /></span>
                <b>{formatoNum(d.total_predicho)}</b>
              </li>
            ))}
          </ol>
          <p className="muted small">Unidades estimadas en los próximos {horizon} días.</p>
        </Card>
      </div>

      <Detalle titulo="¿Qué tan confiable es este pronóstico?">
        <p>
          En promedio se equivoca por <b>±{formatoDec(m?.mae)} unidades</b> por producto y por día
          {mejora != null && <>, y es <b>{mejora} % más preciso</b> que suponer «se vende lo mismo que hace una semana»</>}.
          Se probó con los últimos 30 días, que el modelo no vio al entrenar.
        </p>
        <p className="ux-tecnico">
          XGBoost · MAE {formatoDec(m?.mae)} · R² {formatoDec(m?.r2)} · línea base lag-7: MAE {formatoDec(dm?.mae_baseline_lag7)}, R² {formatoDec(dm?.r2_baseline_lag7)}
          {dm && <> · {formatoNum(dm.n_test)} observaciones de prueba · corte {dm.corte_train}</>}
        </p>
      </Detalle>

      <Detalle titulo={`Ver el pronóstico de cada producto (${datos.length})`}>
        <Field label="Buscar producto" hideLabel icon="buscar" placeholder="Buscar producto…" value={q} onChange={(e) => setQ(e.target.value)} />
        {!hayStock && <p className="muted small">El inventario no está cargado, así que no se calcula si alcanza el stock.</p>}
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Producto</th><th className="num-cell">Unidades en {horizon} días</th>{hayStock && <><th className="num-cell">Stock</th><th>¿Alcanza?</th></>}</tr></thead>
            <tbody>
              {filas.map((d) => (
                <tr key={d.product_id}>
                  <td>{d.name}</td>
                  <td className="num-cell">{formatoDec(d.total_predicho)}</td>
                  {hayStock && <>
                    <td className="num-cell">{formatoNum(d.stock)}</td>
                    <td>{d.stock < d.total_predicho ? <Pill tone="danger">Reponer</Pill> : d.stock < d.total_predicho * 1.5 ? <Pill tone="warn">Justo</Pill> : <Pill tone="ok">Sí</Pill>}</td>
                  </>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Detalle>
    </div>
  );
}

/* ---------------------------------------------------------- Venta cruzada */
function VentaCruzada({ m }: { m?: Metricas }) {
  const reglas = useQuery({ queryKey: ['reglas'], queryFn: getReglas });
  const datos = reglas.data ?? [];
  const cn = m?.detalle?.canasta;

  if (reglas.isError) return <Alert tone="danger" title="No se pudieron cargar los combos" role="alert">{mensajeError(reglas.error)}</Alert>;
  if (reglas.isLoading) return <Skeleton ancho="100%" />;
  if (!m?.disponible) return <SinDatos />;

  if (!datos.length) {
    // Cero reglas es un resultado, no un error: se explica en palabras simples.
    return (
      <div className="stack ux">
        <EmptyState icon="cruce" title="Todavía no hay combos frecuentes">
          Revisamos {formatoNum(cn?.n_canastas)} pedidos y ningún par de productos aparece junto en al menos
          {' '}{formatoDec((cn?.min_support ?? 0) * 100)} % de ellos. Con más ventas, o bajando ese umbral en la configuración, pueden aparecer.
        </EmptyState>
      </div>
    );
  }

  // Una tarjeta por combo, no por regla: «Limonada → Mojarra» y «Mojarra → Limonada» son el mismo combo.
  const combos = agruparCombos(datos);
  const destacados = combos.slice(0, 6);
  return (
    <div className="stack ux">
      <p className="lead-sm">Cuando alguien pide lo de arriba, conviene ofrecerle lo de abajo.</p>
      <div className="ux-combos">
        {destacados.map(({ clave, mejor }) => (
          <Card key={clave} className="ux-combo">
            <p><span className="muted small">Si piden</span><b>{mejor.antecedent}</b></p>
            <p><span className="muted small">ofrece</span><b className="acento">{mejor.consequent}</b></p>
            <p className="muted small">Pasa en {formatoDec(mejor.confidence * 100)} % de esos pedidos · {formatoDec(mejor.lift)}× más que por azar</p>
          </Card>
        ))}
      </div>
      <Detalle titulo={`Ver los ${combos.length} combos y sus ${datos.length} reglas`}>
        <p className="ux-tecnico">
          Apriori · soporte ≥ {formatoPct(cn ? cn.min_support * 100 : null)}
          {' '}· confianza ≥ {formatoPct(cn ? cn.min_confidence * 100 : null)}
          {' '}· lift &gt; {cn ? Number(cn.min_lift).toLocaleString('es-CO', { minimumFractionDigits: 1 }) : '—'}
          {' '}· {formatoNum(cn?.n_canastas)} canastas
        </p>
        <p className="muted small">Cada combo aparece una vez por dirección (A → B y B → A); las reglas del mismo combo van juntas.</p>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Si compra…</th><th>…también compra</th><th className="num-cell">Soporte</th><th className="num-cell">Confianza</th><th className="num-cell">Lift</th></tr></thead>
            <tbody>
              {combos.flatMap((c) => c.reglas).map((r) => (
                <tr key={r.id}>
                  <td>{r.antecedent}</td><td>{r.consequent}</td>
                  <td className="num-cell">{formatoDec(r.support * 100)} %</td>
                  <td className="num-cell">{formatoDec(r.confidence * 100)} %</td>
                  <td className="num-cell">{formatoDec(r.lift)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Detalle>
    </div>
  );
}

/* -------------------------------------------------------------- Segmentos */
/** Si el modelo repite una etiqueta (p. ej. dos «Campeones»), se numeran para no confundir. */
function nombresUnicos(resumen: ResumenSegmento[]): Map<number, string> {
  const vistos = new Map<string, number>();
  const total = new Map<string, number>();
  resumen.forEach((s) => total.set(s.segmento, (total.get(s.segmento) ?? 0) + 1));
  const out = new Map<number, string>();
  resumen.forEach((s) => {
    const n = (vistos.get(s.segmento) ?? 0) + 1;
    vistos.set(s.segmento, n);
    out.set(s.cluster, (total.get(s.segmento) ?? 0) > 1 ? `${s.segmento} ${n}` : s.segmento);
  });
  return out;
}

function Segmentos({ m }: { m?: Metricas }) {
  const seg = useQuery({ queryKey: ['segmentos'], queryFn: getSegmentos });
  const d = seg.data;

  if (seg.isError) return <Alert tone="danger" title="No se pudieron cargar los segmentos" role="alert">{mensajeError(seg.error)}</Alert>;
  if (seg.isLoading) return <Skeleton ancho="100%" className="chart-box" />;
  if (!d?.resumen.length) return <SinDatos />;

  const resumen = [...d.resumen].sort((a, b) => b.monetario_total - a.monetario_total);
  const nombres = nombresUnicos(resumen);
  const totalClientes = resumen.reduce((s, x) => s + x.n_clientes, 0);
  const calidad = calidadSegmentos(m?.silhouette);

  return (
    <div className="stack ux">
      <div className="ux-barra">
        <p className="lead-sm">{formatoNum(totalClientes)} clientes reconocidos por su teléfono, agrupados en {resumen.length} tipos según qué tan reciente, seguido y cuánto compran.</p>
        <span className="ux-confianza">Separación <Pill tone={calidad.tono}>{calidad.texto}</Pill></span>
      </div>
      <div className="ux-segmentos">
        {resumen.map((s) => (
          <Card key={s.cluster} className="ux-seg">
            <div className="ux-fila">
              <h3 className="ux-h">{nombres.get(s.cluster)}</h3>
              <span className="ux-seg-n">{formatoNum(s.n_clientes)} <small>clientes</small></span>
            </div>
            <span className="barra" aria-hidden="true"><i style={{ width: `${(s.n_clientes / totalClientes) * 100}%` }} /></span>
            <p className="small">
              Última compra hace ~{formatoNum(s.recencia_media)} días · {formatoDec(s.frecuencia_media)} pedidos en promedio · gastan {formatoCOP(s.monetario_medio)} cada uno.
            </p>
          </Card>
        ))}
      </div>
      <Detalle titulo="Ver detalle técnico (RFM y K-Means)">
        <p className="ux-tecnico">K-Means · k = {m?.k ?? '—'} · silueta {formatoDec(m?.silhouette)} · {formatoNum(m?.detalle?.segmentos?.n_clientes)} clientes con compras</p>
        <DispersionRFM clientes={d.clientes} resumen={d.resumen} />
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Segmento</th><th className="num-cell">Clientes</th><th className="num-cell">Recencia (d)</th><th className="num-cell">Frecuencia</th><th className="num-cell">Monetario medio</th><th className="num-cell">Monetario total</th></tr></thead>
            <tbody>
              {resumen.map((s) => (
                <tr key={s.cluster}>
                  <td>{nombres.get(s.cluster)}</td><td className="num-cell">{s.n_clientes}</td><td className="num-cell">{formatoDec(s.recencia_media)}</td>
                  <td className="num-cell">{formatoDec(s.frecuencia_media)}</td><td className="num-cell">{formatoCOP(s.monetario_medio)}</td><td className="num-cell">{formatoCOP(s.monetario_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Detalle>
    </div>
  );
}

/* ----------------------------------------------------------------- Página */
export default function Analitica() {
  const [tab, setTab] = useState('demanda');
  const metricas = useQuery({ queryKey: ['metricas'], queryFn: getMetricas });
  const m = metricas.data;
  return (
    <div className="page sobria">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Predicción</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Lo que <em>viene</em></h1>
        <p className="lead rise" style={vars({ '--i': 2 })}>Calculado con tus ventas reales. Arriba, la respuesta; si quieres el detalle técnico, ábrelo abajo.</p>
      </header>
      <div className="rise" style={vars({ '--i': 3 })}>
        <Tabs etiqueta="Preguntas de predicción" tabs={TABS} valor={tab} onChange={setTab} />
        <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="ux-panel">
          {metricas.isLoading ? <Skeleton ancho="100%" /> : m && !m.disponible ? <SinDatos /> : (
            <>
              {tab === 'demanda' && <Demanda m={m} />}
              {tab === 'cruzada' && <VentaCruzada m={m} />}
              {tab === 'segmentos' && <Segmentos m={m} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ejecutarEtl, getFuenteReal, getMetricas, getReglas, getRuns, importarFuenteReal, mensajeError } from '../services/api';
import { Pill, RunPill, type Tono } from '../ui/Badges';
import { Button } from '../ui/Button';
import { Switch } from '../ui/Inputs';
import { Alert, Card, EmptyState, Skeleton } from '../ui/Surfaces';
import { calidadDemanda, calidadSegmentos, mejoraSobreBase } from '../ui/calidadModelo';
import { btnClass, vars } from '../ui/cls';
import { agruparCombos } from '../ui/combos';
import { Detalle } from '../ui/Detalle';
import { formatoDec, formatoFecha, formatoHace, formatoNum } from '../ui/format';
import { useToast } from '../ui/useToast';

/* Principio de esta página (UX): el proceso ETL se cuenta como 3 pasos (pedidos → predicciones → resultados),
   cada uno con su estado y UNA acción. Rutas, watermark, opciones de forzado e historial completo quedan plegados. */

function Paso({ n, titulo, estado, children }: { n: number; titulo: string; estado: { texto: string; tono: Tono }; children: ReactNode }) {
  return (
    <Card className="ux-paso">
      <div className="ux-fila">
        <h3 className="ux-h"><span className="paso-n" aria-hidden="true">{n}</span>{titulo}</h3>
        <Pill tone={estado.tono}>{estado.texto}</Pill>
      </div>
      {children}
    </Card>
  );
}

export default function Datos() {
  const qc = useQueryClient();
  const avisar = useToast();
  const [force, setForce] = useState(false);
  const [forzarImportacion, setForzarImportacion] = useState(false);
  const fuente = useQuery({ queryKey: ['fuente-real'], queryFn: getFuenteReal, refetchInterval: 30_000 });
  const runs = useQuery({ queryKey: ['runs'], queryFn: getRuns });
  const metricas = useQuery({ queryKey: ['metricas'], queryFn: getMetricas });
  // n_reglas cuenta cada dirección (A → B y B → A); el dueño ve combos, así que se cuentan agrupados.
  const reglas = useQuery({ queryKey: ['reglas'], queryFn: getReglas });
  const nCombos = reglas.data ? agruparCombos(reglas.data).length : null;

  const importar = useMutation({
    mutationFn: () => importarFuenteReal(forzarImportacion),
    onSuccess: (r) => {
      avisar(r.message || 'Pedidos sincronizados', r.status === 'SUCCESS' ? 'ok' : 'info');
      for (const key of ['fuente-real', 'productos', 'clientes', 'kpis', 'runs']) void qc.invalidateQueries({ queryKey: [key] });
    },
    onError: (e) => { avisar(mensajeError(e), 'error'); void qc.invalidateQueries({ queryKey: ['fuente-real'] }); },
  });

  const ejecutar = useMutation({
    mutationFn: () => ejecutarEtl(force),
    onSuccess: (r) => {
      avisar(r.status === 'SIN_CAMBIOS' ? 'No hay ventas nuevas: las predicciones ya estaban al día' : `Predicciones actualizadas en ${formatoDec(r.duracion_s)} s`, r.status === 'SUCCESS' ? 'ok' : 'info');
      void qc.invalidateQueries({ queryKey: ['runs'] });
      void qc.invalidateQueries({ queryKey: ['metricas'] });
      for (const k of ['demanda', 'reglas', 'segmentos']) void qc.invalidateQueries({ queryKey: [k] });
    },
    onError: (e) => { avisar(mensajeError(e), 'error'); void qc.invalidateQueries({ queryKey: ['runs'] }); },
  });

  const f = fuente.data;
  const m = metricas.data;
  const d = m?.detalle;
  const r = importar.data;

  // Estado de cada paso, en palabras
  const porCargar = f ? Math.max(0, f.source_orders - f.loaded_orders) : 0;
  const estadoPedidos = !f ? { texto: '…', tono: 'neutral' as Tono }
    : !f.exists ? { texto: 'Sin archivo', tono: 'danger' as Tono }
    : porCargar > 0 ? { texto: `${formatoNum(porCargar)} por cargar`, tono: 'warn' as Tono }
    : { texto: 'Al día', tono: 'ok' as Tono };
  const pedidosMasNuevos = !!(f?.last_import_at && m?.ultimo_run && new Date(f.last_import_at) > new Date(m.ultimo_run));
  const estadoModelos = !m?.disponible ? { texto: 'Sin calcular', tono: 'warn' as Tono }
    : pedidosMasNuevos ? { texto: 'Hay pedidos nuevos', tono: 'warn' as Tono }
    : { texto: 'Al día', tono: 'ok' as Tono };

  const calDem = calidadDemanda(m?.r2);
  const calSeg = calidadSegmentos(m?.silhouette);
  const mejora = mejoraSobreBase(m?.mae, d?.demanda?.mae_baseline_lag7);
  const ultimas = (runs.data ?? []).slice(0, 5);

  return (
    <div className="page sobria">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Datos</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>Tus <em>datos</em></h1>
        <p className="lead rise" style={vars({ '--i': 2 })}>Dos pasos: trae los pedidos nuevos y luego actualiza las predicciones.</p>
      </header>

      {fuente.isError && <Alert tone="danger" title="No se pudo consultar el archivo de pedidos" role="alert">{mensajeError(fuente.error)}</Alert>}

      <div className="ux-pasos rise" style={vars({ '--i': 3 })}>
        <Paso n={1} titulo="Pedidos" estado={estadoPedidos}>
          {fuente.isLoading ? <Skeleton ancho="60%" /> : (
            <>
              <p className="ux-cifra">{formatoNum(f?.loaded_orders)} <span>pedidos guardados</span></p>
              <p className="muted small">{f?.last_import_at ? `Última sincronización ${formatoHace(f.last_import_at)}.` : 'Aún no se ha sincronizado.'}</p>
            </>
          )}
          <Button variant="secondary" icon="next" loading={importar.isPending} disabled={!f?.exists} onClick={() => importar.mutate()}>
            {forzarImportacion ? 'Reconciliar todo' : 'Sincronizar pedidos'}
          </Button>
        </Paso>

        <Paso n={2} titulo="Predicciones" estado={estadoModelos}>
          {metricas.isLoading ? <Skeleton ancho="60%" /> : (
            <>
              <p className="ux-cifra">{m?.disponible ? formatoHace(m.ultimo_run) : '—'} <span>última actualización</span></p>
              <p className="muted small">{m?.disponible ? `Con ${formatoNum(d?.demanda?.dias_historia)} días de historia.` : 'Aún no se han calculado.'}</p>
            </>
          )}
          <Button icon="next" loading={ejecutar.isPending} onClick={() => ejecutar.mutate()}>Actualizar predicciones</Button>
        </Paso>

        <Paso n={3} titulo="Resultados" estado={m?.disponible ? { texto: 'Listos', tono: 'ok' } : { texto: 'Pendientes', tono: 'neutral' }}>
          <p className="ux-cifra">3 <span>respuestas</span></p>
          <p className="muted small">Qué vas a vender, qué se pide junto y quiénes son tus clientes.</p>
          <Link className={btnClass('secondary')} to="/analitica">Ver predicciones</Link>
        </Paso>
      </div>

      {/* Respuestas de las acciones: un solo lugar, anunciado a lectores de pantalla */}
      <div aria-live="polite" className="stack ux-avisos">
        {ejecutar.isPending && <p className="muted small">Entrenando los modelos… tarda unos segundos.</p>}
        {ejecutar.isError && <Alert tone="danger" title="No se pudieron actualizar las predicciones" role="alert">{mensajeError(ejecutar.error)}</Alert>}
        {importar.isError && <Alert tone="danger" title="La sincronización no se completó" role="alert">{mensajeError(importar.error)}</Alert>}
        {r && (
          <Alert tone={r.status === 'SUCCESS' || r.status === 'SIN_CAMBIOS' ? 'ok' : 'warn'} title={r.message || `Sincronización: ${r.status}`} role="status">
            {formatoNum(r.inserted)} nuevos · {formatoNum(r.updated)} actualizados · {formatoNum(r.unchanged)} sin cambios
            {r.skipped > 0 && ` · ${formatoNum(r.skipped)} omitidos`}
          </Alert>
        )}
      </div>

      <div className="grid-2">
        <Card className="rise" style={vars({ '--i': 4 })}>
          <h2 className="ux-h">¿Qué tan buenos son los modelos?</h2>
          {metricas.isLoading ? <Skeleton ancho="100%" /> : !m?.disponible ? <p className="muted small">Se califican después de actualizar las predicciones.</p> : (
            <ul className="ux-modelos">
              <li>
                <div className="ux-fila"><b>Demanda</b><Pill tone={calDem.tono}>{calDem.texto}</Pill></div>
                <p className="muted small">Se equivoca ±{formatoDec(m.mae)} unidades por producto al día{mejora != null && `; ${mejora} % mejor que repetir la semana pasada`}.</p>
              </li>
              <li>
                <div className="ux-fila"><b>Combos</b><Pill tone={m.n_reglas ? 'ok' : 'neutral'}>{!m.n_reglas ? 'Sin combos' : nCombos != null ? `${formatoNum(nCombos)} combos` : `${formatoNum(m.n_reglas)} reglas`}</Pill></div>
                <p className="muted small">{m.n_reglas ? `El más fuerte se da ${formatoDec(d?.canasta?.lift_max)}× más que por azar.` : `Ningún par se repite lo suficiente en ${formatoNum(d?.canasta?.n_canastas)} pedidos.`}</p>
              </li>
              <li>
                <div className="ux-fila"><b>Tipos de clientes</b><Pill tone={calSeg.tono}>{calSeg.texto}</Pill></div>
                <p className="muted small">{m.k ?? '—'} grupos con {formatoNum(d?.segmentos?.n_clientes)} clientes.</p>
              </li>
            </ul>
          )}
        </Card>

        <Card className="rise" style={vars({ '--i': 5 })}>
          <h2 className="ux-h">Últimas actualizaciones</h2>
          {runs.isError && <Alert tone="danger" title="No se pudo cargar el historial" role="alert">{mensajeError(runs.error)}</Alert>}
          {runs.isLoading ? <Skeleton ancho="100%" /> : !ultimas.length ? <EmptyState icon="datos" title="Aún no hay actualizaciones">Usa «Actualizar predicciones» por primera vez.</EmptyState> : (
            <ul className="ux-corridas">
              {ultimas.map((x) => (
                <li key={x.id}>
                  <span>{formatoFecha(x.started_at, true)}</span>
                  <RunPill estado={x.status} />
                  <span className="muted small">{x.duracion_s != null ? `${formatoDec(x.duracion_s)} s` : '—'}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Detalle titulo="Opciones avanzadas">
        <div className="stack">
          <label className="row-gap small"><Switch checked={forzarImportacion} onChange={setForzarImportacion} label="Reconciliar todos los pedidos" /> Revisar todos los pedidos aunque el archivo no haya cambiado</label>
          <label className="row-gap small"><Switch checked={force} onChange={setForce} label="Forzar reentrenamiento" /> Recalcular las predicciones aunque no haya ventas nuevas</label>
          {f && (
            <p className="ux-tecnico">
              Archivo: <code style={{ overflowWrap: 'anywhere' }}>{f.source_path}</code> · {formatoNum(f.source_orders)} pedidos en el JSON ·
              observador cada {f.watcher_interval_seconds} s · la carga no entrena modelos (son pasos separados)
            </p>
          )}
        </div>
      </Detalle>

      <Detalle titulo={`Historial técnico completo (${runs.data?.length ?? 0})`}>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>#</th><th>Inicio</th><th>Estado</th><th className="num-cell">Ventas nuevas</th><th className="num-cell">Duración</th><th>Watermark</th><th>Detalle</th></tr></thead>
            <tbody>
              {(runs.data ?? []).map((x) => (
                <tr key={x.id}>
                  <td className="mono">{x.id}</td>
                  <td>{formatoFecha(x.started_at, true)}</td>
                  <td><RunPill estado={x.status} /></td>
                  <td className="num-cell">{formatoNum(x.rows_extracted)}</td>
                  <td className="num-cell">{x.duracion_s != null ? `${formatoDec(x.duracion_s)} s` : '—'}</td>
                  <td className="muted">{formatoFecha(x.watermark, true)}</td>
                  <td className="muted">{x.error ?? (x.metrics?.mensaje as string | undefined) ?? (x.metrics?.demanda?.model_version as string | undefined) ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Detalle>
    </div>
  );
}

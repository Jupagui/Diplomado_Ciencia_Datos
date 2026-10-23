import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ejecutarEtl, getMetricas, getRuns, mensajeError } from '../services/api';
import { Pill, RunPill } from '../ui/Badges';
import { Button } from '../ui/Button';
import { Switch } from '../ui/Inputs';
import { Alert, Card, CardHeader, EmptyState, Skeleton, Stat } from '../ui/Surfaces';
import { vars } from '../ui/cls';
import { formatoDec, formatoFecha, formatoNum } from '../ui/format';
import { useToast } from '../ui/useToast';

export default function Datos() {
  const qc = useQueryClient();
  const avisar = useToast();
  const [force, setForce] = useState(false);
  const runs = useQuery({ queryKey: ['runs'], queryFn: getRuns });
  const metricas = useQuery({ queryKey: ['metricas'], queryFn: getMetricas });

  const ejecutar = useMutation({
    mutationFn: () => ejecutarEtl(force),
    onSuccess: (r) => {
      avisar(r.status === 'SIN_CAMBIOS' ? 'Sin ventas nuevas: no se reentrenó (activa «Forzar» para reentrenar)' : `Pipeline completado en ${formatoDec(r.duracion_s)} s`, r.status === 'SUCCESS' ? 'ok' : 'info');
      void qc.invalidateQueries({ queryKey: ['runs'] });
      void qc.invalidateQueries({ queryKey: ['metricas'] });
      for (const k of ['demanda', 'reglas', 'segmentos']) void qc.invalidateQueries({ queryKey: [k] });
    },
    onError: (e) => { avisar(mensajeError(e), 'error'); void qc.invalidateQueries({ queryKey: ['runs'] }); },
  });

  const m = metricas.data;
  const d = m?.detalle;

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow rise" style={vars({ '--i': 0 })}>Pipeline de datos</p>
        <h1 className="title rise" style={vars({ '--i': 1 })}>ETL y <em>modelos</em></h1>
        <p className="lead rise" style={vars({ '--i': 2 })}>Extrae de forma incremental (watermark), transforma con Pandas, entrena los tres modelos y carga el esquema analítico.</p>
      </header>

      <Card feature className="rise" style={vars({ '--i': 3 })}>
        <CardHeader icon="datos" title="Ejecutar pipeline" />
        <div className="toolbar">
          <Button icon="next" loading={ejecutar.isPending} onClick={() => ejecutar.mutate()}>Ejecutar pipeline</Button>
          <label className="row-gap small"><Switch checked={force} onChange={setForce} label="Forzar reentrenamiento" /> Forzar reentrenamiento aunque no haya ventas nuevas</label>
        </div>
        {ejecutar.isPending && <p className="muted small" style={{ marginTop: 'var(--sp-2)' }}>Entrenando modelos… puede tardar unos segundos.</p>}
        {ejecutar.isError && <div style={{ marginTop: 'var(--sp-2)' }}><Alert tone="danger" title="El pipeline falló" role="alert">{mensajeError(ejecutar.error)}</Alert></div>}
      </Card>

      <div className="grid-3">
        <Card className="rise" style={vars({ '--i': 4 })}>
          <CardHeader level={3} icon="grafico" title="Demanda · XGBoost" />
          {metricas.isLoading ? <Skeleton ancho="60%" /> : !m?.disponible ? <p className="muted small">Sin ejecutar</p> : (
            <div className="stack">
              <Stat valor={formatoDec(m.mae)} etiqueta="MAE (unidades)" />
              <Stat valor={formatoDec(m.r2)} etiqueta="R² en prueba" />
              <small className="muted">Línea base lag-7: MAE {formatoDec(d?.demanda?.mae_baseline_lag7)} · {formatoNum(d?.demanda?.dias_historia)} días de historia</small>
            </div>
          )}
        </Card>
        <Card className="rise" style={vars({ '--i': 5 })}>
          <CardHeader level={3} icon="cruce" title="Venta cruzada · Apriori" />
          {metricas.isLoading ? <Skeleton ancho="60%" /> : !m?.disponible ? <p className="muted small">Sin ejecutar</p> : (
            <div className="stack">
              <Stat valor={formatoNum(m.n_reglas)} etiqueta="Reglas (lift > 1,2)" />
              <Stat valor={formatoDec(d?.canasta?.lift_max)} etiqueta="Lift máximo" />
              <small className="muted">{formatoNum(d?.canasta?.n_canastas)} canastas analizadas</small>
            </div>
          )}
        </Card>
        <Card className="rise" style={vars({ '--i': 6 })}>
          <CardHeader level={3} icon="usuarios" title="Segmentos · K-Means" />
          {metricas.isLoading ? <Skeleton ancho="60%" /> : !m?.disponible ? <p className="muted small">Sin ejecutar</p> : (
            <div className="stack">
              <Stat valor={formatoDec(m.silhouette)} etiqueta="Coeficiente de silueta" />
              <Stat valor={String(m.k ?? '—')} etiqueta="Clusters (k)" />
              <small className="muted">{formatoNum(d?.segmentos?.n_clientes)} clientes con compras</small>
            </div>
          )}
        </Card>
      </div>

      <Card className="rise" style={vars({ '--i': 7 })}>
        <CardHeader icon="historial" title="Historial de corridas" aside={m?.ultimo_run ? <span className="muted small">Última exitosa: {formatoFecha(m.ultimo_run, true)}</span> : undefined} />
        {runs.isError && <Alert tone="danger" title="No se pudo cargar el historial" role="alert">{mensajeError(runs.error)}</Alert>}
        {runs.isLoading ? <Skeleton ancho="100%" /> : !runs.data?.length ? <EmptyState icon="datos" title="Aún no hay corridas">Ejecuta el pipeline por primera vez.</EmptyState> : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>#</th><th>Inicio</th><th>Estado</th><th className="num-cell">Ventas nuevas</th><th className="num-cell">Duración</th><th>Watermark</th><th>Detalle</th></tr></thead>
              <tbody>
                {runs.data.map((r) => (
                  <tr key={r.id}>
                    <td className="mono">{r.id}</td>
                    <td>{formatoFecha(r.started_at, true)}</td>
                    <td><RunPill estado={r.status} /></td>
                    <td className="num-cell">{formatoNum(r.rows_extracted)}</td>
                    <td className="num-cell">{r.duracion_s != null ? `${formatoDec(r.duracion_s)} s` : '—'}</td>
                    <td className="muted">{formatoFecha(r.watermark, true)}</td>
                    <td className="muted">{r.error ?? (r.metrics?.mensaje as string | undefined) ?? (r.metrics?.demanda ? <Pill tone="gold">{r.metrics.demanda.model_version}</Pill> : '—')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

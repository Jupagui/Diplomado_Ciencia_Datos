"""Pipeline ETL: extrae, transforma, entrena los 3 modelos, carga y registra el run en etl_runs."""
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.errors import ErrorDominio, ErrorPipeline, ValidacionError
from app.domain.ports import AnalyticsRepo, CipherPort, EtlRunRepo, EtlSourcePort, Transaccion
from app.etl import transform as t
from app.etl.extract import DatosExtraidos, extraer
from app.etl.load import ResultadoModelos, cargar
from app.ml import basket_apriori, demand_xgb, rfm_kmeans


@dataclass
class ConfigAnalitica:
    apriori_min_support: float = 0.02
    apriori_min_confidence: float = 0.3
    apriori_min_lift: float = 1.2
    test_dias: int = 30
    semilla: int = 42


def ejecutar_modelos(datos: DatosExtraidos, cfg: ConfigAnalitica) -> ResultadoModelos:
    """Transformación + entrenamiento. Función pura sobre DataFrames (sin acceso a BD)."""
    items, productos, calidad = t.imputar(datos.items, datos.productos)
    if items.empty:
        raise ValidacionError("No hay ventas para analizar")
    version = datetime.now().strftime("%Y%m%d%H%M%S")
    res = ResultadoModelos(model_version=f"xgb-{version}")

    # --- Demanda (XGBoost) ---
    panel = t.construir_panel(items, productos)
    feat = t.agregar_features(panel)
    modelo, m_dem = demand_xgb.entrenar_evaluar(feat, cfg.test_dias, cfg.semilla)
    pron = demand_xgb.pronosticar(modelo, panel, 30)
    for horizonte in (7, 30):
        sub = pron[pron["paso"] <= horizonte]
        res.demanda += [{"product_id": int(r.product_id), "forecast_date": r.forecast_date, "horizon": horizonte,
                         "predicted_qty": float(r.predicted_qty)} for r in sub.itertuples()]
    m_dem["dias_historia"] = int(panel["fecha"].nunique())
    m_dem["model_version"] = res.model_version

    # --- Venta cruzada (Apriori) ---
    matriz = t.matriz_canasta(items, productos)
    reglas = basket_apriori.minar_reglas(matriz, cfg.apriori_min_support, cfg.apriori_min_confidence,
                                         cfg.apriori_min_lift)
    res.reglas = [{k: (float(v) if k in ("support", "confidence", "lift") else v) for k, v in row.items()}
                  for row in reglas.to_dict("records")]
    m_can = {"n_canastas": int(len(matriz)), "n_reglas": int(len(reglas)),
             "min_support": cfg.apriori_min_support, "min_confidence": cfg.apriori_min_confidence,
             "min_lift": cfg.apriori_min_lift,
             "lift_max": float(reglas["lift"].max()) if len(reglas) else None}

    # --- Segmentación (K-Means RFM) ---
    seg, m_seg = rfm_kmeans.segmentar(t.tabla_rfm(items), semilla=cfg.semilla)
    res.segmentos = [{"customer_id": int(r.customer_id), "recency": int(r.recency), "frequency": int(r.frequency),
                      "monetary": float(r.monetary), "cluster": int(r.cluster), "segment_label": r.segment_label}
                     for r in seg.itertuples()]

    res.metricas = {"calidad": calidad, "demanda": m_dem, "canasta": m_can, "segmentos": m_seg}
    return res


class PipelineETL:
    def __init__(self, source: EtlSourcePort, runs: EtlRunRepo, analytics: AnalyticsRepo, cipher: CipherPort,
                 tx: Transaccion, cfg: ConfigAnalitica | None = None):
        self.source, self.runs, self.analytics, self.cipher, self.tx = source, runs, analytics, cipher, tx
        self.cfg = cfg or ConfigAnalitica()

    def ejecutar(self, force: bool = False) -> dict[str, Any]:
        previo = self.runs.ultimo_exitoso()
        wm = previo["watermark"] if previo else None
        run_id = self.runs.iniciar()
        self.tx.commit()
        t0 = time.perf_counter()
        try:
            nuevas = self.source.contar_ventas_desde(wm)
            if previo and nuevas == 0 and not force:
                run = self.runs.finalizar(run_id, "SIN_CAMBIOS", wm, 0,
                                          {"mensaje": "Sin ventas nuevas desde el último watermark",
                                           "duracion_s": round(time.perf_counter() - t0, 3)}, None)
                self.tx.commit()
                return run
            datos = extraer(self.source, self.cipher, wm)
            res = ejecutar_modelos(datos, self.cfg)
            cargar(self.analytics, res)
            res.metricas["ventas_nuevas"] = datos.ventas_nuevas
            res.metricas["duracion_s"] = round(time.perf_counter() - t0, 3)
            run = self.runs.finalizar(run_id, "SUCCESS", self.source.max_fecha_venta(), datos.ventas_nuevas,
                                      res.metricas, None)
            self.tx.commit()
            return run
        except Exception as e:
            self.tx.rollback()
            self.runs.finalizar(run_id, "FAILED", wm, 0, {"duracion_s": round(time.perf_counter() - t0, 3)}, str(e))
            self.tx.commit()
            if isinstance(e, ErrorDominio):
                raise
            raise ErrorPipeline(f"Falló el ETL: {e}") from e

"""Casos de uso de analítica: ejecutar el ETL y consultar resultados (solo depende de puertos)."""
from collections import defaultdict
from typing import Any

from app.domain.errors import NoEncontrado, ValidacionError
from app.domain.ports import AnalyticsRepo, EtlRunRepo


class ServicioAnalitica:
    def __init__(self, pipeline, runs: EtlRunRepo, analytics: AnalyticsRepo):
        self.pipeline = pipeline  # PipelineETL (expone ejecutar(force))
        self.runs = runs
        self.analytics = analytics

    def ejecutar_etl(self, force: bool = False) -> dict[str, Any]:
        return self.pipeline.ejecutar(force)

    def listar_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.runs.listar(limit)

    def demanda(self, horizon: int, product_id: int | None = None) -> list[dict[str, Any]]:
        if horizon not in (7, 30):
            raise ValidacionError("horizon debe ser 7 o 30")
        filas = self.analytics.demanda(horizon, product_id)
        if product_id and not filas:
            raise NoEncontrado(f"Sin pronóstico para el producto {product_id}; ejecute el ETL")
        por_prod: dict[int, dict[str, Any]] = {}
        for f in filas:
            p = por_prod.setdefault(f["product_id"], {
                "product_id": f["product_id"], "name": f["name"], "sku": f["sku"], "category": f["category"],
                "stock": f["stock"], "horizon": horizon, "total_predicho": 0.0, "model_version": f["model_version"],
                "diaria": []})
            p["total_predicho"] = round(p["total_predicho"] + f["predicted_qty"], 3)
            p["diaria"].append({"fecha": f["forecast_date"], "cantidad": f["predicted_qty"]})
        return sorted(por_prod.values(), key=lambda x: -x["total_predicho"])

    def reglas(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.analytics.reglas(limit)

    def segmentos(self) -> dict[str, Any]:
        filas = self.analytics.segmentos()
        grupos: dict[int, list[dict]] = defaultdict(list)
        for f in filas:
            grupos[f["cluster"]].append(f)
        resumen = []
        for c, g in sorted(grupos.items()):
            n = len(g)
            resumen.append({"cluster": c, "segmento": g[0]["segment_label"], "n_clientes": n,
                            "recencia_media": round(sum(x["recency"] for x in g) / n, 1),
                            "frecuencia_media": round(sum(x["frequency"] for x in g) / n, 1),
                            "monetario_medio": round(sum(x["monetary"] for x in g) / n, 2),
                            "monetario_total": round(sum(x["monetary"] for x in g), 2)})
        return {"resumen": resumen, "clientes": filas}

    def metricas(self) -> dict[str, Any]:
        run = self.runs.ultimo_exitoso()
        if run is None:
            return {"disponible": False, "mae": None, "r2": None, "silhouette": None, "k": None,
                    "n_reglas": None, "ultimo_run": None, "detalle": None}
        m = run["metrics"] or {}
        dem, seg, can = m.get("demanda", {}), m.get("segmentos", {}), m.get("canasta", {})
        return {"disponible": True, "mae": dem.get("mae"), "r2": dem.get("r2"), "silhouette": seg.get("silhouette"),
                "k": seg.get("k"), "n_reglas": can.get("n_reglas"), "ultimo_run": run["finished_at"],
                "run_id": run["id"], "detalle": m}

"""Adaptadores SQLAlchemy: fuente del ETL, registro de runs y tablas analíticas."""
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence import models as m


class EtlSourceSQL:
    def __init__(self, s: Session):
        self.s = s

    def contar_ventas_desde(self, watermark: datetime | None) -> int:
        stmt = select(func.count(m.SaleModel.id)).where(m.SaleModel.status == "COMPLETED")
        if watermark is not None:
            stmt = stmt.where(m.SaleModel.created_at > watermark)
        return int(self.s.scalar(stmt))

    def max_fecha_venta(self) -> datetime | None:
        return self.s.scalar(select(func.max(m.SaleModel.created_at)))

    def items_ventas(self) -> list[dict[str, Any]]:
        filas = self.s.execute(
            select(m.SaleItemModel.sale_id, m.SaleModel.created_at, m.SaleModel.customer_id,
                   m.SaleItemModel.product_id, m.SaleItemModel.quantity, m.SaleItemModel.unit_price,
                   m.SaleItemModel.subtotal)
            .join(m.SaleModel, m.SaleModel.id == m.SaleItemModel.sale_id)
            .where(m.SaleModel.status == "COMPLETED").order_by(m.SaleModel.created_at))
        return [dict(f._mapping) for f in filas]

    def productos(self) -> list[dict[str, Any]]:
        filas = self.s.execute(select(m.ProductModel.id, m.ProductModel.sku, m.ProductModel.name,
                                      m.ProductModel.category, m.ProductModel.unit_price, m.ProductModel.unit_cost,
                                      m.ProductModel.stock, m.ProductModel.is_active))
        return [dict(f._mapping) for f in filas]

    def clientes(self) -> list[dict[str, Any]]:
        filas = self.s.execute(select(m.CustomerModel.id, m.CustomerModel.first_name, m.CustomerModel.last_name,
                                      m.CustomerModel.encrypted_email, m.CustomerModel.encrypted_phone,
                                      m.CustomerModel.created_at))
        return [dict(f._mapping) for f in filas]


def _run(r: m.EtlRunModel) -> dict[str, Any]:
    dur = (r.finished_at - r.started_at).total_seconds() if r.finished_at else None
    return {"id": r.id, "started_at": r.started_at, "finished_at": r.finished_at, "status": r.status,
            "watermark": r.watermark, "rows_extracted": r.rows_extracted, "metrics": r.metrics,
            "error": r.error, "duracion_s": round(dur, 3) if dur is not None else None}


class EtlRunRepoSQL:
    def __init__(self, s: Session):
        self.s = s

    def iniciar(self) -> int:
        r = m.EtlRunModel(started_at=datetime.now(), status="RUNNING")
        self.s.add(r)
        self.s.flush()
        return r.id

    def finalizar(self, run_id, status, watermark, rows_extracted, metrics, error):
        r = self.s.get(m.EtlRunModel, run_id)
        r.status, r.watermark, r.rows_extracted = status, watermark, rows_extracted
        r.metrics, r.error, r.finished_at = metrics, error, datetime.now()
        self.s.flush()
        return _run(r)

    def ultimo_exitoso(self):
        r = self.s.scalar(select(m.EtlRunModel).where(m.EtlRunModel.status == "SUCCESS")
                          .order_by(m.EtlRunModel.id.desc()).limit(1))
        return _run(r) if r else None

    def listar(self, limit=20):
        return [_run(r) for r in self.s.scalars(select(m.EtlRunModel).order_by(m.EtlRunModel.id.desc()).limit(limit))]


class AnalyticsRepoSQL:
    def __init__(self, s: Session):
        self.s = s

    def reemplazar_demanda(self, filas, model_version):
        self.s.execute(delete(m.DemandForecastModel))
        if filas:
            self.s.execute(insert(m.DemandForecastModel),
                           [{**f, "model_version": model_version, "created_at": datetime.now()} for f in filas])

    def reemplazar_reglas(self, filas):
        self.s.execute(delete(m.MarketBasketRuleModel))
        if filas:
            self.s.execute(insert(m.MarketBasketRuleModel), [{**f, "created_at": datetime.now()} for f in filas])

    def reemplazar_segmentos(self, filas):
        self.s.execute(delete(m.CustomerSegmentModel))
        if filas:
            self.s.execute(insert(m.CustomerSegmentModel), [{**f, "created_at": datetime.now()} for f in filas])

    def demanda(self, horizon, product_id=None):
        stmt = (select(m.DemandForecastModel.product_id, m.ProductModel.name, m.ProductModel.sku,
                       m.ProductModel.category, m.ProductModel.stock, m.DemandForecastModel.forecast_date,
                       m.DemandForecastModel.predicted_qty, m.DemandForecastModel.model_version)
                .join(m.ProductModel, m.ProductModel.id == m.DemandForecastModel.product_id)
                .where(m.DemandForecastModel.horizon == horizon))
        if product_id:
            stmt = stmt.where(m.DemandForecastModel.product_id == product_id)
        stmt = stmt.order_by(m.DemandForecastModel.product_id, m.DemandForecastModel.forecast_date)
        return [dict(f._mapping) for f in self.s.execute(stmt)]

    def reglas(self, limit=100):
        filas = self.s.scalars(select(m.MarketBasketRuleModel)
                               .order_by(m.MarketBasketRuleModel.lift.desc()).limit(limit))
        return [{"id": r.id, "antecedent": r.antecedent, "consequent": r.consequent, "support": r.support,
                 "confidence": r.confidence, "lift": r.lift} for r in filas]

    def segmentos(self):
        stmt = (select(m.CustomerSegmentModel.customer_id, m.CustomerModel.first_name, m.CustomerModel.last_name,
                       m.CustomerSegmentModel.recency, m.CustomerSegmentModel.frequency,
                       m.CustomerSegmentModel.monetary, m.CustomerSegmentModel.cluster,
                       m.CustomerSegmentModel.segment_label)
                .join(m.CustomerModel, m.CustomerModel.id == m.CustomerSegmentModel.customer_id)
                .order_by(m.CustomerSegmentModel.cluster, m.CustomerSegmentModel.customer_id))
        return [dict(f._mapping) for f in self.s.execute(stmt)]

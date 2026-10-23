from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class EtlRunOut(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    watermark: datetime | None
    rows_extracted: int
    duracion_s: float | None
    metrics: dict[str, Any] | None
    error: str | None


class PuntoDemanda(BaseModel):
    fecha: date
    cantidad: float


class DemandaProductoOut(BaseModel):
    product_id: int
    name: str
    sku: str
    category: str | None
    stock: int
    horizon: int
    total_predicho: float
    model_version: str
    diaria: list[PuntoDemanda]


class ReglaOut(BaseModel):
    id: int
    antecedent: str
    consequent: str
    support: float
    confidence: float
    lift: float


class ResumenSegmento(BaseModel):
    cluster: int
    segmento: str
    n_clientes: int
    recencia_media: float
    frecuencia_media: float
    monetario_medio: float
    monetario_total: float


class ClienteSegmentoOut(BaseModel):
    customer_id: int
    first_name: str
    last_name: str
    recency: int
    frequency: int
    monetary: float
    cluster: int
    segment_label: str


class SegmentosOut(BaseModel):
    resumen: list[ResumenSegmento]
    clientes: list[ClienteSegmentoOut]


class MetricasOut(BaseModel):
    disponible: bool
    mae: float | None
    r2: float | None
    silhouette: float | None
    k: int | None
    n_reglas: int | None
    ultimo_run: datetime | None
    run_id: int | None = None
    detalle: dict[str, Any] | None


class PreguntaIn(BaseModel):
    pregunta: str = Field(min_length=1, max_length=2000)

"""Carga: persiste los resultados en el esquema analítico (reemplazo por versión de modelo)."""
from dataclasses import dataclass, field
from typing import Any

from app.domain.ports import AnalyticsRepo


@dataclass
class ResultadoModelos:
    model_version: str
    demanda: list[dict[str, Any]] = field(default_factory=list)
    reglas: list[dict[str, Any]] = field(default_factory=list)
    segmentos: list[dict[str, Any]] = field(default_factory=list)
    metricas: dict[str, Any] = field(default_factory=dict)


def cargar(repo: AnalyticsRepo, r: ResultadoModelos) -> None:
    repo.reemplazar_demanda(r.demanda, r.model_version)
    repo.reemplazar_reglas(r.reglas)
    repo.reemplazar_segmentos(r.segmentos)

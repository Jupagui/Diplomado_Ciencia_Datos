"""Contrato Pydantic del asesor estratégico (salida validada del LLM o del asesor simulado)."""
from typing import Literal

from pydantic import BaseModel, Field


class Accion(BaseModel):
    accion: str = Field(min_length=5, description="Acción concreta y accionable")
    justificacion: str = Field(min_length=5, description="Por qué, apoyada en los datos")
    impacto_estimado: str = Field(min_length=3, description="Impacto esperado (cualitativo o cuantitativo)")
    riesgo: Literal["bajo", "medio", "alto"]
    datos_citados: list[str] = Field(default_factory=list,
                                     description="Cifras analíticas concretas que respaldan la acción")
    descuento_pct: float | None = Field(default=None, ge=0, le=100,
                                        description="Descuento propuesto (%), si la acción implica uno")


class PlanBase(BaseModel):
    """Esquema que se le pide al LLM."""
    resumen: str = Field(min_length=5)
    acciones: list[Accion] = Field(min_length=1, max_length=5)
    advertencias: list[str] = Field(default_factory=list)


class PlanAccion(PlanBase):
    """Plan final devuelto por la API (incluye el modo del asesor)."""
    modo: Literal["gemini", "simulado"] = "simulado"

"""Asesor estratégico: contexto analítico + guardrails (red teaming) + reintento sobre el contrato PlanAccion."""
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import holidays
from pydantic import ValidationError

from app.application.analitica import ServicioAnalitica
from app.application.kpis import ServicioKpis
from app.domain.errors import ErrorDominio, ValidacionError
from app.domain.plan_accion import PlanAccion, PlanBase
from app.domain.ports import AdvisorPort

MAX_DESCUENTO_PCT = 30.0
_PALABRAS_DESCUENTO = re.compile(r"descuent|rebaj|promoci|\bdto\b|oferta|liquidaci", re.I)
_PORCENTAJE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


class PlanRechazado(ErrorDominio):
    """Todas las acciones del plan violaron algún guardrail."""


def _descuento_en_texto(texto: str) -> float:
    """Mayor porcentaje de descuento mencionado en el texto (0 si ninguno)."""
    mayor = 0.0
    for frase in re.split(r"[.;\n]", texto):
        if _PALABRAS_DESCUENTO.search(frase):
            for p in _PORCENTAJE.findall(frase):
                mayor = max(mayor, float(p.replace(",", ".")))
    return mayor


def aplicar_guardrails(plan: PlanBase) -> PlanBase:
    """Descarta acciones con descuento > 30% o sin datos citados. Falla si no queda ninguna."""
    validas, advertencias = [], list(plan.advertencias)
    for a in plan.acciones:
        citados = [d for d in a.datos_citados if d and d.strip()]
        if not citados:
            advertencias.append(f"Acción descartada por no citar datos analíticos: «{a.accion[:80]}»")
            continue
        descuento = max(a.descuento_pct or 0.0, _descuento_en_texto(f"{a.accion}. {a.justificacion}"))
        if descuento > MAX_DESCUENTO_PCT:
            advertencias.append(f"Acción descartada: propone un descuento de {descuento:g}%, "
                                f"superior al máximo permitido de {MAX_DESCUENTO_PCT:g}%: «{a.accion[:80]}»")
            continue
        validas.append(a.model_copy(update={"datos_citados": citados}))
    if not validas:
        raise PlanRechazado("; ".join(advertencias) or "Plan sin acciones válidas")
    return PlanBase(resumen=plan.resumen, acciones=validas, advertencias=advertencias)


def proximos_festivos(hoy: date | None = None, dias: int = 60) -> list[dict[str, Any]]:
    hoy = hoy or date.today()
    fest = holidays.Colombia(years=[hoy.year, hoy.year + 1])
    return [{"fecha": str(d), "nombre": n, "en_dias": (d - hoy).days}
            for d, n in sorted(fest.items()) if 0 <= (d - hoy).days <= dias]


def estacionalidad(serie_diaria: list[dict[str, Any]], hoy: date | None = None) -> dict[str, Any]:
    """Factores (promedio / promedio global) por mes y por día de la semana a partir de la serie diaria."""
    hoy = hoy or date.today()
    if not serie_diaria:
        return {}
    por_mes, por_dow = defaultdict(list), defaultdict(list)
    for p in serie_diaria:
        d = date.fromisoformat(str(p["fecha"])[:10])
        por_mes[d.month].append(p["total"])
        por_dow[d.weekday()].append(p["total"])
    todos = [p["total"] for p in serie_diaria]
    glob = sum(todos) / len(todos) or 1.0
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    f_mes = {mes: round(sum(v) / len(v) / glob, 2) for mes, v in sorted(por_mes.items())}
    f_dow = {dias[k]: round(sum(v) / len(v) / glob, 2) for k, v in sorted(por_dow.items())}
    return {"factor_por_mes": f_mes, "factor_por_dia_semana": f_dow, "mes_actual": hoy.month,
            "factor_mes_actual": f_mes.get(hoy.month), "mes_pico": max(f_mes, key=f_mes.get),
            "dia_pico": max(f_dow, key=f_dow.get)}


def _limpiar_json(texto: str) -> str:
    t = texto.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    return t


class ServicioAsesor:
    def __init__(self, advisor: AdvisorPort, respaldo: AdvisorPort, analitica: ServicioAnalitica,
                 kpis: ServicioKpis):
        self.advisor, self.respaldo, self.analitica, self.kpis = advisor, respaldo, analitica, kpis

    def construir_contexto(self, hoy: date | None = None) -> dict[str, Any]:
        hoy = hoy or date.today()
        metricas = self.analitica.metricas()
        k30 = self.kpis.resumen(30, 5)
        k365 = self.kpis.resumen(365, 1)
        ctx: dict[str, Any] = {
            "fecha_hoy": str(hoy),
            "hay_datos_analiticos": bool(metricas["disponible"]),
            "kpis_30d": {k: k30[k] for k in ("total_ventas", "n_ventas", "ticket_promedio", "margen", "margen_pct",
                                              "rotacion", "valor_inventario", "productos_bajo_stock")},
            "top_productos_30d": k30["top_productos"],
            "ventas_por_categoria_30d": k30["ventas_por_categoria"],
            "festivos_proximos_co": proximos_festivos(hoy),
            "estacionalidad": estacionalidad(k365["serie_diaria"], hoy),
            "metricas_modelos": {k: metricas[k] for k in ("mae", "r2", "silhouette", "k", "n_reglas")},
        }
        if metricas["disponible"]:
            dem = self.analitica.demanda(7)
            ctx["demanda_7d"] = [{"producto": d["name"], "stock": d["stock"], "total_predicho": d["total_predicho"]}
                                 for d in dem[:15]]
            ctx["reglas_venta_cruzada"] = [{k: r[k] for k in ("antecedent", "consequent", "support", "confidence", "lift")}
                                           for r in self.analitica.reglas(8)]
            ctx["segmentos"] = self.analitica.segmentos()["resumen"]
        else:
            ctx.update(demanda_7d=[], reglas_venta_cruzada=[], segmentos=[])
        return ctx

    def _plan_desde(self, advisor: AdvisorPort, pregunta: str, ctx: dict) -> PlanBase:
        """Genera y valida el plan; reintenta UNA vez si el JSON no cumple el contrato."""
        error = None
        for _ in range(2):
            texto = advisor.generar(pregunta, ctx, error)
            try:
                return PlanBase.model_validate_json(_limpiar_json(texto))
            except (ValidationError, ValueError) as e:
                error = str(e)[:600]
        raise ValidacionError(f"El asesor no devolvió un JSON válido tras un reintento: {error}")

    def preguntar(self, pregunta: str) -> PlanAccion:
        pregunta = pregunta.strip()
        if not pregunta:
            raise ValidacionError("La pregunta no puede estar vacía")
        ctx = self.construir_contexto()
        modo, extra = self.advisor.modo, []
        try:
            plan = aplicar_guardrails(self._plan_desde(self.advisor, pregunta, ctx))
        except Exception as e:  # JSON inválido, guardrails o falla del proveedor -> respaldo determinístico
            extra.append(f"El asesor principal no produjo un plan válido ({str(e)[:200]}); "
                         f"se usó el asesor simulado.")
            plan = aplicar_guardrails(self._plan_desde(self.respaldo, pregunta, ctx))
            modo = self.respaldo.modo
        return PlanAccion(resumen=plan.resumen, acciones=plan.acciones,
                          advertencias=plan.advertencias + extra, modo=modo)

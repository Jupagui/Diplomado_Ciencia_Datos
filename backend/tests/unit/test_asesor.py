"""Contrato PlanAccion, guardrails, reintento, respaldo y seleccion Gemini/simulado."""
import json
from datetime import date

import pytest
from pydantic import ValidationError

from app.adapters.inbound.api import deps
from app.adapters.outbound.llm.mock_advisor import MockAdvisor
from app.application.asesor import (PlanRechazado, ServicioAsesor, _descuento_en_texto, aplicar_guardrails,
                                    estacionalidad, proximos_festivos)
from app.domain.errors import ValidacionError
from app.domain.plan_accion import Accion, PlanAccion, PlanBase


def accion(**kw):
    base = dict(accion="Reponer cafe de inmediato", justificacion="La demanda proyectada supera el stock",
                impacto_estimado="Evita quiebres", riesgo="bajo", datos_citados=["Cafe: demanda 7d 40 u. vs stock 10 u."])
    base.update(kw)
    return Accion(**base)


def plan(*acciones, advertencias=()):
    return PlanBase(resumen="Resumen del plan", acciones=list(acciones), advertencias=list(advertencias))


# ---- Contrato
def test_contrato_acepta_valido():
    p = PlanAccion(resumen="Resumen largo", acciones=[accion()])
    assert p.modo == "simulado"


@pytest.mark.parametrize("acciones", [[], [accion()] * 6])
def test_contrato_1_a_5_acciones(acciones):
    with pytest.raises(ValidationError):
        PlanBase(resumen="Resumen largo", acciones=acciones)


def test_contrato_riesgo_y_descuento_validos():
    with pytest.raises(ValidationError):
        accion(riesgo="extremo")
    with pytest.raises(ValidationError):
        accion(descuento_pct=120)
    with pytest.raises(ValidationError):
        PlanAccion(resumen="Resumen largo", acciones=[accion()], modo="otro")


# ---- Guardrails
def test_guardrail_descuento_40_descartado_con_advertencia():
    r = aplicar_guardrails(plan(accion(), accion(accion="Liquidar con descuento", descuento_pct=40)))
    assert len(r.acciones) == 1 and r.acciones[0].descuento_pct is None
    assert any("40" in a and "30" in a for a in r.advertencias)


def test_guardrail_descuento_exacto_30_pasa():
    r = aplicar_guardrails(plan(accion(descuento_pct=30)))
    assert len(r.acciones) == 1 and not r.advertencias


def test_guardrail_descuento_en_texto():
    r = aplicar_guardrails(plan(accion(), accion(accion="Promoción del 50% en pan de bono")))
    assert len(r.acciones) == 1
    assert any("50" in a for a in r.advertencias)
    r2 = aplicar_guardrails(plan(accion(), accion(accion="Subir el precio", justificacion="Hay un descuento del 45%.")))
    assert len(r2.acciones) == 1


def test_guardrail_porcentaje_sin_palabra_de_descuento_no_se_confunde():
    r = aplicar_guardrails(plan(accion(justificacion="El margen es 60% y el soporte 45% de las canastas")))
    assert len(r.acciones) == 1


@pytest.mark.parametrize("datos", [[], ["", "   "]])
def test_guardrail_sin_datos_citados_descartada(datos):
    r = aplicar_guardrails(plan(accion(), accion(accion="Cambiar la vitrina", datos_citados=datos)))
    assert len(r.acciones) == 1
    assert any("no citar datos" in a for a in r.advertencias)


def test_guardrail_limpia_datos_vacios_y_conserva_advertencias():
    r = aplicar_guardrails(plan(accion(datos_citados=["dato real", " "]), advertencias=["previa"]))
    assert r.acciones[0].datos_citados == ["dato real"] and r.advertencias == ["previa"]


def test_guardrail_ninguna_sobrevive_lanza():
    with pytest.raises(PlanRechazado):
        aplicar_guardrails(plan(accion(descuento_pct=60), accion(datos_citados=[])))


def test_descuento_en_texto_helper():
    assert _descuento_en_texto("Haz un descuento del 35% y otro de 10%") == 35
    assert _descuento_en_texto("rebaja de 12,5 %") == 12.5
    assert _descuento_en_texto("Sube 80% el volumen") == 0


# ---- Servicio con asesor falso
class Analitica:
    def metricas(self):
        return {"disponible": False, "mae": None, "r2": None, "silhouette": None, "k": None, "n_reglas": None}


class Kpis:
    def resumen(self, dias=30, top=5, ahora=None):
        return {"total_ventas": 1000.0, "n_ventas": 5, "ticket_promedio": 200.0, "margen": 400.0,
                "margen_pct": 40.0, "rotacion": 1.0, "valor_inventario": 100.0, "productos_bajo_stock": 1,
                "top_productos": [], "ventas_por_categoria": [], "serie_diaria": []}


class AsesorFalso:
    def __init__(self, respuestas, modo="gemini"):
        self.respuestas, self.modo, self.llamadas = list(respuestas), modo, []

    def generar(self, pregunta, contexto, error_previo=None):
        self.llamadas.append(error_previo)
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r)


def _json(*acciones):
    return {"resumen": "Resumen del plan", "acciones": [a.model_dump() for a in acciones], "advertencias": []}


def svc(advisor):
    return ServicioAsesor(advisor, MockAdvisor(), Analitica(), Kpis())


def test_servicio_usa_asesor_principal_si_es_valido():
    a = AsesorFalso([_json(accion())])
    r = svc(a).preguntar("hola")
    assert r.modo == "gemini" and len(r.acciones) == 1 and len(a.llamadas) == 1


def test_servicio_descarta_malas_y_deja_advertencia():
    a = AsesorFalso([_json(accion(), accion(accion="Descuento total", descuento_pct=40),
                           accion(accion="Sin datos aqui", datos_citados=[]))])
    r = svc(a).preguntar("hola")
    assert r.modo == "gemini" and len(r.acciones) == 1
    assert len(r.advertencias) == 2


def test_servicio_json_invalido_reintenta_con_error_previo():
    a = AsesorFalso(["esto no es json", _json(accion())])
    r = svc(a).preguntar("hola")
    assert r.modo == "gemini" and len(a.llamadas) == 2
    assert a.llamadas[0] is None and a.llamadas[1]          # el reintento recibe el error
    assert not any("simulado" in w for w in r.advertencias)


def test_servicio_acepta_json_en_bloque_markdown():
    a = AsesorFalso(["```json\n" + json.dumps(_json(accion())) + "\n```"])
    assert svc(a).preguntar("hola").modo == "gemini"


def test_servicio_dos_json_invalidos_cae_al_simulado():
    a = AsesorFalso(["basura", "{\"resumen\": 1}"])
    r = svc(a).preguntar("hola")
    assert r.modo == "simulado" and len(a.llamadas) == 2
    assert any("simulado" in w for w in r.advertencias)
    assert r.acciones and all(x.datos_citados for x in r.acciones)


def test_servicio_ninguna_sobrevive_cae_al_simulado():
    a = AsesorFalso([_json(accion(descuento_pct=50), accion(datos_citados=[]))])
    r = svc(a).preguntar("hola")
    assert r.modo == "simulado" and any("simulado" in w for w in r.advertencias)


def test_servicio_falla_del_proveedor_cae_al_simulado():
    r = svc(AsesorFalso([RuntimeError("503 Gemini caido")])).preguntar("hola")
    assert r.modo == "simulado" and any("503" in w for w in r.advertencias)


def test_servicio_pregunta_vacia():
    with pytest.raises(ValidacionError):
        svc(AsesorFalso([])).preguntar("   ")


def test_mock_cumple_contrato_con_contexto_completo():
    ctx = {
        "kpis_30d": {"total_ventas": 5e6, "n_ventas": 300, "ticket_promedio": 16000, "margen_pct": 35.0,
                     "margen": 1.7e6},
        "hay_datos_analiticos": True,
        "demanda_7d": [{"producto": "Cafe", "stock": 10, "total_predicho": 40.0}],
        "reglas_venta_cruzada": [{"antecedent": "Cafe", "consequent": "Pan", "support": .1, "confidence": .6, "lift": 2.0}],
        "segmentos": [{"segmento": "En riesgo", "n_clientes": 20, "recencia_media": 90, "monetario_medio": 1e5}],
        "festivos_proximos_co": proximos_festivos(date(2026, 12, 1)),
        "estacionalidad": {"dia_pico": "sábado", "factor_mes_actual": 1.3},
        "ventas_por_categoria_30d": [{"category": "Bebidas", "ingresos": 1e6}],
    }
    texto = MockAdvisor().generar("dame todo", ctx)
    p = aplicar_guardrails(PlanBase.model_validate_json(texto))
    assert 1 <= len(p.acciones) <= 5 and len(p.acciones) == 5
    assert all(a.datos_citados for a in p.acciones)
    assert texto == MockAdvisor().generar("dame todo", ctx)   # determinista
    assert [a.descuento_pct for a in p.acciones if a.descuento_pct] == [10.0]


def test_festivos_y_estacionalidad():
    f = proximos_festivos(date(2026, 12, 1), dias=30)
    assert any(x["fecha"] == "2026-12-25" and x["en_dias"] == 24 for x in f)
    serie = [{"fecha": "2026-01-05", "total": 100.0}, {"fecha": "2026-01-06", "total": 300.0}]
    e = estacionalidad(serie, date(2026, 1, 10))
    assert e["factor_por_mes"] == {1: 1.0} and e["dia_pico"] == "martes"
    assert estacionalidad([]) == {}


# ---- Seleccion Gemini / simulado segun GEMINI_API_KEY (sin llamar a la API real)
class _Cfg:
    def __init__(self, key):
        self.gemini_api_key, self.gemini_model = key, "modelo-x"


def test_get_advisor_sin_key_es_simulado(monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: _Cfg(""))
    assert isinstance(deps.get_advisor(), MockAdvisor) and deps.get_advisor().modo == "simulado"


def test_get_advisor_con_key_es_gemini_sin_red(monkeypatch):
    creado = {}

    class GeminiFalso:
        modo = "gemini"

        def __init__(self, key, modelo):
            creado.update(key=key, modelo=modelo)

    monkeypatch.setattr(deps, "get_settings", lambda: _Cfg("K-123"))
    monkeypatch.setattr(deps, "GeminiAdvisor", GeminiFalso)
    a = deps.get_advisor()
    assert a.modo == "gemini" and creado == {"key": "K-123", "modelo": "modelo-x"}


def test_servicio_asesor_siempre_tiene_respaldo_simulado():
    s = deps.servicio_asesor(analitica=Analitica(), kpis=Kpis(), advisor=AsesorFalso([]))
    assert isinstance(s.respaldo, MockAdvisor)

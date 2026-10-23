"""401 en endpoints nuevos y comportamiento sin ETL previo."""
import json

import pytest

P = "/api/v1"


@pytest.mark.parametrize("metodo,ruta", [
    ("post", "/etl/run"), ("get", "/etl/runs"), ("get", "/analytics/demand?horizon=7"),
    ("get", "/analytics/basket"), ("get", "/analytics/segments"), ("get", "/analytics/metrics"),
    ("post", "/advisor/ask")])
def test_401_endpoints_fase2(client, metodo, ruta):
    kw = {"json": {"pregunta": "hola"}} if metodo == "post" else {}
    assert getattr(client, metodo)(P + ruta, **kw).status_code == 401


def test_metricas_sin_etl(client, auth):
    j = client.get(f"{P}/analytics/metrics", headers=auth).json()
    assert j["disponible"] is False and j["mae"] is None and j["n_reglas"] is None


def test_etl_sin_ventas_falla_con_mensaje_y_queda_FAILED(client, auth):
    r = client.post(f"{P}/etl/run", headers=auth)
    assert r.status_code == 422 and "ventas" in r.json()["detail"].lower()
    runs = client.get(f"{P}/etl/runs", headers=auth).json()
    assert runs[0]["status"] == "FAILED" and runs[0]["error"]


def test_asesor_sin_etl_sugiere_ejecutar_etl(client, auth):
    r = client.post(f"{P}/advisor/ask", headers=auth, json={"pregunta": "¿qué hago?"})
    assert r.status_code == 200
    j = r.json()
    assert j["modo"] == "simulado" and "ETL" in j["acciones"][0]["accion"]
    assert j["acciones"][0]["datos_citados"]


def test_demanda_sin_etl_lista_vacia(client, auth):
    assert client.get(f"{P}/analytics/demand?horizon=7", headers=auth).json() == []


def test_api_con_proveedor_gemini_falso_responde_modo_gemini(client, auth):
    """Con un proveedor 'gemini' (falso, sin red) el endpoint devuelve modo=gemini."""
    from app.adapters.inbound.api import deps
    from app.main import app

    class GeminiFalso:
        modo = "gemini"

        def generar(self, pregunta, contexto, error_previo=None):
            return json.dumps({"resumen": "Resumen del plan", "advertencias": [], "acciones": [{
                "accion": "Reponer cafe", "justificacion": "Demanda alta", "impacto_estimado": "Evita quiebres",
                "riesgo": "bajo", "datos_citados": ["Cafe: 40 u."]}]})

    app.dependency_overrides[deps.get_advisor] = lambda: GeminiFalso()
    r = client.post(f"{P}/advisor/ask", headers=auth, json={"pregunta": "hola"})
    assert r.status_code == 200 and r.json()["modo"] == "gemini"

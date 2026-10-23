"""Demanda, Apriori, K-Means, metricas y asesor via API sobre una BD sembrada con un run de ETL."""
import math
from datetime import date

import pytest
from sqlalchemy import func, select

from app.adapters.outbound.persistence import models as m
from tests.api.fase2_env import crear_entorno_fixture

env = crear_entorno_fixture()
P = "/api/v1"
ETIQUETAS = {"Campeones", "Leales", "En riesgo", "Perdidos", "Nuevos", "Ocasionales"}


@pytest.fixture(scope="module")
def corrida(env):
    r = env.client.post(f"{P}/etl/run", headers=env.auth)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "SUCCESS"
    return r.json()


# ---- Demanda
@pytest.mark.parametrize("horizon", [7, 30])
def test_demanda_horizontes(env, corrida, horizon):
    r = env.client.get(f"{P}/analytics/demand?horizon={horizon}", headers=env.auth)
    assert r.status_code == 200
    prods = r.json()
    assert len(prods) > 0
    for p in prods:
        assert p["horizon"] == horizon and len(p["diaria"]) == horizon
        assert all(d["cantidad"] >= 0 for d in p["diaria"])
        assert p["total_predicho"] >= 0
        assert p["total_predicho"] == pytest.approx(sum(d["cantidad"] for d in p["diaria"]), abs=0.01)
    assert [p["total_predicho"] for p in prods] == sorted((p["total_predicho"] for p in prods), reverse=True)
    # el pronostico empieza despues del ultimo dia de historia (hoy o antes) y es consecutivo
    fechas = [d["fecha"] for d in prods[0]["diaria"]]
    assert fechas == sorted(fechas) and date.fromisoformat(fechas[0]) <= date.today() + __import__("datetime").timedelta(days=1)


def test_demanda_30_incluye_los_7_primeros(env, corrida):
    d7 = {p["product_id"]: p for p in env.client.get(f"{P}/analytics/demand?horizon=7", headers=env.auth).json()}
    d30 = {p["product_id"]: p for p in env.client.get(f"{P}/analytics/demand?horizon=30", headers=env.auth).json()}
    pid = next(iter(d7))
    assert d30[pid]["diaria"][:7] == d7[pid]["diaria"]


def test_demanda_por_producto(env, corrida):
    pid = env.client.get(f"{P}/analytics/demand?horizon=7", headers=env.auth).json()[0]["product_id"]
    r = env.client.get(f"{P}/analytics/demand?horizon=7&product_id={pid}", headers=env.auth).json()
    assert len(r) == 1 and r[0]["product_id"] == pid
    assert env.client.get(f"{P}/analytics/demand?horizon=7&product_id=99999", headers=env.auth).status_code == 404


@pytest.mark.parametrize("h", [5, 0, 14])
def test_demanda_horizonte_invalido_422(env, corrida, h):
    assert env.client.get(f"{P}/analytics/demand?horizon={h}", headers=env.auth).status_code == 422


def test_metricas_demanda_finitas(env, corrida):
    j = env.client.get(f"{P}/analytics/metrics", headers=env.auth).json()
    assert j["disponible"] is True
    assert math.isfinite(j["mae"]) and j["mae"] >= 0
    assert math.isfinite(j["r2"])
    d = j["detalle"]["demanda"]
    assert d["n_train"] > 0 and d["n_test"] > 0
    assert math.isfinite(d["mae_baseline_lag7"]) and math.isfinite(d["r2_baseline_lag7"])


# ---- Apriori
def test_reglas_apriori(env, corrida):
    reglas = env.client.get(f"{P}/analytics/basket?limit=500", headers=env.auth).json()
    assert len(reglas) > 0
    for r in reglas:
        assert r["lift"] > 1.2
        assert 0 <= r["support"] <= 1 and 0 <= r["confidence"] <= 1
        assert r["antecedent"] and r["consequent"] and r["antecedent"] != r["consequent"]
    assert [r["lift"] for r in reglas] == sorted((r["lift"] for r in reglas), reverse=True)
    # el seed mete combos (cafe americano + croissant): debe aparecer alguna regla del catalogo
    assert any("Croissant" in r["antecedent"] + r["consequent"] for r in reglas)


def test_basket_limit(env, corrida):
    assert len(env.client.get(f"{P}/analytics/basket?limit=3", headers=env.auth).json()) <= 3


# ---- K-Means
def test_kmeans_segmentos(env, corrida):
    mt = env.client.get(f"{P}/analytics/metrics", headers=env.auth).json()
    assert -1 <= mt["silhouette"] <= 1
    assert 2 <= mt["k"] <= 6
    seg = env.client.get(f"{P}/analytics/segments", headers=env.auth).json()
    clientes, resumen = seg["clientes"], seg["resumen"]
    assert len(clientes) > 0
    assert {c["segment_label"] for c in clientes} <= ETIQUETAS
    assert {c["cluster"] for c in clientes} == {r["cluster"] for r in resumen}
    assert len(resumen) <= mt["k"]
    assert sum(r["n_clientes"] for r in resumen) == len(clientes)
    assert all(c["segment_label"] for c in clientes)
    assert all(c["recency"] >= 0 and c["frequency"] >= 1 and c["monetary"] > 0 for c in clientes)
    assert len({c["customer_id"] for c in clientes}) == len(clientes)


def test_todo_cliente_con_ventas_tiene_segmento(env, corrida):
    with env.sf() as s:
        con_ventas = {x for x in s.scalars(select(m.SaleModel.customer_id).where(
            m.SaleModel.customer_id.is_not(None)).distinct())}
    segs = {c["customer_id"] for c in env.client.get(f"{P}/analytics/segments", headers=env.auth).json()["clientes"]}
    assert con_ventas == segs


def test_silueta_por_k_en_rango(env, corrida):
    det = env.client.get(f"{P}/analytics/metrics", headers=env.auth).json()["detalle"]["segmentos"]
    assert all(-1 <= v <= 1 and 2 <= int(k) <= 6 for k, v in det["silhouette_por_k"].items())
    assert det["silhouette"] == pytest.approx(max(det["silhouette_por_k"].values()), abs=1e-3)


# ---- Metricas / persistencia
def test_metricas_coinciden_con_tablas(env, corrida):
    j = env.client.get(f"{P}/analytics/metrics", headers=env.auth).json()
    assert j["run_id"] == corrida["id"]
    with env.sf() as s:
        n = s.execute(select(func.count()).select_from(m.Base.metadata.tables["analytics_market_basket_rules"])).scalar()
        n_seg = s.execute(select(func.count()).select_from(m.Base.metadata.tables["analytics_customer_segments"])).scalar()
        run = s.execute(select(m.Base.metadata.tables["etl_runs"])).first()
    assert j["n_reglas"] == n > 0
    assert n_seg == j["detalle"]["segmentos"]["n_clientes"]
    assert run is not None


def test_pii_no_se_persiste_en_claro(env, corrida):
    with env.sf() as s:
        for tabla in ("analytics_customer_segments", "etl_runs"):
            for fila in s.execute(select(m.Base.metadata.tables[tabla])).all():
                assert "@example.com" not in str(fila)


# ---- Asesor via API (modo simulado: no hay key en tests)
def test_asesor_simulado_cumple_contrato(env, corrida):
    r = env.client.post(f"{P}/advisor/ask", headers=env.auth,
                        json={"pregunta": "¿Qué debo reponer y qué combos armo?"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["modo"] == "simulado" and j["resumen"]
    assert 1 <= len(j["acciones"]) <= 5
    for a in j["acciones"]:
        assert a["datos_citados"] and all(d.strip() for d in a["datos_citados"])
        assert a["riesgo"] in ("bajo", "medio", "alto")
        assert a["accion"] and a["justificacion"] and a["impacto_estimado"]
        assert (a["descuento_pct"] or 0) <= 30


def test_asesor_es_deterministico_y_prioriza_por_pregunta(env, corrida):
    q = {"pregunta": "Quiero mejorar el stock y la reposición"}
    a = env.client.post(f"{P}/advisor/ask", headers=env.auth, json=q).json()
    b = env.client.post(f"{P}/advisor/ask", headers=env.auth, json=q).json()
    assert a == b
    c = env.client.post(f"{P}/advisor/ask", headers=env.auth, json={"pregunta": "combos y canasta juntos"}).json()
    assert "combo" in c["acciones"][0]["accion"].lower()


def test_asesor_pregunta_vacia_422(env, corrida):
    assert env.client.post(f"{P}/advisor/ask", headers=env.auth, json={"pregunta": ""}).status_code == 422
    assert env.client.post(f"{P}/advisor/ask", headers=env.auth, json={"pregunta": "   "}).status_code == 422

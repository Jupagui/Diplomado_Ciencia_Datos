"""ETL incremental por watermark, force y persistencia. Flujo ordenado en una sola prueba."""
import pytest
from sqlalchemy import func, select

from app.adapters.outbound.persistence import models as m
from tests.api.fase2_env import crear_entorno_fixture

env = crear_entorno_fixture()
P = "/api/v1"


def _cuenta(env, modelo):
    with env.sf() as s:
        return s.scalar(select(func.count()).select_from(modelo))


def test_flujo_etl_incremental(env):
    c, h = env.client, env.auth
    assert _cuenta(env, m.AnalyticsDemandForecastModel) == 0 if hasattr(m, "AnalyticsDemandForecastModel") else True

    # 1) primer run
    r1 = c.post(f"{P}/etl/run", headers=h)
    assert r1.status_code == 200, r1.text
    j1 = r1.json()
    assert j1["status"] == "SUCCESS" and j1["rows_extracted"] > 0 and j1["watermark"]
    assert j1["metrics"] and {"demanda", "canasta", "segmentos", "calidad"} <= set(j1["metrics"])

    # 2) sin ventas nuevas
    r2 = c.post(f"{P}/etl/run", headers=h).json()
    assert r2["status"] == "SIN_CAMBIOS" and r2["rows_extracted"] == 0
    assert r2["watermark"] == j1["watermark"]

    # 3) venta nueva -> procesa de nuevo
    prods = c.get(f"{P}/products?solo_activos=true&limit=1000", headers=h).json()
    p = next(x for x in prods if x["stock"] > 5)
    v = c.post(f"{P}/sales", headers=h, json={"items": [{"product_id": p["id"], "quantity": 1}],
                                              "payment_method": "EFECTIVO"})
    assert v.status_code == 201
    r3 = c.post(f"{P}/etl/run", headers=h).json()
    assert r3["status"] == "SUCCESS"
    assert r3["metrics"]["ventas_nuevas"] == 1
    assert r3["watermark"] > j1["watermark"]

    # 4) de nuevo sin cambios y force=true reentrena
    assert c.post(f"{P}/etl/run", headers=h).json()["status"] == "SIN_CAMBIOS"
    rf = c.post(f"{P}/etl/run?force=true", headers=h).json()
    assert rf["status"] == "SUCCESS" and rf["metrics"]["demanda"]["mae"] is not None

    # 5) historial
    runs = c.get(f"{P}/etl/runs", headers=h).json()
    assert [x["status"] for x in runs][:5] == ["SUCCESS", "SIN_CAMBIOS", "SUCCESS", "SIN_CAMBIOS", "SUCCESS"]
    assert all(x["error"] is None for x in runs)


def test_tablas_analytics_pobladas_y_reemplazadas(env):
    # depende del flujo anterior (mismo modulo, mismo entorno)
    with env.sf() as s:
        for tabla in ("analytics_demand_forecast", "analytics_market_basket_rules",
                      "analytics_customer_segments"):
            n = s.execute(select(func.count()).select_from(m.Base.metadata.tables[tabla])).scalar()
            assert n > 0, tabla
        n_dem = s.execute(select(func.count()).select_from(
            m.Base.metadata.tables["analytics_demand_forecast"])).scalar()
        n_prod = s.scalar(select(func.count(m.ProductModel.id)))
        # 41 productos x (7 + 30) filas: el reentrenamiento reemplaza, no acumula
        assert n_dem == n_prod * 37

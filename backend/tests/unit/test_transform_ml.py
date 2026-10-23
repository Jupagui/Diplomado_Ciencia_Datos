"""Transformaciones sobre DataFrames hechos a mano y modelos sobre datos sinteticos pequenos."""
import math

import numpy as np
import pandas as pd
import pytest

from app.domain.errors import ValidacionError
from app.etl import transform as t
from app.ml import basket_apriori, demand_xgb, rfm_kmeans


# ---- Transform
def _panel(valores, pid=1, inicio="2025-03-03"):
    fechas = pd.date_range(inicio, periods=len(valores), freq="D")
    return pd.DataFrame({"fecha": fechas, "product_id": pid, "qty": np.array(valores, dtype=float)})


def test_lags_y_medias_moviles_a_mano():
    v = list(range(1, 31))  # 1..30
    f = t.agregar_features(_panel(v))
    fila = f.iloc[20]  # qty = 21
    assert fila["qty"] == 21
    assert fila["lag_1"] == 20 and fila["lag_7"] == 14 and fila["lag_14"] == 7
    assert fila["ma_7"] == pytest.approx(np.mean(v[13:20]))   # 14..20 (solo el pasado)
    assert math.isnan(f.iloc[0]["lag_1"]) and math.isnan(f.iloc[6]["lag_7"]) and not math.isnan(f.iloc[7]["lag_7"])
    assert math.isnan(f.iloc[6]["ma_7"]) and not math.isnan(f.iloc[7]["ma_7"])
    assert f.iloc[28]["ma_28"] == pytest.approx(np.mean(v[0:28]))


def test_sin_fuga_de_datos_el_futuro_no_cambia_las_features_pasadas():
    v = [float(x % 5 + 1) for x in range(40)]
    a = t.agregar_features(_panel(v))
    v2 = v.copy()
    v2[30:] = [999.0] * 10   # alterar solo el futuro
    b = t.agregar_features(_panel(v2))
    cols = ["lag_1", "lag_7", "lag_14", "ma_7", "ma_28"]
    pd.testing.assert_frame_equal(a.loc[:30, cols], b.loc[:30, cols])
    # la fila 30 tiene features distintas de qty 30 pero sus features solo usan el pasado
    assert a.loc[30, "lag_1"] == v[29]


def test_features_no_mezclan_productos():
    p = pd.concat([_panel([1.0] * 20, pid=1), _panel([100.0] * 20, pid=2)], ignore_index=True)
    f = t.agregar_features(p)
    assert (f[f.product_id == 1]["lag_1"].dropna() == 1).all()
    assert (f[f.product_id == 2]["lag_1"].dropna() == 100).all()


def test_festivos_y_calendario():
    p = _panel([1.0] * 3, inicio="2025-12-24")  # 25-dic es festivo en CO
    f = t.agregar_features(p)
    assert list(f["is_holiday"]) == [0, 1, 0]
    assert list(f["dow"]) == [2, 3, 4] and (f["month"] == 12).all()


def _items():
    return pd.DataFrame({
        "sale_id": [1, 1, 2, 2, 3, 4, 4],
        "created_at": pd.to_datetime(["2025-01-01 10:00"] * 2 + ["2025-01-02 10:00"] * 2 + ["2025-01-02 11:00"]
                                     + ["2025-01-03 09:00"] * 2),
        "customer_id": [10, 10, 11, 11, None, 10, 10],
        "product_id": [1, 2, 1, 3, 2, 1, 2],
        "quantity": [1, 2, 1, 1, 3, 2, 1],
        "unit_price": [100.0] * 7,
        "subtotal": [100.0, 200.0, 100.0, 100.0, 300.0, 200.0, 100.0],
    })


def _productos():
    return pd.DataFrame({"id": [1, 2, 3], "sku": list("ABC"), "name": ["Cafe", "Pan", "Te"],
                         "category": ["x", "y", None], "unit_price": [100.0] * 3,
                         "unit_cost": [50.0, None, 10.0], "stock": 5, "is_active": True})


def test_imputar_y_calidad():
    it = _items()
    it.loc[0, "quantity"] = np.nan
    it.loc[2, "subtotal"] = np.nan
    items, prods, cal = t.imputar(it, _productos())
    assert len(items) == 6                       # quantity nula -> 0 -> descartada
    assert items["subtotal"].notna().all()
    assert prods["unit_cost"].tolist() == [50.0, 0.0, 10.0]
    assert prods["category"].tolist() == ["x", "y", "Sin categoría"]
    assert cal["nulos_imputados"] >= 3 and "fecha" in items


def test_matriz_canasta_binaria():
    items, prods, _ = t.imputar(_items(), _productos())
    mx = t.matriz_canasta(items, prods)
    assert mx.dtypes.eq(bool).all()
    assert mx.shape == (4, 3)
    assert set(mx.columns) == {"Cafe", "Pan", "Te"}
    assert mx.loc[1].to_dict() == {"Cafe": True, "Pan": True, "Te": False}
    assert mx.loc[3].to_dict() == {"Cafe": False, "Pan": True, "Te": False}


def test_matriz_canasta_ignora_cantidad_repetida():
    it = pd.concat([_items(), _items().iloc[[0]]], ignore_index=True)  # misma linea repetida
    items, prods, _ = t.imputar(it, _productos())
    assert t.matriz_canasta(items, prods).loc[1, "Cafe"] == True  # noqa: E712 (binaria, no conteo)


def test_panel_rellena_ceros_y_excluye_hoy():
    items, prods, _ = t.imputar(_items(), _productos())
    panel = t.construir_panel(items, prods, hoy=pd.Timestamp("2025-01-03"))
    assert panel["fecha"].max() == pd.Timestamp("2025-01-02")  # el dia en curso se excluye
    assert len(panel) == 2 * 3
    q = panel.set_index(["fecha", "product_id"])["qty"]
    assert q[(pd.Timestamp("2025-01-01"), 3)] == 0 and q[(pd.Timestamp("2025-01-01"), 2)] == 2


def test_rfm_a_mano():
    items, _, _ = t.imputar(_items(), _productos())
    rfm = t.tabla_rfm(items).set_index("customer_id")
    assert set(rfm.index) == {10, 11}                    # la venta sin cliente se ignora
    assert rfm.loc[10, "frequency"] == 2 and rfm.loc[10, "monetary"] == 600.0
    assert rfm.loc[10, "recency"] == 1 and rfm.loc[11, "recency"] == 2
    assert t.tabla_rfm(items.iloc[0:0]).empty


# ---- Apriori
def _canastas(n=200, seed=0):
    rng = np.random.default_rng(seed)
    a = rng.random(n) < 0.4
    b = np.where(a, rng.random(n) < 0.9, rng.random(n) < 0.1)  # B depende fuertemente de A
    c = rng.random(n) < 0.3
    return pd.DataFrame({"A": a, "B": b, "C": c})


def test_apriori_reglas_validas():
    r = basket_apriori.minar_reglas(_canastas(), 0.05, 0.3, 1.2)
    assert len(r) > 0
    assert (r["lift"] > 1.2).all()
    assert r[["support", "confidence"]].apply(lambda s: s.between(0, 1).all()).all()
    top = r.iloc[0]
    assert {top["antecedent"], top["consequent"]} == {"A", "B"}
    assert r["lift"].is_monotonic_decreasing


def test_apriori_umbral_alto_filtra_y_pocos_datos_vacio():
    assert basket_apriori.minar_reglas(_canastas(), 0.05, 0.3, min_lift=50).empty
    assert basket_apriori.minar_reglas(_canastas(5)).empty
    assert list(basket_apriori.minar_reglas(pd.DataFrame()).columns) == [
        "antecedent", "consequent", "support", "confidence", "lift"]


# ---- K-Means
def _rfm(n=60, seed=1):
    rng = np.random.default_rng(seed)
    grupos = []
    for rec, fre, mon in ((5, 30, 900000), (60, 3, 40000), (150, 1, 8000)):
        k = n // 3
        grupos.append(pd.DataFrame({
            "recency": np.maximum(1, rng.normal(rec, rec * 0.2, k)).astype(int),
            "frequency": np.maximum(1, rng.normal(fre, fre * 0.2 + 0.3, k)).astype(int),
            "monetary": np.abs(rng.normal(mon, mon * 0.15, k))}))
    df = pd.concat(grupos, ignore_index=True)
    df.insert(0, "customer_id", range(1, len(df) + 1))
    return df


def test_kmeans_silueta_k_y_etiquetas():
    out, met = rfm_kmeans.segmentar(_rfm())
    assert -1 <= met["silhouette"] <= 1 and 2 <= met["k"] <= 6
    assert met["silhouette"] > 0.3                       # grupos bien separados
    assert len(out) == 60 and out["segment_label"].notna().all()
    assert set(out["segment_label"]) <= {"Campeones", "Leales", "En riesgo", "Perdidos", "Nuevos", "Ocasionales"}
    assert out["cluster"].nunique() == met["k"] or out["cluster"].nunique() >= 2
    assert "Campeones" in set(out["segment_label"])


def test_kmeans_reproducible_y_pocos_clientes():
    a, _ = rfm_kmeans.segmentar(_rfm(), semilla=3)
    b, _ = rfm_kmeans.segmentar(_rfm(), semilla=3)
    assert a["cluster"].tolist() == b["cluster"].tolist()
    with pytest.raises(ValidacionError):
        rfm_kmeans.segmentar(_rfm(6).iloc[:5])


# ---- Demanda
def _feat_sintetico(dias=120, productos=3):
    rng = np.random.default_rng(0)
    partes = []
    for pid in range(1, productos + 1):
        fechas = pd.date_range("2025-01-01", periods=dias)
        qty = np.maximum(0, 5 + 3 * (fechas.dayofweek >= 4) + rng.normal(0, 1, dias)).round()
        partes.append(pd.DataFrame({"fecha": fechas, "product_id": pid, "qty": qty}))
    panel = pd.concat(partes, ignore_index=True)
    return panel, t.agregar_features(panel)


def test_demanda_metricas_y_pronostico():
    panel, feat = _feat_sintetico()
    modelo, met = demand_xgb.entrenar_evaluar(feat, test_dias=30, semilla=1)
    assert math.isfinite(met["mae"]) and met["mae"] >= 0 and math.isfinite(met["r2"])
    assert met["mae"] < met["mae_baseline_lag7"] * 1.5
    assert met["n_test"] > 0 and met["n_train"] > met["n_test"]
    pr = demand_xgb.pronosticar(modelo, panel, 30)
    assert len(pr) == 3 * 30 and (pr["predicted_qty"] >= 0).all()
    assert pr["paso"].between(1, 30).all()
    assert pr["forecast_date"].min() == (panel["fecha"].max() + pd.Timedelta(days=1)).date()


def test_demanda_split_temporal_sin_fuga():
    _, feat = _feat_sintetico()
    _, met = demand_xgb.entrenar_evaluar(feat, test_dias=30, semilla=1)
    corte = pd.Timestamp(met["corte_train"])
    assert corte == feat["fecha"].max() - pd.Timedelta(days=30)


def test_demanda_pocos_dias_rechaza():
    _, feat = _feat_sintetico(dias=40)
    with pytest.raises(ValidacionError):
        demand_xgb.entrenar_evaluar(feat)

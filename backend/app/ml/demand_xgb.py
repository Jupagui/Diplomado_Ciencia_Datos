"""Proyección de demanda con XGBoost (split temporal, pronóstico recursivo a 7 y 30 días)."""
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

from app.domain.errors import ValidacionError
from app.etl.transform import FEATURES, festivos_co

MIN_DIAS = 60


def _nuevo_modelo(semilla: int) -> XGBRegressor:
    return XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
                        colsample_bytree=0.8, objective="reg:squarederror", random_state=semilla, n_jobs=2)


def entrenar_evaluar(feat: pd.DataFrame, test_dias: int = 30, semilla: int = 42) -> tuple[XGBRegressor, dict]:
    """Entrena con el pasado y evalúa en los últimos `test_dias` (sin fuga temporal).

    Devuelve el modelo reentrenado con todo el histórico (para pronosticar) y las métricas del test.
    """
    datos = feat.dropna(subset=FEATURES)
    if datos["fecha"].nunique() < MIN_DIAS:
        raise ValidacionError(f"Se necesitan al menos {MIN_DIAS} días de historia para entrenar la demanda")
    corte = datos["fecha"].max() - pd.Timedelta(days=test_dias)
    train, test = datos[datos["fecha"] <= corte], datos[datos["fecha"] > corte]
    modelo = _nuevo_modelo(semilla).fit(train[FEATURES], train["qty"])
    pred = np.clip(modelo.predict(test[FEATURES]), 0, None)
    base = test["lag_7"].to_numpy()  # línea base ingenua: misma cantidad de hace una semana
    metricas = {
        "mae": float(mean_absolute_error(test["qty"], pred)),
        "r2": float(r2_score(test["qty"], pred)),
        "mae_baseline_lag7": float(mean_absolute_error(test["qty"], base)),
        "r2_baseline_lag7": float(r2_score(test["qty"], base)),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "corte_train": str(corte.date()),
    }
    final = _nuevo_modelo(semilla).fit(datos[FEATURES], datos["qty"])
    return final, metricas


def pronosticar(modelo: XGBRegressor, panel: pd.DataFrame, horizonte: int = 30) -> pd.DataFrame:
    """Pronóstico recursivo día a día para todos los productos. Cantidades siempre >= 0."""
    pivote = panel.pivot(index="fecha", columns="product_id", values="qty").sort_index()
    pids = list(pivote.columns)
    hist = {pid: pivote[pid].to_numpy(dtype=float).tolist() for pid in pids}
    ultima = pivote.index.max()
    fest = festivos_co([ultima.year, (ultima + pd.Timedelta(days=horizonte)).year])
    filas = []
    for paso in range(1, horizonte + 1):
        dia = ultima + pd.Timedelta(days=paso)
        X = pd.DataFrame({
            "product_id": pids,
            "lag_1": [hist[p][-1] for p in pids],
            "lag_7": [hist[p][-7] for p in pids],
            "lag_14": [hist[p][-14] for p in pids],
            "ma_7": [np.mean(hist[p][-7:]) for p in pids],
            "ma_28": [np.mean(hist[p][-28:]) for p in pids],
            "dow": dia.day_of_week, "month": dia.month, "is_holiday": int(dia.date() in fest),
        })[FEATURES]
        pred = np.clip(modelo.predict(X), 0, None)
        for pid, q in zip(pids, pred):
            hist[pid].append(float(q))
            filas.append({"product_id": int(pid), "forecast_date": dia.date(), "paso": paso,
                          "predicted_qty": round(float(q), 3)})
    return pd.DataFrame(filas)

"""Segmentación RFM con K-Means (k de 2 a 6 por coeficiente de silueta)."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from app.domain.errors import ValidacionError


def _etiquetar(rfm: pd.DataFrame) -> dict[int, str]:
    """Etiquetas legibles a partir de las medias de cada cluster frente a los cuantiles globales."""
    medias = rfm.groupby("cluster")[["recency", "frequency", "monetary"]].mean()
    q40, q60 = rfm[["recency", "frequency", "monetary"]].quantile(0.4), rfm[["recency", "frequency", "monetary"]].quantile(0.6)
    etiquetas: dict[int, str] = {}
    for c, fila in medias.iterrows():
        r_bueno, r_malo = fila.recency <= q40.recency, fila.recency > q60.recency
        f_alta, f_baja = fila.frequency >= q60.frequency, fila.frequency <= q40.frequency
        m_alto = fila.monetary >= q60.monetary
        if not r_malo and f_alta and m_alto:
            etiquetas[c] = "Campeones"
        elif r_malo and f_baja:
            etiquetas[c] = "Perdidos"
        elif r_malo:
            etiquetas[c] = "En riesgo"
        elif r_bueno and f_baja:
            etiquetas[c] = "Nuevos"
        elif f_alta or m_alto:
            etiquetas[c] = "Leales"
        else:
            etiquetas[c] = "Ocasionales"
    return etiquetas


def segmentar(rfm: pd.DataFrame, k_min: int = 2, k_max: int = 6, semilla: int = 42) -> tuple[pd.DataFrame, dict]:
    """Devuelve el RFM con `cluster` y `segment_label`, y métricas (k, silueta, silueta por k)."""
    if len(rfm) < k_max + 2:
        raise ValidacionError("No hay suficientes clientes identificados para segmentar")
    X = np.column_stack([np.log1p(rfm["recency"]), np.log1p(rfm["frequency"]), np.log1p(rfm["monetary"])])
    Xs = StandardScaler().fit_transform(X)
    mejor, mejor_s, siluetas = None, -2.0, {}
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=semilla).fit(Xs)
        if len(set(km.labels_)) < 2:
            continue
        s = float(silhouette_score(Xs, km.labels_))
        siluetas[k] = round(s, 4)
        if s > mejor_s:
            mejor, mejor_s = km, s
    out = rfm.copy()
    out["cluster"] = mejor.labels_.astype(int)
    out["segment_label"] = out["cluster"].map(_etiquetar(out))
    metricas = {"k": int(mejor.n_clusters), "silhouette": float(mejor_s), "silhouette_por_k": siluetas,
                "n_clientes": int(len(out))}
    return out, metricas

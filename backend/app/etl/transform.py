"""Transformación con Pandas/NumPy: imputación, panel diario con lags, canasta binaria y RFM."""
import holidays
import numpy as np
import pandas as pd

FEATURES = ["product_id", "lag_1", "lag_7", "lag_14", "ma_7", "ma_28", "dow", "month", "is_holiday"]


def festivos_co(anios) -> holidays.HolidayBase:
    return holidays.Colombia(years=sorted({int(a) for a in anios}))


def imputar(items: pd.DataFrame, productos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Imputa nulos y normaliza tipos. Devuelve (items, productos, resumen de calidad)."""
    items = items.copy()
    productos = productos.copy()
    nulos = int(items[["quantity", "unit_price", "subtotal"]].isna().sum().sum()
                + productos[["unit_cost", "category"]].isna().sum().sum())
    productos["unit_cost"] = productos["unit_cost"].fillna(0.0).astype(float)
    productos["category"] = productos["category"].fillna("Sin categoría")
    items = items.dropna(subset=["sale_id", "product_id", "created_at"])
    items["quantity"] = items["quantity"].fillna(0).astype(float)
    items = items[items["quantity"] > 0].copy()
    items["unit_price"] = items["unit_price"].astype(float).fillna(
        items["product_id"].map(productos.set_index("id")["unit_price"].astype(float)))
    items["subtotal"] = items["subtotal"].astype(float).fillna(items["quantity"] * items["unit_price"])
    items["created_at"] = pd.to_datetime(items["created_at"])
    items["fecha"] = items["created_at"].dt.normalize()
    return items, productos, {"nulos_imputados": nulos, "lineas": int(len(items))}


def construir_panel(items: pd.DataFrame, productos: pd.DataFrame, hoy: pd.Timestamp | None = None) -> pd.DataFrame:
    """Serie diaria completa (fecha x producto) con ceros donde no hubo ventas.

    Se excluye el día en curso por estar incompleto.
    """
    hoy = (hoy or pd.Timestamp.now()).normalize()
    items = items[items["fecha"] < hoy]
    if items.empty:
        return pd.DataFrame(columns=["fecha", "product_id", "qty"])
    diario = items.groupby(["fecha", "product_id"])["quantity"].sum()
    fechas = pd.date_range(items["fecha"].min(), items["fecha"].max(), freq="D")
    idx = pd.MultiIndex.from_product([fechas, sorted(productos["id"].tolist())], names=["fecha", "product_id"])
    panel = diario.reindex(idx, fill_value=0.0).rename("qty").reset_index()
    return panel.sort_values(["product_id", "fecha"]).reset_index(drop=True)


def agregar_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Lags (1, 7, 14), medias móviles (7, 28) sin fuga (desplazadas un día), calendario y festivos CO."""
    p = panel.copy()
    g = p.groupby("product_id")["qty"]
    for k in (1, 7, 14):
        p[f"lag_{k}"] = g.shift(k)
    for w in (7, 28):
        p[f"ma_{w}"] = g.transform(lambda s, w=w: s.shift(1).rolling(w).mean())
    p["dow"] = p["fecha"].dt.day_of_week
    p["month"] = p["fecha"].dt.month
    fest = festivos_co(p["fecha"].dt.year.unique())
    p["is_holiday"] = p["fecha"].dt.date.map(lambda d: d in fest).astype(int)
    return p


def matriz_canasta(items: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    """Matriz binaria venta x producto (columnas = nombre del producto)."""
    nombres = productos.set_index("id")["name"]
    df = items[["sale_id", "product_id"]].drop_duplicates().copy()
    df["producto"] = df["product_id"].map(nombres)
    df["v"] = True
    m = df.set_index(["sale_id", "producto"])["v"].unstack(fill_value=False)
    return m.fillna(False).astype(bool)


def tabla_rfm(items: pd.DataFrame) -> pd.DataFrame:
    """Recencia (días), frecuencia (nº ventas) y valor monetario por cliente identificado."""
    df = items.dropna(subset=["customer_id"]).copy()
    if df.empty:
        return pd.DataFrame(columns=["customer_id", "recency", "frequency", "monetary"])
    ref = items["fecha"].max() + pd.Timedelta(days=1)
    g = df.groupby("customer_id")
    rfm = pd.DataFrame({
        "recency": (ref - g["fecha"].max()).dt.days,
        "frequency": g["sale_id"].nunique(),
        "monetary": g["subtotal"].sum(),
    }).reset_index()
    rfm["customer_id"] = rfm["customer_id"].astype(int)
    rfm["monetary"] = rfm["monetary"].astype(float)
    return rfm


def log_monetario(x: pd.Series) -> pd.Series:
    return pd.Series(np.log1p(x.astype(float)), index=x.index)

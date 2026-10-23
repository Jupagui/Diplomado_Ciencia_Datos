"""Venta cruzada: reglas de asociación con Apriori (mlxtend)."""
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


def _texto(conjunto) -> str:
    return " + ".join(sorted(conjunto))


def minar_reglas(matriz: pd.DataFrame, min_support: float = 0.02, min_confidence: float = 0.3,
                 min_lift: float = 1.2, max_len: int = 3, max_reglas: int = 200) -> pd.DataFrame:
    """Devuelve reglas (antecedent, consequent, support, confidence, lift) con lift > min_lift."""
    columnas = ["antecedent", "consequent", "support", "confidence", "lift"]
    if matriz.empty or len(matriz) < 10:
        return pd.DataFrame(columns=columnas)
    frecuentes = apriori(matriz, min_support=min_support, use_colnames=True, max_len=max_len)
    if frecuentes.empty or (frecuentes["itemsets"].map(len) < 2).all():
        return pd.DataFrame(columns=columnas)
    reglas = association_rules(frecuentes, num_itemsets=len(matriz), metric="confidence",
                               min_threshold=min_confidence)
    reglas = reglas[reglas["lift"] > min_lift]
    if reglas.empty:
        return pd.DataFrame(columns=columnas)
    out = pd.DataFrame({
        "antecedent": reglas["antecedents"].map(_texto),
        "consequent": reglas["consequents"].map(_texto),
        "support": reglas["support"].astype(float),
        "confidence": reglas["confidence"].astype(float),
        "lift": reglas["lift"].astype(float),
    })
    return out.sort_values(["lift", "confidence"], ascending=False).head(max_reglas).reset_index(drop=True)

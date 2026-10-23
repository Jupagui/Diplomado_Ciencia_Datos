"""Extracción: incremental por watermark (etl_runs) y descifrado de PII solo en memoria."""
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from app.domain.ports import CipherPort, EtlSourcePort


@dataclass
class DatosExtraidos:
    items: pd.DataFrame      # una fila por línea de venta
    productos: pd.DataFrame
    clientes: pd.DataFrame   # incluye email/phone descifrados (solo en memoria)
    ventas_nuevas: int       # ventas posteriores al watermark previo
    watermark_previo: datetime | None


def extraer(source: EtlSourcePort, cipher: CipherPort, watermark_previo: datetime | None) -> DatosExtraidos:
    """Cuenta lo nuevo desde el watermark y carga el histórico completo.

    El histórico completo es necesario para calcular lags, ventanas móviles y matrices de canasta;
    el watermark decide si hay trabajo nuevo y cuántas ventas son incrementales.
    """
    nuevas = source.contar_ventas_desde(watermark_previo)
    items = pd.DataFrame(source.items_ventas(), columns=[
        "sale_id", "created_at", "customer_id", "product_id", "quantity", "unit_price", "subtotal"])
    productos = pd.DataFrame(source.productos(), columns=[
        "id", "sku", "name", "category", "unit_price", "unit_cost", "stock", "is_active"])
    clientes = pd.DataFrame(source.clientes(), columns=[
        "id", "first_name", "last_name", "encrypted_email", "encrypted_phone", "created_at"])
    # La PII se descifra en memoria (nunca se persiste en claro)
    clientes["email"] = clientes["encrypted_email"].map(cipher.descifrar)
    clientes["phone"] = clientes["encrypted_phone"].map(cipher.descifrar)
    clientes = clientes.drop(columns=["encrypted_email", "encrypted_phone"])
    return DatosExtraidos(items, productos, clientes, nuevas, watermark_previo)

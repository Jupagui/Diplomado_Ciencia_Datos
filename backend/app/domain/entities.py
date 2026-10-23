"""Entidades del dominio como dataclasses puras."""
from dataclasses import dataclass, field
from datetime import datetime

MEDIOS_PAGO = ("EFECTIVO", "TARJETA", "NEQUI", "TRANSFERENCIA")
TIPOS_MOVIMIENTO = ("IN", "OUT", "MERMA")


@dataclass
class Producto:
    sku: str
    name: str
    unit_price: float
    category: str | None = None
    unit_cost: float = 0.0
    stock: int = 0
    is_active: bool = True
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class Cliente:
    first_name: str
    last_name: str
    encrypted_email: str | None = None
    encrypted_phone: str | None = None
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class ItemVenta:
    product_id: int
    quantity: int
    unit_price: float
    subtotal: float
    id: int | None = None
    sale_id: int | None = None
    product_name: str | None = None


@dataclass
class Venta:
    payment_method: str
    total_amount: float = 0.0
    customer_id: int | None = None
    status: str = "COMPLETED"
    items: list[ItemVenta] = field(default_factory=list)
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class MovimientoInventario:
    product_id: int
    movement_type: str
    quantity: int
    reason: str | None = None
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class Usuario:
    username: str
    password_hash: str
    is_admin: bool = True
    id: int | None = None

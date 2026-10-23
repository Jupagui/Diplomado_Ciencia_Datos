from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemVentaIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class VentaIn(BaseModel):
    items: list[ItemVentaIn] = Field(min_length=1)
    payment_method: str
    customer_id: int | None = None


class ItemVentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int | None
    product_id: int
    product_name: str | None
    quantity: int
    unit_price: float
    subtotal: float


class VentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int | None
    total_amount: float
    payment_method: str
    status: str
    created_at: datetime | None
    items: list[ItemVentaOut]

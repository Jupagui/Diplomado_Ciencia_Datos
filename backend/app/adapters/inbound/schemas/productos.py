from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductoIn(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    unit_price: float = Field(gt=0)
    unit_cost: float = Field(default=0, ge=0)
    stock: int = Field(default=0, ge=0)


class ProductoUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    unit_price: float | None = Field(default=None, gt=0)
    unit_cost: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    category: str | None
    unit_price: float
    unit_cost: float
    stock: int
    is_active: bool
    created_at: datetime | None

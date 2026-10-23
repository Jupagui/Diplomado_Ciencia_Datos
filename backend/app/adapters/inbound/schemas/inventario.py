from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MovimientoIn(BaseModel):
    product_id: int
    movement_type: str = Field(description="IN, OUT o MERMA")
    quantity: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=255)


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    movement_type: str
    quantity: int
    reason: str | None
    created_at: datetime | None

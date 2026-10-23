from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClienteIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=30)


class ClienteUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=30)


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    revelado: bool
    created_at: datetime | None

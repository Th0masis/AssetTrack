from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = None
    description: str | None = None
    serial_number: str | None = None
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    photo_url: str | None = None
    responsible_person: str | None = None
    is_active: bool = True


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    category: str | None = None
    description: str | None = None
    serial_number: str | None = None
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    photo_url: str | None = None
    responsible_person: str | None = None


class ItemResponse(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

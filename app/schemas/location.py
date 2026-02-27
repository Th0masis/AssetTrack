from datetime import datetime
from pydantic import BaseModel, Field


class LocationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=32)
    building: str | None = None
    floor: str | None = None
    description: str | None = None
    is_active: bool = True


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    building: str | None = None
    floor: str | None = None
    description: str | None = None


class LocationResponse(LocationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

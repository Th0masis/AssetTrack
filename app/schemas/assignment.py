from datetime import datetime
from pydantic import BaseModel


class MoveRequest(BaseModel):
    item_id: int
    location_id: int
    note: str | None = None


class AssignmentResponse(BaseModel):
    id: int
    item_id: int
    location_id: int
    user_id: int | None
    note: str | None
    assigned_at: datetime

    model_config = {"from_attributes": True}

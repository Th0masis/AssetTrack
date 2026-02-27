from datetime import datetime
from pydantic import BaseModel


class AuditCreate(BaseModel):
    name: str


class AuditScanRequest(BaseModel):
    item_id: int | None = None
    item_code: str | None = None
    location_id: int | None = None


class AuditScanResponse(BaseModel):
    id: int
    audit_id: int
    item_id: int
    location_id: int | None
    scanned_by: int | None
    scanned_at: datetime

    model_config = {"from_attributes": True}


class AuditResponse(BaseModel):
    id: int
    name: str
    status: str
    started_at: datetime
    closed_at: datetime | None
    created_by: int

    model_config = {"from_attributes": True}

from datetime import datetime
from pydantic import BaseModel, Field
from app.models.disposal import DisposalReason


class DisposalRequest(BaseModel):
    reason: DisposalReason
    disposed_at: datetime | None = None  # defaults to now() in service
    note: str | None = None
    document_ref: str | None = None


class BulkDisposeRequest(BaseModel):
    item_ids: list[int] = Field(..., min_length=1)
    reason: DisposalReason
    disposed_at: datetime | None = None
    note: str | None = None
    document_ref: str | None = None


class DisposalResponse(BaseModel):
    id: int
    item_id: int
    reason: DisposalReason
    disposed_at: datetime
    disposed_by: int | None
    note: str | None
    document_ref: str | None
    # Denormalized item fields — eliminuje nutnost druhého dotazu v list view
    item_code: str | None = None
    item_name: str | None = None

    model_config = {"from_attributes": True}


class BulkDisposeResponse(BaseModel):
    disposed: list[DisposalResponse]
    skipped_ids: list[int]  # již vyřazené nebo neexistující

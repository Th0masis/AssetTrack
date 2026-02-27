from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.disposal import DisposalResponse
from app.schemas.pagination import Page
from app.routers.auth_ui import require_session_user
import app.services.disposal_service as svc

router = APIRouter(prefix="/api/disposals", tags=["disposals"])


@router.get("", response_model=Page[DisposalResponse])
def list_disposals(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    year: int | None = Query(None, description="Filtrovat dle roku vyřazení"),
    reason: str | None = Query(None, description="Filtrovat dle důvodu (liquidation, sale, ...)"),
    db: Session = Depends(get_db),
    _=Depends(require_session_user),
):
    return svc.get_disposals(db, page=page, size=size, year=year, reason=reason)

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.schemas.assignment import AssignmentResponse
from app.schemas.disposal import DisposalRequest, DisposalResponse, BulkDisposeRequest, BulkDisposeResponse
from app.schemas.pagination import Page
from fastapi import HTTPException
from app.routers.auth_ui import require_session_manager
import app.services.item_service as svc
import app.services.disposal_service as disposal_svc

router = APIRouter(prefix="/api/items", tags=["items"])


@router.get("", response_model=Page[ItemResponse])
def list_items(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    search: str = Query(""),
    db: Session = Depends(get_db),
):
    return svc.get_items(db, page=page, size=size, search=search)


@router.post("", response_model=ItemResponse, status_code=201)
def create_item(data: ItemCreate, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return svc.create_item(db, data)


@router.get("/by-code/{code}", response_model=ItemResponse)
def get_item_by_code(code: str, db: Session = Depends(get_db)):
    item = svc.get_item_by_code(db, code)
    if not item:
        raise HTTPException(status_code=404, detail="Položka nenalezena")
    return item


@router.post("/bulk-dispose", response_model=BulkDisposeResponse, status_code=200)
def bulk_dispose(data: BulkDisposeRequest, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return disposal_svc.bulk_dispose_items(db, data)


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return svc.get_item(db, item_id)


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return svc.update_item(db, item_id, data)


@router.delete("/{item_id}", response_model=ItemResponse)
def delete_item(item_id: int, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return svc.delete_item(db, item_id)


@router.get("/{item_id}/history", response_model=list[AssignmentResponse])
def item_history(item_id: int, db: Session = Depends(get_db)):
    return svc.get_item_history(db, item_id)


@router.post("/{item_id}/dispose", response_model=DisposalResponse, status_code=201)
def dispose_item(item_id: int, data: DisposalRequest, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return disposal_svc.dispose_item(db, item_id, data)

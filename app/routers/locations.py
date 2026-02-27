from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.schemas.item import ItemResponse
from app.schemas.pagination import Page
from app.routers.auth_ui import require_session_manager
import app.services.location_service as svc

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=Page[LocationResponse])
def list_locations(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return svc.get_locations(db, page=page, size=size)


@router.post("", response_model=LocationResponse, status_code=201)
def create_location(data: LocationCreate, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return svc.create_location(db, data)


@router.get("/{loc_id}", response_model=LocationResponse)
def get_location(loc_id: int, db: Session = Depends(get_db)):
    return svc.get_location(db, loc_id)


@router.put("/{loc_id}", response_model=LocationResponse)
def update_location(loc_id: int, data: LocationUpdate, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return svc.update_location(db, loc_id, data)


@router.delete("/{loc_id}", response_model=LocationResponse)
def delete_location(loc_id: int, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return svc.delete_location(db, loc_id)


@router.get("/{loc_id}/items", response_model=list[ItemResponse])
def items_at_location(loc_id: int, db: Session = Depends(get_db)):
    return svc.get_items_at_location(db, loc_id)

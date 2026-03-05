from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.assignment import MoveRequest, AssignmentResponse, BulkMoveRequest, BulkMoveResponse
from app.routers.auth_ui import require_session_manager
import app.services.move_service as svc

router = APIRouter(prefix="/api/moves", tags=["moves"])


@router.post("", response_model=AssignmentResponse, status_code=201)
def move_item(data: MoveRequest, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return svc.move_item(db, data)


@router.post("/bulk", response_model=BulkMoveResponse, status_code=200)
def bulk_move(data: BulkMoveRequest, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    count = svc.bulk_move_items(db, data.from_location_id, data.to_location_id, data.note)
    return BulkMoveResponse(moved=count)


@router.post("/assign-unlocated/{loc_id}", response_model=BulkMoveResponse, status_code=200)
def assign_unlocated(loc_id: int, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    count = svc.assign_unlocated_items(db, loc_id)
    return BulkMoveResponse(moved=count)

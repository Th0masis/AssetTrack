from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.assignment import MoveRequest, AssignmentResponse
from app.routers.auth_ui import require_session_manager
import app.services.move_service as svc

router = APIRouter(prefix="/api/moves", tags=["moves"])


@router.post("", response_model=AssignmentResponse, status_code=201)
def move_item(data: MoveRequest, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    return svc.move_item(db, data)

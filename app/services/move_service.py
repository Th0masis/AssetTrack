from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.assignment import Assignment
from app.models.item import Item
from app.models.location import Location
from app.schemas.assignment import MoveRequest


def move_item(db: Session, data: MoveRequest, user_id: int | None = None) -> Assignment:
    item = db.get(Item, data.item_id)
    if not item or not item.is_active:
        raise HTTPException(status_code=404, detail="Položka nenalezena")

    loc = db.get(Location, data.location_id)
    if not loc or not loc.is_active:
        raise HTTPException(status_code=404, detail="Lokace nenalezena")

    assignment = Assignment(
        item_id=data.item_id,
        location_id=data.location_id,
        user_id=user_id,
        note=data.note,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

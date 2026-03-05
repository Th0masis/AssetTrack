from sqlalchemy.orm import Session
from sqlalchemy import select, func, exists
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


def bulk_move_items(db: Session, from_loc_id: int, to_loc_id: int, note: str | None = None) -> int:
    """Přesune všechny položky z from_loc_id do to_loc_id (nové záznamy v assignments)."""
    to_loc = db.get(Location, to_loc_id)
    if not to_loc or not to_loc.is_active:
        raise HTTPException(status_code=404, detail="Cílová lokace nenalezena nebo není aktivní")

    # Najde položky, jejichž POSLEDNÍ přiřazení je na from_loc_id (i neaktivní lokace)
    subq = (
        select(Assignment.item_id, func.max(Assignment.assigned_at).label("max_at"))
        .group_by(Assignment.item_id)
        .subquery()
    )
    item_ids = db.scalars(
        select(Assignment.item_id)
        .join(subq, (Assignment.item_id == subq.c.item_id) &
              (Assignment.assigned_at == subq.c.max_at))
        .where(Assignment.location_id == from_loc_id)
    ).all()

    count = 0
    for item_id in item_ids:
        item = db.get(Item, item_id)
        if item and item.is_active:
            db.add(Assignment(item_id=item_id, location_id=to_loc_id, note=note))
            count += 1

    if count > 0:
        db.commit()
    return count


def assign_unlocated_items(db: Session, to_loc_id: int, note: str | None = None) -> int:
    """Přiřadí sem všechny aktivní položky bez viditelné lokace.

    Pokrývá dva případy:
    1. Položka nemá žádný záznam v assignments.
    2. Poslední assignment ukazuje na neaktivní nebo chybějící lokaci.
    """
    to_loc = db.get(Location, to_loc_id)
    if not to_loc or not to_loc.is_active:
        raise HTTPException(status_code=404, detail="Cílová lokace nenalezena nebo není aktivní")

    # Případ 1 — žádný assignment
    assigned_subq = select(Assignment.item_id).distinct().subquery()
    no_assign_ids = set(db.scalars(
        select(Item.id)
        .where(Item.is_active == True)
        .where(~Item.id.in_(select(assigned_subq.c.item_id)))
    ).all())

    # Případ 2 — poslední assignment → neaktivní/chybějící lokace
    subq = (
        select(Assignment.item_id, func.max(Assignment.assigned_at).label("max_at"))
        .group_by(Assignment.item_id)
        .subquery()
    )
    latest = db.execute(
        select(Assignment.item_id, Assignment.location_id)
        .join(subq, (Assignment.item_id == subq.c.item_id) &
              (Assignment.assigned_at == subq.c.max_at))
    ).all()

    orphan_ids = set()
    for item_id, loc_id in latest:
        loc = db.get(Location, loc_id)
        if loc is None or not loc.is_active:
            item = db.get(Item, item_id)
            if item and item.is_active:
                orphan_ids.add(item_id)

    all_ids = no_assign_ids | orphan_ids
    count = 0
    for item_id in all_ids:
        db.add(Assignment(item_id=item_id, location_id=to_loc_id, note=note))
        count += 1

    if count > 0:
        db.commit()
    return count

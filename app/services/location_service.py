from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.location import Location
from app.models.assignment import Assignment
from app.models.item import Item
from app.schemas.location import LocationCreate, LocationUpdate
from app.schemas.pagination import Page
import math


def get_locations(db: Session, page: int = 1, size: int = 50) -> Page:
    query = select(Location).where(Location.is_active == True)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    locs = db.scalars(query.offset((page - 1) * size).limit(size)).all()
    return Page(items=locs, total=total, page=page, pages=math.ceil(total / size) if total else 1, size=size)


def get_location(db: Session, loc_id: int) -> Location:
    loc = db.get(Location, loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Lokace nenalezena")
    return loc


def create_location(db: Session, data: LocationCreate) -> Location:
    existing = db.scalar(select(Location).where(Location.code == data.code))
    if existing:
        raise HTTPException(status_code=409, detail="Kód lokace již existuje")
    loc = Location(**data.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def update_location(db: Session, loc_id: int, data: LocationUpdate) -> Location:
    loc = get_location(db, loc_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(loc, field, value)
    db.commit()
    db.refresh(loc)
    return loc


def delete_location(db: Session, loc_id: int) -> Location:
    loc = get_location(db, loc_id)
    loc.is_active = False
    db.commit()
    db.refresh(loc)
    return loc


def get_items_at_location(db: Session, loc_id: int) -> list[Item]:
    get_location(db, loc_id)
    # Get latest assignment per item, filter by this location
    subquery = (
        select(Assignment.item_id, func.max(Assignment.assigned_at).label("max_at"))
        .group_by(Assignment.item_id)
        .subquery()
    )
    item_ids = db.scalars(
        select(Assignment.item_id)
        .join(subquery, (Assignment.item_id == subquery.c.item_id) &
              (Assignment.assigned_at == subquery.c.max_at))
        .where(Assignment.location_id == loc_id)
    ).all()
    if not item_ids:
        return []
    return db.scalars(
        select(Item).where(Item.id.in_(item_ids), Item.is_active == True)
    ).all()

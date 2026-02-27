from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.item import Item
from app.models.assignment import Assignment
from app.schemas.item import ItemCreate, ItemUpdate
from app.schemas.pagination import Page
import math


def get_items(db: Session, page: int = 1, size: int = 50, search: str = "", category: str = "") -> Page:
    query = select(Item).where(Item.is_active == True)
    if search:
        query = query.where(
            Item.name.ilike(f"%{search}%")
            | Item.code.ilike(f"%{search}%")
            | Item.serial_number.ilike(f"%{search}%")
        )
    if category:
        query = query.where(Item.category == category)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.offset((page - 1) * size).limit(size)).all()
    return Page(
        items=items,
        total=total,
        page=page,
        pages=math.ceil(total / size) if total else 1,
        size=size,
    )


def get_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Položka nenalezena", )
    return item


def get_item_by_code(db: Session, code: str) -> Item | None:
    return db.scalar(select(Item).where(Item.code == code))


def create_item(db: Session, data: ItemCreate) -> Item:
    existing = get_item_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=409, detail="Kód položky již existuje")
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item_id: int, data: ItemUpdate) -> Item:
    item = get_item(db, item_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: int) -> Item:
    item = get_item(db, item_id)
    item.is_active = False
    db.commit()
    db.refresh(item)
    return item


def get_item_history(db: Session, item_id: int) -> list[Assignment]:
    get_item(db, item_id)
    return db.scalars(
        select(Assignment)
        .where(Assignment.item_id == item_id)
        .order_by(Assignment.assigned_at)
    ).all()


def get_current_location(db: Session, item_id: int) -> Assignment | None:
    return db.scalar(
        select(Assignment)
        .where(Assignment.item_id == item_id)
        .order_by(Assignment.assigned_at.desc())
        .limit(1)
    )

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, extract
from fastapi import HTTPException
import math

from app.models.disposal import Disposal
from app.models.item import Item
from app.schemas.disposal import DisposalRequest, BulkDisposeRequest
from app.schemas.pagination import Page


def dispose_item(
    db: Session,
    item_id: int,
    data: DisposalRequest,
    user_id: int | None = None,
) -> Disposal:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Položka nenalezena")
    if not item.is_active:
        raise HTTPException(status_code=409, detail="Položka je již vyřazena")

    item.is_active = False

    disposal = Disposal(
        item_id=item_id,
        reason=data.reason,
        disposed_at=data.disposed_at or datetime.now(timezone.utc),
        disposed_by=user_id,
        note=data.note,
        document_ref=data.document_ref,
    )
    db.add(disposal)
    db.commit()
    db.refresh(disposal)
    return disposal


def get_disposals(
    db: Session,
    page: int = 1,
    size: int = 50,
    year: int | None = None,
    reason: str | None = None,
) -> Page:
    query = select(Disposal)

    if year is not None:
        query = query.where(extract("year", Disposal.disposed_at) == year)
    if reason is not None:
        query = query.where(Disposal.reason == reason)

    query = query.order_by(Disposal.disposed_at.desc())

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.offset((page - 1) * size).limit(size)).all()

    # Obohacení o denormalizované položkové údaje
    results = []
    for d in rows:
        item = db.get(Item, d.item_id)
        obj = _to_response_dict(d, item)
        results.append(obj)

    return Page(
        items=results,
        total=total,
        page=page,
        pages=math.ceil(total / size) if total else 1,
        size=size,
    )


def get_disposal(db: Session, disposal_id: int) -> Disposal:
    disposal = db.get(Disposal, disposal_id)
    if not disposal:
        raise HTTPException(status_code=404, detail="Záznam o vyřazení nenalezen")
    return disposal


def bulk_dispose_items(
    db: Session,
    data: BulkDisposeRequest,
    user_id: int | None = None,
) -> dict:
    """Hromadné vyřazení. Již vyřazené nebo neexistující položky jsou přeskočeny."""
    disposed = []
    skipped_ids = []
    disposed_at = data.disposed_at or datetime.now(timezone.utc)

    for item_id in data.item_ids:
        item = db.get(Item, item_id)
        if not item or not item.is_active:
            skipped_ids.append(item_id)
            continue

        item.is_active = False
        disposal = Disposal(
            item_id=item_id,
            reason=data.reason,
            disposed_at=disposed_at,
            disposed_by=user_id,
            note=data.note,
            document_ref=data.document_ref,
        )
        db.add(disposal)
        db.flush()
        disposed.append(disposal)

    db.commit()
    for d in disposed:
        db.refresh(d)

    return {
        "disposed": [_to_response_dict(d, db.get(Item, d.item_id)) for d in disposed],
        "skipped_ids": skipped_ids,
    }


def _to_response_dict(disposal: Disposal, item: Item | None) -> dict:
    return {
        "id": disposal.id,
        "item_id": disposal.item_id,
        "reason": disposal.reason,
        "disposed_at": disposal.disposed_at,
        "disposed_by": disposal.disposed_by,
        "note": disposal.note,
        "document_ref": disposal.document_ref,
        "item_code": item.code if item else None,
        "item_name": item.name if item else None,
    }

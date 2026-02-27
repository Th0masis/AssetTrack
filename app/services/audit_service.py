from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from app.models.audit import Audit, AuditScan
from app.models.item import Item
from app.models.location import Location
from app.models.assignment import Assignment
from app.schemas.audit import AuditCreate, AuditScanRequest
from app.schemas.pagination import Page
import math


def create_audit(db: Session, data: AuditCreate, user_id: int) -> Audit:
    audit = Audit(name=data.name, created_by=user_id)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def get_audits(db: Session, page: int = 1, size: int = 50) -> Page:
    from sqlalchemy import func
    query = select(Audit)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    audits = db.scalars(query.offset((page - 1) * size).limit(size)).all()
    return Page(items=audits, total=total, page=page, pages=math.ceil(total / size) if total else 1, size=size)


def get_audit(db: Session, audit_id: int) -> Audit:
    audit = db.get(Audit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Inventura nenalezena")
    return audit


def scan_item(db: Session, audit_id: int, data: AuditScanRequest, user_id: int | None = None) -> AuditScan:
    audit = get_audit(db, audit_id)
    if audit.status != "open":
        raise HTTPException(status_code=400, detail="Inventura je uzavřena")

    # Resolve item by item_id or item_code
    if data.item_id:
        item = db.get(Item, data.item_id)
    elif data.item_code:
        item = db.scalar(select(Item).where(Item.code == data.item_code))
    else:
        raise HTTPException(status_code=400, detail="Zadejte item_id nebo item_code")

    if not item or not item.is_active:
        raise HTTPException(status_code=404, detail="Položka nenalezena")

    # Idempotent: if already scanned, return existing
    existing = db.scalar(
        select(AuditScan)
        .where(AuditScan.audit_id == audit_id, AuditScan.item_id == item.id)
    )
    if existing:
        return existing

    # Get current location from latest assignment
    latest_assignment = db.scalar(
        select(Assignment)
        .where(Assignment.item_id == item.id)
        .order_by(Assignment.assigned_at.desc())
        .limit(1)
    )
    current_location_id = latest_assignment.location_id if latest_assignment else None

    # Use scanned location if provided, otherwise fall back to current
    scan_location_id = data.location_id if data.location_id else current_location_id

    # Auto-move: item found at different location than recorded → create assignment
    if data.location_id and current_location_id != data.location_id:
        db.add(Assignment(
            item_id=item.id,
            location_id=data.location_id,
            user_id=user_id,
            note=f"Automatický přesun při inventuře #{audit_id}",
        ))

    scan = AuditScan(
        audit_id=audit_id,
        item_id=item.id,
        location_id=scan_location_id,
        scanned_by=user_id,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def close_audit(db: Session, audit_id: int, user_id: int | None = None) -> Audit:
    audit = get_audit(db, audit_id)
    if audit.status == "closed":
        raise HTTPException(status_code=400, detail="Inventura je již uzavřena")
    audit.status = "closed"
    audit.closed_at = datetime.now(timezone.utc)
    audit.closed_by = user_id
    db.commit()
    db.refresh(audit)
    return audit


def get_audit_report(db: Session, audit_id: int) -> dict:
    audit = get_audit(db, audit_id)
    scans = db.scalars(select(AuditScan).where(AuditScan.audit_id == audit_id)).all()
    all_items = db.scalars(select(Item).where(Item.is_active == True)).all()
    scanned_ids = {s.item_id for s in scans}
    missing = [i for i in all_items if i.id not in scanned_ids]

    # Detekce přesunů: porovnáme lokaci skenu s posledním přiřazením PŘED zahájením
    # inventury. Pokud se liší, položka byla během inventury přesunuta. Automatický
    # přesun (Assignment) byl již vytvořen v scan_item() při skenu.
    scan_details = []
    for scan in scans:
        pre_assignment = db.scalar(
            select(Assignment)
            .where(
                Assignment.item_id == scan.item_id,
                Assignment.assigned_at < audit.started_at,
            )
            .order_by(Assignment.assigned_at.desc())
            .limit(1)
        )
        was_moved = (
            pre_assignment is not None
            and scan.location_id is not None
            and pre_assignment.location_id != scan.location_id
        )
        from_loc = db.get(Location, pre_assignment.location_id) if was_moved else None
        scan_details.append({
            "scan": scan,
            "was_moved": was_moved,
            "from_location_name": from_loc.name if from_loc else None,
        })

    moved_count = sum(1 for d in scan_details if d["was_moved"])
    return {
        "audit": audit,
        "scanned_count": len(scans),
        "total_items": len(all_items),
        "missing_count": len(missing),
        "moved_count": moved_count,
        "missing_items": missing,
        "scans": scans,
        "scan_details": scan_details,
    }

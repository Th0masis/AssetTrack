from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models.item import Item
from app.models.location import Location
from app.models.audit import Audit, AuditScan
from app.models.assignment import Assignment
from app.config import settings
from app.routers.auth_ui import require_user, require_session_user

router = APIRouter(tags=["scan"])


@router.get("/scan/{code}")
def scan_redirect(code: str, db: Session = Depends(get_db), _=Depends(require_user)):
    # 1. Zkus položku
    item = db.scalar(select(Item).where(Item.code == code, Item.is_active == True))
    if item:
        active_audit = db.scalar(select(Audit).where(Audit.status == "open").limit(1))
        if active_audit:
            return RedirectResponse(url=f"{settings.BASE_URL}/inventury/{active_audit.id}/sken/{code}")
        return RedirectResponse(url=f"{settings.BASE_URL}/majetek/{item.id}")

    # 2. Zkus lokaci
    loc = db.scalar(select(Location).where(Location.code == code, Location.is_active == True))
    if loc:
        return RedirectResponse(url=f"{settings.BASE_URL}/lokace/{loc.id}")

    # 3. Neznámý kód → home
    return RedirectResponse(url=f"{settings.BASE_URL}/")


@router.get("/api/scan/resolve/{code}")
def resolve_code(code: str, db: Session = Depends(get_db), _=Depends(require_session_user)):
    """JSON endpoint — vrátí info o kódu bez redirectu. Používá scan stránka."""

    # Zkus aktivní položku
    item = db.scalar(select(Item).where(Item.code == code))
    if item:
        active_audit = db.scalar(select(Audit).where(Audit.status == "open").limit(1))
        audit_id = None
        audit_status = None
        if active_audit:
            audit_id = active_audit.id
            existing = db.scalar(
                select(AuditScan).where(
                    AuditScan.audit_id == active_audit.id,
                    AuditScan.item_id == item.id,
                )
            )
            audit_status = "scanned" if existing else "not_scanned"

        # Aktuální lokace
        current = db.scalar(
            select(Assignment)
            .where(Assignment.item_id == item.id)
            .order_by(Assignment.assigned_at.desc())
            .limit(1)
        )
        loc_name = None
        loc_id = None
        if current:
            loc = db.get(Location, current.location_id)
            if loc:
                loc_name = loc.name
                loc_id = loc.id

        return {
            "type": "item",
            "id": item.id,
            "name": item.name,
            "code": item.code,
            "category": item.category,
            "is_active": item.is_active,
            "current_location_name": loc_name,
            "current_location_id": loc_id,
            "audit_id": audit_id,
            "audit_status": audit_status,
        }

    # Zkus lokaci
    loc = db.scalar(select(Location).where(Location.code == code, Location.is_active == True))
    if loc:
        return {
            "type": "location",
            "id": loc.id,
            "name": loc.name,
            "code": loc.code,
            "building": loc.building,
            "floor": loc.floor,
        }

    return {"type": "unknown", "code": code}

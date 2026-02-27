from fastapi import APIRouter, Depends, Request, Query, UploadFile, File
from app.routers.auth_ui import require_user, require_manager, verify_csrf
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, func, extract
from app.database import get_db
from app.models.item import Item
from app.models.location import Location
from app.models.assignment import Assignment
from app.models.audit import Audit, AuditScan
from app.models.disposal import Disposal, DisposalReason
import app.services.item_service as item_svc
import app.services.location_service as loc_svc
import app.services.audit_service as audit_svc
import app.services.disposal_service as disposal_svc
import app.services.import_service as import_svc
from app.config import settings
from datetime import datetime, timezone

_REASON_LABELS = {
    "liquidation": "Likvidace",
    "sale": "Prodej",
    "donation": "Darování",
    "theft": "Krádež",
    "loss": "Ztráta",
    "transfer": "Převod",
}

router = APIRouter(tags=["ui"], dependencies=[Depends(require_user)])
templates = Jinja2Templates(directory="app/templates")


def flash(request: Request, message: str, category: str = "info") -> None:
    msgs = request.session.setdefault("_flash_messages", [])
    msgs.append((category, message))


def _get_active_audit(db: Session):
    return db.scalar(select(Audit).where(Audit.status == "open").limit(1))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    total_items = db.scalar(select(func.count()).select_from(Item).where(Item.is_active == True))
    total_locations = db.scalar(select(func.count()).select_from(Location).where(Location.is_active == True))
    open_audits = db.scalar(select(func.count()).select_from(Audit).where(Audit.status == "open"))

    # Moves this month
    now = datetime.now(timezone.utc)
    moves_this_month = db.scalar(
        select(func.count()).select_from(Assignment).where(
            extract("year", Assignment.assigned_at) == now.year,
            extract("month", Assignment.assigned_at) == now.month,
        )
    ) or 0

    # Recent activity: last 10 assignments
    recent_assignments = db.scalars(
        select(Assignment)
        .join(Item, Assignment.item_id == Item.id)
        .order_by(Assignment.assigned_at.desc())
        .limit(10)
    ).all()

    # Recent audit scans: last 10
    recent_scans = db.scalars(
        select(AuditScan)
        .join(Item, AuditScan.item_id == Item.id)
        .order_by(AuditScan.scanned_at.desc())
        .limit(10)
    ).all()

    # Recent disposals: last 10
    recent_disposals = db.scalars(
        select(Disposal)
        .join(Item, Disposal.item_id == Item.id)
        .order_by(Disposal.disposed_at.desc())
        .limit(10)
    ).all()

    # Sestavit unified timeline z přesunů, skenů inventury a vyřazení
    recent_activity = []
    for a in recent_assignments:
        if a.item:
            recent_activity.append({
                "item_id": a.item.id,
                "item_name": a.item.name,
                "item_code": a.item.code,
                "pill_type": "move",
                "type_label": "Přesun",
                "detail": f"→ {a.location.name}" if a.location else "",
                "created_at": a.assigned_at,
            })

    for s in recent_scans:
        if s.item:
            recent_activity.append({
                "item_id": s.item.id,
                "item_name": s.item.name,
                "item_code": s.item.code,
                "pill_type": "audit",
                "type_label": "Inventura",
                "detail": s.audit.name if s.audit else "",
                "created_at": s.scanned_at,
            })

    for d in recent_disposals:
        if d.item:
            recent_activity.append({
                "item_id": d.item.id,
                "item_name": d.item.name,
                "item_code": d.item.code,
                "pill_type": "remove",
                "type_label": "Vyřazení",
                "detail": _REASON_LABELS.get(d.reason, d.reason),
                "created_at": d.disposed_at,
            })

    recent_activity.sort(key=lambda x: x["created_at"], reverse=True)
    recent_activity = recent_activity[:10]

    # Active audit + report
    active_audit = _get_active_audit(db)
    report = None
    if active_audit:
        report = audit_svc.get_audit_report(db, active_audit.id)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_items": total_items,
        "total_locations": total_locations,
        "open_audits": open_audits,
        "moves_this_month": moves_this_month,
        "recent_activity": recent_activity,
        "active_audit": active_audit,
        "report": report,
    })


@router.get("/majetek", response_class=HTMLResponse)
def items_list(request: Request, page: int = 1, search: str = "", category: str = "", db: Session = Depends(get_db)):
    result = item_svc.get_items(db, page=page, size=20, search=search, category=category)

    # Enrich items with current_location
    items = []
    for item in result.items:
        assignment = item_svc.get_current_location(db, item.id)
        loc_name = None
        if assignment:
            loc = db.get(Location, assignment.location_id)
            loc_name = loc.name if loc else None
        item.current_location = loc_name
        items.append(item)
    result.items = items

    # Get unique categories
    categories = db.scalars(
        select(Item.category).where(Item.is_active == True, Item.category != None).distinct()
    ).all()

    locations = db.scalars(select(Location).where(Location.is_active == True).order_by(Location.name)).all()

    return templates.TemplateResponse("items/list.html", {
        "request": request,
        "page_data": result,
        "items": items,
        "search": search,
        "selected_category": category,
        "categories": sorted([c for c in categories if c]),
        "locations": locations,
    })


@router.get("/majetek/search", response_class=HTMLResponse)
def items_search(request: Request, search: str = "", category: str = "", db: Session = Depends(get_db)):
    result = item_svc.get_items(db, page=1, size=50, search=search, category=category)
    items = []
    for item in result.items:
        assignment = item_svc.get_current_location(db, item.id)
        loc_name = None
        if assignment:
            loc = db.get(Location, assignment.location_id)
            loc_name = loc.name if loc else None
        item.current_location = loc_name
        items.append(item)
    return templates.TemplateResponse("partials/item_row.html", {
        "request": request,
        "items": items,
    })


@router.get("/majetek/novy", response_class=RedirectResponse)
def items_new_redirect():
    return RedirectResponse("/majetek", status_code=302)


@router.get("/majetek/{item_id}", response_class=HTMLResponse)
def item_detail(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = item_svc.get_item(db, item_id)
    history = item_svc.get_item_history(db, item_id)
    current = item_svc.get_current_location(db, item_id)
    locations = db.scalars(select(Location).where(Location.is_active == True)).all()
    disposal = db.scalar(
        select(Disposal).where(Disposal.item_id == item_id).order_by(Disposal.disposed_at.desc()).limit(1)
    )

    # Enrich history with location objects
    for a in history:
        if not hasattr(a, 'location') or a.location is None:
            a.location = db.get(Location, a.location_id)

    # Current assignment with location
    if current and not hasattr(current, 'location'):
        current.location = db.get(Location, current.location_id)

    scan_url = f"{settings.BASE_URL}/scan/{item.code}"

    return templates.TemplateResponse("items/detail.html", {
        "request": request,
        "item": item,
        "history": history,
        "current_assignment": current,
        "locations": locations,
        "disposal": disposal,
        "disposal_reason_label": _REASON_LABELS.get(disposal.reason if disposal else "", ""),
        "scan_url": scan_url,
    })


@router.get("/lokace", response_class=HTMLResponse)
def locations_list(request: Request, page: int = 1, db: Session = Depends(get_db)):
    result = loc_svc.get_locations(db, page=page, size=50)

    # Count items per location (latest assignment per item)
    subq = (
        select(Assignment.item_id, func.max(Assignment.assigned_at).label("max_at"))
        .group_by(Assignment.item_id)
        .subquery()
    )
    rows = db.execute(
        select(Assignment.location_id, func.count(Item.id))
        .join(subq, (Assignment.item_id == subq.c.item_id) & (Assignment.assigned_at == subq.c.max_at))
        .join(Item, Item.id == Assignment.item_id)
        .where(Item.is_active == True)
        .group_by(Assignment.location_id)
    ).all()
    item_counts = {loc_id: cnt for loc_id, cnt in rows}

    return templates.TemplateResponse("locations/list.html", {
        "request": request,
        "page_data": result,
        "item_counts": item_counts,
    })


@router.get("/lokace/{loc_id}", response_class=HTMLResponse)
def location_detail(loc_id: int, request: Request, db: Session = Depends(get_db)):
    loc = loc_svc.get_location(db, loc_id)
    items = loc_svc.get_items_at_location(db, loc_id)
    return templates.TemplateResponse("locations/detail.html", {
        "request": request,
        "location": loc,
        "items": items,
    })


@router.post("/lokace/{loc_id}/deactivate")
async def location_deactivate(loc_id: int, request: Request, db: Session = Depends(get_db), _=Depends(require_manager), _csrf=Depends(verify_csrf)):
    loc_svc.delete_location(db, loc_id)
    flash(request, f"Lokace byla deaktivována.", "success")
    return RedirectResponse("/lokace", status_code=303)


@router.get("/inventury", response_class=HTMLResponse)
def audits_list(request: Request, db: Session = Depends(get_db)):
    result = audit_svc.get_audits(db, page=1, size=50)
    return templates.TemplateResponse("audits/list.html", {
        "request": request,
        "audits": result.items,
    })


@router.get("/inventury/{audit_id}", response_class=HTMLResponse)
def audit_detail(audit_id: int, request: Request, db: Session = Depends(get_db)):
    audit = audit_svc.get_audit(db, audit_id)
    report = audit_svc.get_audit_report(db, audit_id)
    return templates.TemplateResponse("audits/detail.html", {
        "request": request,
        "audit": audit,
        "report": report,
    })


@router.get("/inventury/{audit_id}/progress", response_class=HTMLResponse)
def audit_progress(audit_id: int, request: Request, db: Session = Depends(get_db)):
    audit = audit_svc.get_audit(db, audit_id)
    report = audit_svc.get_audit_report(db, audit_id)
    return templates.TemplateResponse("partials/audit_progress.html", {
        "request": request,
        "audit": audit,
        "report": report,
    })


@router.get("/inventury/{audit_id}/sken/{item_code}", response_class=HTMLResponse)
def audit_scan_page(audit_id: int, item_code: str, request: Request, db: Session = Depends(get_db)):
    audit = audit_svc.get_audit(db, audit_id)
    item = item_svc.get_item_by_code(db, item_code)
    return templates.TemplateResponse("audits/scan.html", {
        "request": request,
        "audit": audit,
        "item": item,
        "item_code": item_code,
    })


@router.get("/sken", response_class=HTMLResponse)
def scan_page(request: Request, db: Session = Depends(get_db)):
    active_audit = _get_active_audit(db)
    return templates.TemplateResponse("scan/index.html", {
        "request": request,
        "active_audit": active_audit,
    })


@router.get("/tisk", response_class=HTMLResponse)
def print_page(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(Item).where(Item.is_active == True)).all()
    locations = db.scalars(select(Location).where(Location.is_active == True)).all()
    return templates.TemplateResponse("print.html", {
        "request": request,
        "items": items,
        "locations": locations,
    })


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request, db: Session = Depends(get_db), _=Depends(require_manager)):
    locations = db.scalars(select(Location).where(Location.is_active == True).order_by(Location.code)).all()
    return templates.TemplateResponse("import.html", {
        "request": request,
        "result": None,
        "locations": locations,
    })


@router.post("/import", response_class=HTMLResponse)
async def import_items(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(require_manager)):
    locations = db.scalars(select(Location).where(Location.is_active == True).order_by(Location.code)).all()

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        result = {
            "success": False,
            "error": "Nepodporovaný formát souboru. Nahrajte soubor .xlsx nebo .xlsm.",
            "imported": 0, "skipped": 0, "errors": 0, "details": [],
        }
        return templates.TemplateResponse("import.html", {
            "request": request, "result": result, "locations": locations,
        })

    # Rychlá kontrola Content-Length před čtením do paměti
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        result = {
            "success": False,
            "error": "Soubor je příliš velký. Maximální povolená velikost je 10 MB.",
            "imported": 0, "skipped": 0, "errors": 0, "details": [],
        }
        return templates.TemplateResponse("import.html", {
            "request": request, "result": result, "locations": locations,
        })

    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        result = {
            "success": False,
            "error": "Soubor je příliš velký. Maximální povolená velikost je 10 MB.",
            "imported": 0, "skipped": 0, "errors": 0, "details": [],
        }
        return templates.TemplateResponse("import.html", {
            "request": request, "result": result, "locations": locations,
        })

    result = import_svc.import_items_from_excel(db, file_data)
    return templates.TemplateResponse("import.html", {
        "request": request,
        "result": result,
        "locations": locations,
    })


@router.get("/vyrazeni/sken", response_class=HTMLResponse)
def dispose_scan_page(request: Request):
    return templates.TemplateResponse("dispose/scan.html", {"request": request})


@router.get("/vyrazeni", response_class=HTMLResponse)
def disposals_list(
    request: Request,
    page: int = Query(1, ge=1),
    year: str | None = Query(None),
    reason: str | None = Query(None),
    db: Session = Depends(get_db),
):
    year_int: int | None = int(year) if year and year.strip().isdigit() else None
    reason_clean: str | None = reason if reason and reason.strip() else None
    page_data = disposal_svc.get_disposals(db, page=page, size=25, year=year_int, reason=reason_clean)

    years_raw = db.scalars(
        select(extract("year", Disposal.disposed_at)).distinct().order_by(
            extract("year", Disposal.disposed_at).desc()
        )
    ).all()
    available_years = [int(y) for y in years_raw if y is not None]

    return templates.TemplateResponse("disposals/list.html", {
        "request": request,
        "page_data": page_data,
        "selected_year": year_int,
        "selected_reason": reason_clean,
        "available_years": available_years,
        "reason_choices": list(_REASON_LABELS.items()),
        "reason_labels": _REASON_LABELS,
    })

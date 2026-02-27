from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.audit import AuditCreate, AuditScanRequest, AuditScanResponse, AuditResponse
from app.schemas.pagination import Page
from app.routers.auth_ui import require_session_user, require_session_manager
import app.services.audit_service as svc

router = APIRouter(prefix="/api/audits", tags=["audits"])


@router.get("", response_model=Page[AuditResponse])
def list_audits(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_session_user),
):
    return svc.get_audits(db, page=page, size=size)


@router.post("", response_model=AuditResponse, status_code=201)
def create_audit(request: Request, data: AuditCreate, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    user_id = request.session.get("user_id")
    return svc.create_audit(db, data, user_id=user_id)


@router.get("/{audit_id}", response_model=AuditResponse)
def get_audit(audit_id: int, db: Session = Depends(get_db), _=Depends(require_session_user)):
    return svc.get_audit(db, audit_id)


@router.post("/{audit_id}/scan", response_model=AuditScanResponse)
def scan_item(request: Request, audit_id: int, data: AuditScanRequest, db: Session = Depends(get_db), _=Depends(require_session_user)):
    user_id = request.session.get("user_id")
    return svc.scan_item(db, audit_id, data, user_id=user_id)


@router.post("/{audit_id}/close", response_model=AuditResponse)
def close_audit(request: Request, audit_id: int, db: Session = Depends(get_db), _=Depends(require_session_manager)):
    user_id = request.session.get("user_id")
    return svc.close_audit(db, audit_id, user_id=user_id)


@router.get("/{audit_id}/report")
def audit_report(audit_id: int, db: Session = Depends(get_db), _=Depends(require_session_user)):
    report = svc.get_audit_report(db, audit_id)
    return {
        "audit_id": audit_id,
        "audit_name": report["audit"].name,
        "status": report["audit"].status,
        "scanned_count": report["scanned_count"],
        "total_items": report["total_items"],
        "missing_count": report["missing_count"],
        "missing_items": [{"id": i.id, "code": i.code, "name": i.name} for i in report["missing_items"]],
    }

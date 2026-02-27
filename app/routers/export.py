from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
import app.services.export_service as svc
import app.services.import_service as import_svc

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/export/excel")
def export_excel(db: Session = Depends(get_db)):
    xlsx_bytes = svc.export_items_excel(db)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=inventory.xlsx"},
    )


@router.get("/export/pdf/{audit_id}")
def export_audit_pdf(audit_id: int, db: Session = Depends(get_db)):
    pdf_bytes = svc.export_audit_pdf(db, audit_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=audit-{audit_id}.pdf"},
    )


@router.get("/export/excel/disposals")
def export_disposals_excel(db: Session = Depends(get_db)):
    xlsx_bytes = svc.export_disposals_excel(db)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=vyrazeny-majetek.xlsx"},
    )


@router.get("/export/pdf/disposal/{disposal_id}")
def export_disposal_pdf(disposal_id: int, db: Session = Depends(get_db)):
    pdf_bytes = svc.export_disposal_pdf(db, disposal_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=protokol-vyrazeni-{disposal_id}.pdf"},
    )


@router.get("/import/template")
def download_import_template():
    """Stáhne Excel šablonu pro hromadný import majetku."""
    xlsx_bytes = import_svc.generate_import_template()
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=assettrack-import-sablona.xlsx"},
    )

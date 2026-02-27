from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
import app.services.qr_service as svc

router = APIRouter(prefix="/api/qr", tags=["qr"])


@router.get("/item/{item_id}")
def qr_item(item_id: int, db: Session = Depends(get_db)):
    png_bytes = svc.generate_item_qr(db, item_id)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/location/{loc_id}")
def qr_location(loc_id: int, db: Session = Depends(get_db)):
    png_bytes = svc.generate_location_qr(db, loc_id)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/batch")
def qr_batch(
    ids: str = Query(..., description="Comma-separated IDs"),
    type: str = Query("item", description="Typ štítku: 'item' nebo 'location'"),
    db: Session = Depends(get_db),
):
    id_list = [int(i.strip()) for i in ids.split(",") if i.strip().isdigit()]

    if type == "location":
        pdf_bytes = svc.generate_location_batch_pdf(db, id_list)
        filename = "qr-lokace.pdf"
    else:
        pdf_bytes = svc.generate_batch_pdf(db, id_list)
        filename = "qr-labels.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

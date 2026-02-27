import io
import os
import qrcode
from qrcode.image.pil import PilImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.item import Item
from app.models.location import Location
from app.config import settings


# ── Font registration (podpora české diakritiky) ──────────────────────────────
_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_CZECH_CAPABLE = False

# Kandidátní páry fontů: (regular, bold, jméno_regular, jméno_bold)
_FONT_PAIRS = [
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVu", "DejaVuBold",
    ),
    (
        "/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/ttf-dejavu/DejaVuSans-Bold.ttf",
        "DejaVu", "DejaVuBold",
    ),
    (
        "/mnt/c/Windows/Fonts/arial.ttf",
        "/mnt/c/Windows/Fonts/arialbd.ttf",
        "Arial", "ArialBold",
    ),
    (
        "/mnt/c/Windows/Fonts/calibri.ttf",
        "/mnt/c/Windows/Fonts/calibrib.ttf",
        "Calibri", "CalibriBold",
    ),
]


def _init_fonts() -> None:
    global _FONT_REGULAR, _FONT_BOLD, _CZECH_CAPABLE
    for reg_path, bold_path, reg_name, bold_name in _FONT_PAIRS:
        if not os.path.exists(reg_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(reg_name, reg_path))
            _FONT_REGULAR = reg_name
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                _FONT_BOLD = bold_name
            else:
                _FONT_BOLD = reg_name  # regular jako náhrada bold
            _CZECH_CAPABLE = True
            break
        except Exception:
            continue


_init_fonts()

# Transliterace pro případ, že není dostupný Unicode font (Helvetica = Latin-1)
_CZECH_MAP = str.maketrans(
    "áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ",
    "acdeeinorstuuyzACDEEINORSTUUYZ",
)


def _t(text: str) -> str:
    """Vrátí text bezpečný pro aktuální font — přeloží diakritiku pokud nutno."""
    if _CZECH_CAPABLE:
        return text
    return text.translate(_CZECH_MAP)


# ── Generování QR kódu (PNG) ──────────────────────────────────────────────────

def _make_qr_bytes(url: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img: PilImage = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_item_qr(db: Session, item_id: int) -> bytes:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Položka nenalezena")
    url = f"{settings.BASE_URL}/scan/{item.code}"
    return _make_qr_bytes(url)


def generate_location_qr(db: Session, loc_id: int) -> bytes:
    loc = db.get(Location, loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Lokace nenalezena")
    url = f"{settings.BASE_URL}/scan/{loc.code}"
    return _make_qr_bytes(url)


# ── PDF štítky pro položky ─────────────────────────────────────────────────────

def generate_batch_pdf(db: Session, item_ids: list[int]) -> bytes:
    """PDF se štítky pro položky — čtvercový QR ~3.3 cm + kód + název."""
    items = [db.get(Item, iid) for iid in item_ids if db.get(Item, iid)]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_width, page_height = A4

    label_w = 50 * mm   # šířka štítku
    label_h = 48 * mm   # výška štítku
    qr_size = 33 * mm   # QR kód 3.3 × 3.3 cm — vždy čtvercový
    margin = 8 * mm

    cols = int((page_width - margin) / (label_w + margin))
    rows_per_page = int((page_height - margin) / (label_h + margin))

    for idx, item in enumerate(items):
        col = idx % cols
        row = (idx // cols) % rows_per_page
        if idx > 0 and idx % (cols * rows_per_page) == 0:
            c.showPage()

        x = margin + col * (label_w + margin)
        y = page_height - margin - (row + 1) * (label_h + margin)

        # QR kód — čtvercový, centrovaný horizontálně
        qr_x = x + (label_w - qr_size) / 2
        qr_y = y + 13 * mm  # 13 mm prostoru dole pro text
        qr_png = _make_qr_bytes(f"{settings.BASE_URL}/scan/{item.code}")
        c.drawImage(
            ImageReader(io.BytesIO(qr_png)),
            qr_x, qr_y,
            width=qr_size, height=qr_size,  # width == height → čtverec
        )

        # Kód položky — tučně
        c.setFont(_FONT_BOLD, 8)
        c.drawCentredString(x + label_w / 2, y + 7 * mm, _t(item.code))

        # Název položky
        c.setFont(_FONT_REGULAR, 7)
        c.drawCentredString(x + label_w / 2, y + 2.5 * mm, _t(item.name[:28]))

        # Rámeček
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.rect(x, y, label_w, label_h)

    c.save()
    return buf.getvalue()


# ── PDF štítky pro lokace ──────────────────────────────────────────────────────

def generate_location_batch_pdf(db: Session, loc_ids: list[int]) -> bytes:
    """PDF se štítky pro lokace — čtvercový QR ~3.5 cm + kód + název, modrý header."""
    locations = [db.get(Location, lid) for lid in loc_ids if db.get(Location, lid)]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_width, page_height = A4

    label_w = 60 * mm   # šířka štítku
    label_h = 56 * mm   # výška štítku
    qr_size = 35 * mm   # QR kód 3.5 × 3.5 cm — vždy čtvercový
    header_h = 10 * mm  # výška modrého záhlaví
    margin = 8 * mm

    cols = int((page_width - margin) / (label_w + margin))
    rows_per_page = int((page_height - margin) / (label_h + margin))

    for idx, loc in enumerate(locations):
        col = idx % cols
        row = (idx // cols) % rows_per_page
        if idx > 0 and idx % (cols * rows_per_page) == 0:
            c.showPage()

        x = margin + col * (label_w + margin)
        y = page_height - margin - (row + 1) * (label_h + margin)

        # Modrý záhlaví pruh (nahoře)
        c.setFillColor(colors.HexColor("#0d6efd"))
        c.rect(x, y + label_h - header_h, label_w, header_h, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont(_FONT_BOLD, 8)
        c.drawCentredString(x + label_w / 2, y + label_h - 6.5 * mm, "LOKACE / ROOM")

        # QR kód — čtvercový, centrovaný, s 1 mm mezerou pod záhlavím
        c.setFillColor(colors.black)
        qr_x = x + (label_w - qr_size) / 2
        qr_y = y + 10 * mm  # 10 mm dole pro text; QR sahá do y+45mm, záhlaví od y+46mm
        qr_png = _make_qr_bytes(f"{settings.BASE_URL}/scan/{loc.code}")
        c.drawImage(
            ImageReader(io.BytesIO(qr_png)),
            qr_x, qr_y,
            width=qr_size, height=qr_size,  # width == height → čtverec
        )

        # Kód místnosti — tučně, větší písmo
        c.setFont(_FONT_BOLD, 10)
        c.drawCentredString(x + label_w / 2, y + 7 * mm, _t(loc.code))

        # Název místnosti
        c.setFont(_FONT_REGULAR, 8)
        c.drawCentredString(x + label_w / 2, y + 3 * mm, _t(loc.name[:32]))

        # Modrý rámeček
        c.setStrokeColor(colors.HexColor("#0d6efd"))
        c.setLineWidth(2)
        c.rect(x, y, label_w, label_h)
        c.setLineWidth(1)

    c.save()
    return buf.getvalue()

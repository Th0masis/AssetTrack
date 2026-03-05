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
from reportlab.pdfbase.pdfmetrics import stringWidth
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

def _make_qr_bytes(url: str, border: int = 4) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=10, border=border)
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
    """PDF se štítky pro položky — QR vlevo + kód vpravo, výška štítku 2 cm."""
    items = [db.get(Item, iid) for iid in item_ids if db.get(Item, iid)]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_width, page_height = A4

    label_h = 20 * mm   # výška štítku = 2 cm
    qr_size = 16 * mm   # QR čtverec — vejde se do 2 cm s 2mm marginem
    pad = 2 * mm        # vnitřní mezery

    # Šířka se přizpůsobí nejdelšímu kódu — min. 55 mm
    label_w = 55 * mm
    margin = 6 * mm

    cols = int((page_width - margin) / (label_w + margin))
    rows_per_page = int((page_height - margin) / (label_h + margin))

    for idx, item in enumerate(items):
        col = idx % cols
        row = (idx // cols) % rows_per_page
        if idx > 0 and idx % (cols * rows_per_page) == 0:
            c.showPage()

        x = margin + col * (label_w + margin)
        y = page_height - margin - (row + 1) * (label_h + margin)

        # QR kód — vlevo, vertikálně vystředěn
        qr_x = x + pad
        qr_y = y + (label_h - qr_size) / 2
        # border=1 — minimální quiet zone, vzor QR vyplní téměř celý qr_size
        qr_png = _make_qr_bytes(f"{settings.BASE_URL}/scan/{item.code}", border=1)
        c.drawImage(
            ImageReader(io.BytesIO(qr_png)),
            qr_x, qr_y,
            width=qr_size, height=qr_size,
        )

        # Kód položky — vpravo od QR, tučně, auto-fit, vertikálně vystředěn
        code_text = _t(item.code)
        code_x = x + pad + qr_size + pad          # začátek textové oblasti
        code_w = label_w - pad - qr_size - 2 * pad  # dostupná šířka pro text
        font_size = _fit_font_size(code_text, _FONT_BOLD, code_w, start_size=14.0)
        c.setFont(_FONT_BOLD, font_size)
        # Vertikální střed: baseline ≈ střed štítku - 1/3 velikosti fontu
        text_y = y + label_h / 2 - font_size * 0.35 * mm
        c.drawString(code_x, text_y, code_text)

        # Rámeček
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.rect(x, y, label_w, label_h)

    c.save()
    return buf.getvalue()


# ── PDF štítky pro lokace ──────────────────────────────────────────────────────

def _fit_font_size(text: str, font_name: str, max_width: float, start_size: float, min_size: float = 5.0) -> float:
    """Vrátí největší velikost fontu, při které text nepřesáhne max_width."""
    size = start_size
    while size > min_size and stringWidth(text, font_name, size) > max_width:
        size -= 0.5
    return size


def generate_location_batch_pdf(db: Session, loc_ids: list[int]) -> bytes:
    """PDF se štítky pro lokace — čtvercový QR 2 cm + kód lokace v záhlaví + název."""
    locations = [db.get(Location, lid) for lid in loc_ids if db.get(Location, lid)]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_width, page_height = A4

    label_w = 45 * mm   # šířka štítku — širší pro dlouhé kódy
    label_h = 42 * mm   # výška štítku
    qr_size = 20 * mm   # QR kód 2 × 2 cm — vždy čtvercový
    header_h = 8 * mm   # výška modrého záhlaví
    margin = 6 * mm
    inner_pad = 2 * mm  # vnitřní okraj záhlaví

    cols = int((page_width - margin) / (label_w + margin))
    rows_per_page = int((page_height - margin) / (label_h + margin))

    for idx, loc in enumerate(locations):
        col = idx % cols
        row = (idx // cols) % rows_per_page
        if idx > 0 and idx % (cols * rows_per_page) == 0:
            c.showPage()

        x = margin + col * (label_w + margin)
        y = page_height - margin - (row + 1) * (label_h + margin)

        # Modrý záhlaví pruh (nahoře) — název místnosti
        c.setFillColor(colors.HexColor("#0d6efd"))
        c.rect(x, y + label_h - header_h, label_w, header_h, fill=True, stroke=False)
        c.setFillColor(colors.white)
        header_text = _t(loc.name)
        header_font_size = _fit_font_size(header_text, _FONT_BOLD, label_w - 2 * inner_pad, start_size=8.0)
        c.setFont(_FONT_BOLD, header_font_size)
        c.drawCentredString(x + label_w / 2, y + label_h - 5 * mm, header_text)

        # QR kód — čtvercový, centrovaný
        c.setFillColor(colors.black)
        qr_x = x + (label_w - qr_size) / 2
        qr_y = y + 10 * mm
        qr_png = _make_qr_bytes(f"{settings.BASE_URL}/scan/{loc.code}")
        c.drawImage(
            ImageReader(io.BytesIO(qr_png)),
            qr_x, qr_y,
            width=qr_size, height=qr_size,
        )

        # Kód místnosti pod QR — tučně, auto-fit
        code_text = _t(loc.code)
        code_font_size = _fit_font_size(code_text, _FONT_BOLD, label_w - 2 * inner_pad, start_size=9.0)
        c.setFont(_FONT_BOLD, code_font_size)
        c.drawCentredString(x + label_w / 2, y + 4 * mm, code_text)

        # Modrý rámeček
        c.setStrokeColor(colors.HexColor("#0d6efd"))
        c.setLineWidth(2)
        c.rect(x, y, label_w, label_h)
        c.setLineWidth(1)

    c.save()
    return buf.getvalue()

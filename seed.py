"""Seed script — naplní DB testovacími daty."""
import os
import sys

# Ensure we're in the project root
sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.location import Location
from app.models.item import Item
from app.models.assignment import Assignment
from app.models.disposal import Disposal, DisposalReason
from app.services.user_service import hash_password
from datetime import date, datetime, timezone


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Admin user
    if not db.query(User).filter_by(username="admin").first():
        admin = User(
            username="admin",
            email="admin@assettrack.local",
            hashed_password=hash_password("admin123"),
            role="admin",
        )
        db.add(admin)

    # Locations
    locs = [
        Location(name="Serverovna", code="LOC-SRV", building="A", floor="1", description="Hlavní serverovna"),
        Location(name="Kancelář 101", code="LOC-K101", building="A", floor="1"),
        Location(name="Kancelář 201", code="LOC-K201", building="A", floor="2"),
        Location(name="Sklad IT", code="LOC-SKLAD", building="B", floor="0"),
    ]
    existing_codes = {l.code for l in db.query(Location).all()}
    for loc in locs:
        if loc.code not in existing_codes:
            db.add(loc)

    db.commit()

    # Items
    items_data = [
        ("IT-NB-001", "Notebook Dell Latitude", "IT", "SN-DELL-001", date(2023, 1, 10), 35000),
        ("IT-NB-002", "Notebook Lenovo ThinkPad", "IT", "SN-LEN-001", date(2023, 3, 15), 32000),
        ("IT-MON-001", "Monitor Samsung 24\"", "IT", "SN-SAM-001", date(2022, 6, 1), 8500),
        ("IT-MON-002", "Monitor LG 27\"", "IT", "SN-LG-001", date(2023, 9, 20), 12000),
        ("NAB-ZID-001", "Nábytek — Psací stůl", "Nábytek", None, date(2021, 1, 1), 5000),
        ("NAB-ZID-002", "Kancelářská židle", "Nábytek", None, date(2021, 1, 1), 3500),
        ("IT-TIS-001", "Tiskárna HP LaserJet", "IT", "SN-HP-001", date(2022, 11, 5), 15000),
        ("TEL-001", "Telefon Cisco IP", "Telefony", "SN-CIS-001", date(2022, 5, 10), 4500),
    ]

    existing_item_codes = {i.code for i in db.query(Item).all()}
    locs_all = db.query(Location).all()
    loc_srv = next((l for l in locs_all if l.code == "LOC-SRV"), locs_all[0] if locs_all else None)
    loc_k101 = next((l for l in locs_all if l.code == "LOC-K101"), loc_srv)

    for code, name, cat, sn, pd, price in items_data:
        if code not in existing_item_codes:
            item = Item(code=code, name=name, category=cat, serial_number=sn,
                       purchase_date=pd, purchase_price=price)
            db.add(item)
            db.flush()
            # Assign to a location
            target_loc = loc_srv if "IT-" in code or "IT-" in code else loc_k101
            if "NAB-" in code or "TEL-" in code:
                target_loc = loc_k101
            a = Assignment(item_id=item.id, location_id=target_loc.id if target_loc else 1, note="Počáteční přiřazení")
            db.add(a)

    db.commit()

    # ── Vyřazené položky ────────────────────────────────────────────────────
    disposed_data = [
        (
            "IT-NB-OLD-001", "Notebook HP ProBook (vyřazený)", "IT", "SN-HP-NB-001",
            date(2018, 3, 1), 28000,
            DisposalReason.liquidation, "Fyzicky poškozený, neopravitelný", "LIK-2024-001",
            datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc),
        ),
        (
            "IT-MON-OLD-001", "Monitor Dell 19\" (vyřazený)", "IT", None,
            date(2017, 1, 20), 4500,
            DisposalReason.sale, "Prodáno zaměstnanci za zůstatkovou cenu", "PROD-2024-042",
            datetime(2024, 8, 1, 9, 30, tzinfo=timezone.utc),
        ),
        (
            "NAB-KR-001", "Křeslo kancelářské (vyřazené)", "Nábytek", None,
            date(2016, 5, 10), 6000,
            DisposalReason.donation, "Darováno neziskové organizaci", "DAR-2024-007",
            datetime(2024, 9, 20, 14, 0, tzinfo=timezone.utc),
        ),
        (
            "TEL-OLD-001", "Mobilní telefon Nokia (ztracený)", "Telefony", "SN-NOK-001",
            date(2019, 11, 1), 3200,
            DisposalReason.theft, "Odcizeno při služební cestě, nahlášeno PČR", "PČR-2024-12345",
            datetime(2024, 10, 5, 8, 0, tzinfo=timezone.utc),
        ),
        (
            "IT-SRV-OLD-001", "Server Dell PowerEdge (převod)", "IT", "SN-DELL-SRV-001",
            date(2015, 7, 15), 120000,
            DisposalReason.transfer, "Převedeno na dceřinou společnost AssetTrack SK s.r.o.", "PREV-2024-003",
            datetime(2024, 12, 31, 12, 0, tzinfo=timezone.utc),
        ),
    ]

    admin = db.query(User).filter_by(username="admin").first()
    loc_sklad = next((l for l in db.query(Location).all() if l.code == "LOC-SKLAD"), None)
    existing_item_codes = {i.code for i in db.query(Item).all()}

    for (code, name, cat, sn, pd, price,
         reason, note, doc_ref, disposed_at) in disposed_data:
        if code not in existing_item_codes:
            item = Item(
                code=code, name=name, category=cat, serial_number=sn,
                purchase_date=pd, purchase_price=price,
                is_active=False,  # soft delete — vyřazená položka
            )
            db.add(item)
            db.flush()

            if loc_sklad:
                db.add(Assignment(
                    item_id=item.id,
                    location_id=loc_sklad.id,
                    note="Počáteční přiřazení (před vyřazením)",
                ))

            db.add(Disposal(
                item_id=item.id,
                reason=reason,
                disposed_at=disposed_at,
                disposed_by=admin.id if admin else None,
                note=note,
                document_ref=doc_ref,
            ))

    db.commit()
    db.close()
    print("✅ Seed dokončen!")


if __name__ == "__main__":
    seed()

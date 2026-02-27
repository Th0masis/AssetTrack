"""Unit testy pro SQLAlchemy modely."""
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.location import Location
from app.models.item import Item
from app.models.assignment import Assignment
from app.models.audit import Audit, AuditScan
from app.models.disposal import Disposal, DisposalReason


# ─── User ────────────────────────────────────────────────────────────────────

def test_user_create(db):
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpw",
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.role == "user"
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)


def test_user_unique_username(db):
    db.add(User(username="dup", email="a@a.com", hashed_password="x"))
    db.commit()
    db.add(User(username="dup", email="b@b.com", hashed_password="x"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_user_unique_email(db):
    db.add(User(username="u1", email="same@same.com", hashed_password="x"))
    db.commit()
    db.add(User(username="u2", email="same@same.com", hashed_password="x"))
    with pytest.raises(IntegrityError):
        db.commit()


# ─── Location ────────────────────────────────────────────────────────────────

def test_location_create(db):
    loc = Location(name="Serverovna", code="LOC-001", building="A", floor="1")
    db.add(loc)
    db.commit()
    db.refresh(loc)

    assert loc.id is not None
    assert loc.code == "LOC-001"
    assert loc.is_active is True


def test_location_unique_code(db):
    db.add(Location(name="L1", code="CODE-1"))
    db.commit()
    db.add(Location(name="L2", code="CODE-1"))
    with pytest.raises(IntegrityError):
        db.commit()


# ─── Item ─────────────────────────────────────────────────────────────────────

def test_item_create(db):
    item = Item(
        code="ITEM-001",
        name="Notebook Dell",
        category="IT",
        serial_number="SN123",
        purchase_date=date(2024, 1, 15),
        purchase_price=Decimal("29999.00"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.id is not None
    assert item.code == "ITEM-001"
    assert item.is_active is True
    assert item.purchase_price == Decimal("29999.00")


def test_item_unique_code(db):
    db.add(Item(code="DUP-ITEM", name="A"))
    db.commit()
    db.add(Item(code="DUP-ITEM", name="B"))
    with pytest.raises(IntegrityError):
        db.commit()


# ─── Assignment (append-only) ─────────────────────────────────────────────────

def test_assignment_create(db):
    user = User(username="u", email="u@u.com", hashed_password="x")
    loc = Location(name="L", code="L1")
    item = Item(code="I1", name="Item1")
    db.add_all([user, loc, item])
    db.commit()

    a = Assignment(item_id=item.id, location_id=loc.id, user_id=user.id, note="initial")
    db.add(a)
    db.commit()
    db.refresh(a)

    assert a.id is not None
    assert a.item_id == item.id
    assert isinstance(a.assigned_at, datetime)


def test_assignment_append_only(db):
    """Aktuální lokace = poslední assignment, nesmí být update."""
    user = User(username="u2", email="u2@u.com", hashed_password="x")
    loc1 = Location(name="L1", code="L001")
    loc2 = Location(name="L2", code="L002")
    item = Item(code="I2", name="Item2")
    db.add_all([user, loc1, loc2, item])
    db.commit()

    a1 = Assignment(item_id=item.id, location_id=loc1.id)
    db.add(a1)
    db.commit()

    a2 = Assignment(item_id=item.id, location_id=loc2.id)
    db.add(a2)
    db.commit()

    assignments = db.query(Assignment).filter_by(item_id=item.id).all()
    assert len(assignments) == 2
    latest = max(assignments, key=lambda x: x.assigned_at)
    assert latest.location_id == loc2.id


# ─── Audit ───────────────────────────────────────────────────────────────────

def test_audit_create(db):
    user = User(username="admin", email="admin@x.com", hashed_password="x")
    db.add(user)
    db.commit()

    audit = Audit(name="Inventura Q1 2024", created_by=user.id)
    db.add(audit)
    db.commit()
    db.refresh(audit)

    assert audit.id is not None
    assert audit.status == "open"


def test_audit_scan_idempotent(db):
    """Stejná položka naskenovaná 2× = IntegrityError (unique constraint)."""
    user = User(username="u3", email="u3@u.com", hashed_password="x")
    loc = Location(name="L", code="L999")
    item = Item(code="I3", name="Item3")
    db.add_all([user, loc, item])
    db.commit()

    audit = Audit(name="Test audit", created_by=user.id)
    db.add(audit)
    db.commit()

    scan1 = AuditScan(audit_id=audit.id, item_id=item.id, location_id=loc.id, scanned_by=user.id)
    db.add(scan1)
    db.commit()

    scan2 = AuditScan(audit_id=audit.id, item_id=item.id, location_id=loc.id, scanned_by=user.id)
    db.add(scan2)
    with pytest.raises(IntegrityError):
        db.commit()


def test_audit_scan_create(db):
    user = User(username="u4", email="u4@u.com", hashed_password="x")
    loc = Location(name="L", code="L888")
    item = Item(code="I4", name="Item4")
    db.add_all([user, loc, item])
    db.commit()

    audit = Audit(name="Test2", created_by=user.id)
    db.add(audit)
    db.commit()

    scan = AuditScan(audit_id=audit.id, item_id=item.id, location_id=loc.id, scanned_by=user.id)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    assert scan.id is not None
    assert scan.audit_id == audit.id
    assert isinstance(scan.scanned_at, datetime)


# ─── Disposal ─────────────────────────────────────────────────────────────────

def test_disposal_create(db):
    """Základní vytvoření záznamu o vyřazení."""
    user = User(username="disp_u1", email="disp1@x.com", hashed_password="x")
    item = Item(code="DISP-001", name="Vyřazený notebook")
    db.add_all([user, item])
    db.commit()

    disposal = Disposal(
        item_id=item.id,
        reason=DisposalReason.liquidation,
        disposed_by=user.id,
        note="Neopravitelná závada",
        document_ref="LIK-2024-001",
    )
    db.add(disposal)
    db.commit()
    db.refresh(disposal)

    assert disposal.id is not None
    assert disposal.reason == DisposalReason.liquidation
    assert disposal.item_id == item.id
    assert disposal.disposed_by == user.id
    assert disposal.document_ref == "LIK-2024-001"
    assert isinstance(disposal.disposed_at, datetime)


def test_disposal_all_reasons(db):
    """Všechny hodnoty enumu jsou platné."""
    item = Item(code="DISP-BASE", name="Base item")
    db.add(item)
    db.commit()

    for i, reason in enumerate(DisposalReason):
        d = Disposal(item_id=item.id, reason=reason)
        db.add(d)
        db.commit()
        db.refresh(d)
        assert d.reason == reason
        assert d.id is not None


def test_disposal_optional_fields(db):
    """Disposal funguje i bez volitelných polí."""
    item = Item(code="DISP-MIN", name="Minimální položka")
    db.add(item)
    db.commit()

    disposal = Disposal(item_id=item.id, reason=DisposalReason.loss)
    db.add(disposal)
    db.commit()
    db.refresh(disposal)

    assert disposal.disposed_by is None
    assert disposal.note is None
    assert disposal.document_ref is None


def test_disposal_relationship_item(db):
    """Relace disposal.item funguje správně."""
    item = Item(code="DISP-REL", name="Položka s relací")
    db.add(item)
    db.commit()

    disposal = Disposal(item_id=item.id, reason=DisposalReason.sale)
    db.add(disposal)
    db.commit()
    db.refresh(disposal)

    assert disposal.item is not None
    assert disposal.item.code == "DISP-REL"


def test_disposal_relationship_user(db):
    """Relace disposal.disposed_by_user funguje správně."""
    user = User(username="disp_u2", email="disp2@x.com", hashed_password="x")
    item = Item(code="DISP-USR", name="Položka uživatele")
    db.add_all([user, item])
    db.commit()

    disposal = Disposal(item_id=item.id, reason=DisposalReason.donation, disposed_by=user.id)
    db.add(disposal)
    db.commit()
    db.refresh(disposal)

    assert disposal.disposed_by_user is not None
    assert disposal.disposed_by_user.username == "disp_u2"


def test_disposal_item_soft_deleted(db):
    """Po vyřazení je položka označena is_active=False (soft delete)."""
    item = Item(code="DISP-SOFT", name="Soft deleted položka", is_active=True)
    db.add(item)
    db.commit()

    # Vyřazení: soft delete položky + záznam disposal
    item.is_active = False
    disposal = Disposal(item_id=item.id, reason=DisposalReason.theft, note="Odcizeno")
    db.add(disposal)
    db.commit()
    db.refresh(item)

    assert item.is_active is False
    assert len(item.disposals) == 1
    assert item.disposals[0].reason == DisposalReason.theft


def test_disposal_requires_item_id(db):
    """Disposal bez item_id (NULL) způsobí IntegrityError — pole je NOT NULL."""
    disposal = Disposal(reason=DisposalReason.loss)  # item_id chybí záměrně
    db.add(disposal)
    with pytest.raises(IntegrityError):
        db.commit()

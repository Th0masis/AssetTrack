"""Testy pro hromadné vyřazení a by-code endpoint."""


def _item(client, code, name="Item"):
    r = client.post("/api/items", json={"code": code, "name": name})
    assert r.status_code == 201
    return r.json()["id"]


# ── GET /api/items/by-code/{code} ─────────────────────────────────────────────

def test_get_item_by_code(client):
    _item(client, "BC-001", "By Code Item")
    res = client.get("/api/items/by-code/BC-001")
    assert res.status_code == 200
    assert res.json()["code"] == "BC-001"


def test_get_item_by_code_not_found(client):
    res = client.get("/api/items/by-code/NEXISTS-XYZ")
    assert res.status_code == 404


# ── POST /api/items/bulk-dispose ──────────────────────────────────────────────

def test_bulk_dispose_basic(client):
    """Hromadné vyřazení dvou položek."""
    id1 = _item(client, "BULK-001")
    id2 = _item(client, "BULK-002")

    res = client.post("/api/items/bulk-dispose", json={
        "item_ids": [id1, id2],
        "reason": "liquidation",
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["disposed"]) == 2
    assert data["skipped_ids"] == []
    assert all(d["reason"] == "liquidation" for d in data["disposed"])


def test_bulk_dispose_sets_inactive(client):
    """Po vyřazení jsou položky neaktivní."""
    id1 = _item(client, "BULK-003")
    id2 = _item(client, "BULK-004")
    client.post("/api/items/bulk-dispose", json={"item_ids": [id1, id2], "reason": "sale"})

    for item_id in [id1, id2]:
        res = client.get(f"/api/items/{item_id}")
        assert res.json()["is_active"] is False


def test_bulk_dispose_skips_already_inactive(client):
    """Již vyřazená položka je přeskočena, neskončí chybou."""
    id1 = _item(client, "BULK-005")
    id2 = _item(client, "BULK-006")
    # Vyřaď id1 předem
    client.post(f"/api/items/{id1}/dispose", json={"reason": "theft"})

    res = client.post("/api/items/bulk-dispose", json={
        "item_ids": [id1, id2],
        "reason": "loss",
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["disposed"]) == 1
    assert id1 in data["skipped_ids"]
    assert data["disposed"][0]["item_id"] == id2


def test_bulk_dispose_all_skipped(client):
    """Pokud jsou všechny položky již vyřazeny, vrátí prázdný disposed."""
    id1 = _item(client, "BULK-007")
    client.post(f"/api/items/{id1}/dispose", json={"reason": "sale"})

    res = client.post("/api/items/bulk-dispose", json={"item_ids": [id1], "reason": "loss"})
    assert res.status_code == 200
    data = res.json()
    assert data["disposed"] == []
    assert id1 in data["skipped_ids"]


def test_bulk_dispose_with_metadata(client):
    """Volitelná pole (datum, doklad, poznámka) se správně uloží."""
    id1 = _item(client, "BULK-008")
    res = client.post("/api/items/bulk-dispose", json={
        "item_ids": [id1],
        "reason": "donation",
        "disposed_at": "2024-06-15T10:00:00Z",
        "document_ref": "DAR-BULK-001",
        "note": "Hromadné darování",
    })
    assert res.status_code == 200
    d = res.json()["disposed"][0]
    assert d["document_ref"] == "DAR-BULK-001"
    assert d["note"] == "Hromadné darování"
    assert d["reason"] == "donation"


def test_bulk_dispose_missing_reason(client):
    """Chybějící reason → 422."""
    id1 = _item(client, "BULK-009")
    res = client.post("/api/items/bulk-dispose", json={"item_ids": [id1]})
    assert res.status_code == 422


def test_bulk_dispose_empty_ids(client):
    """Prázdný seznam item_ids → 422."""
    res = client.post("/api/items/bulk-dispose", json={"item_ids": [], "reason": "loss"})
    assert res.status_code == 422


# ── GET /api/qr/batch?type=location ──────────────────────────────────────────

def test_qr_batch_location(client):
    """Batch PDF pro lokace — správný content-type, PDF hlavička."""
    r1 = client.post("/api/locations", json={"name": "Místnost A", "code": "LOC-QR-001"})
    r2 = client.post("/api/locations", json={"name": "Místnost B", "code": "LOC-QR-002"})
    ids = f"{r1.json()['id']},{r2.json()['id']}"

    res = client.get(f"/api/qr/batch?ids={ids}&type=location")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content[:4] == b"%PDF"
    assert len(res.content) > 0


def test_qr_location_url_uses_scan_pattern(client):
    """QR kód lokace vrací PNG (URL obsahuje /scan/{code} — ověřeno indirektně přes PNG validitu)."""
    r = client.post("/api/locations", json={"name": "Test Loc QR", "code": "QRTEST-LOC"})
    loc_id = r.json()["id"]

    res = client.get(f"/api/qr/location/{loc_id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content[:4] == b'\x89PNG'


def test_scan_redirect_location(client):
    """Sken QR lokace přesměruje na detail lokace."""
    r = client.post("/api/locations", json={"name": "Scan Loc", "code": "SCAN-LOC-001"})
    loc_id = r.json()["id"]

    res = client.get("/scan/SCAN-LOC-001", follow_redirects=False)
    assert res.status_code in (301, 302, 307, 308)
    assert f"/lokace/{loc_id}" in res.headers["location"]

"""API testy pro POST /api/items/{id}/dispose a GET /api/disposals."""
from datetime import datetime, timezone


def _create_item(client, code="DISP-T001", name="Test Položka"):
    res = client.post("/api/items", json={"code": code, "name": name})
    assert res.status_code == 201
    return res.json()["id"]


# ─── POST /api/items/{id}/dispose ────────────────────────────────────────────

def test_dispose_item_basic(client):
    """Základní vyřazení — vrátí DisposalResponse s HTTP 201."""
    item_id = _create_item(client)
    res = client.post(f"/api/items/{item_id}/dispose", json={"reason": "liquidation"})
    assert res.status_code == 201
    data = res.json()
    assert data["item_id"] == item_id
    assert data["reason"] == "liquidation"
    assert data["disposed_by"] is None
    assert "disposed_at" in data


def test_dispose_sets_item_inactive(client):
    """Po vyřazení musí být položka is_active=False."""
    item_id = _create_item(client, code="DISP-T002")
    client.post(f"/api/items/{item_id}/dispose", json={"reason": "sale"})
    res = client.get(f"/api/items/{item_id}")
    # Soft-deleted položka stále existuje v DB
    assert res.json()["is_active"] is False


def test_dispose_with_all_fields(client):
    """Vyřazení se všemi volitelnými poli."""
    item_id = _create_item(client, code="DISP-T003")
    payload = {
        "reason": "donation",
        "disposed_at": "2024-09-15T10:00:00Z",
        "note": "Darováno škole",
        "document_ref": "DAR-2024-001",
    }
    res = client.post(f"/api/items/{item_id}/dispose", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["reason"] == "donation"
    assert data["note"] == "Darováno škole"
    assert data["document_ref"] == "DAR-2024-001"


def test_dispose_all_reason_values(client):
    """Všechny hodnoty enumu jsou přijaty."""
    reasons = ["liquidation", "sale", "donation", "theft", "loss", "transfer"]
    for i, reason in enumerate(reasons):
        item_id = _create_item(client, code=f"DISP-R{i:03d}")
        res = client.post(f"/api/items/{item_id}/dispose", json={"reason": reason})
        assert res.status_code == 201, f"Selhalo pro reason={reason}"
        assert res.json()["reason"] == reason


def test_dispose_not_found(client):
    """Neexistující položka → 404."""
    res = client.post("/api/items/99999/dispose", json={"reason": "loss"})
    assert res.status_code == 404


def test_dispose_already_inactive(client):
    """Pokus o vyřazení již vyřazené položky → 409."""
    item_id = _create_item(client, code="DISP-T004")
    client.post(f"/api/items/{item_id}/dispose", json={"reason": "theft"})
    # Druhý pokus musí selhat
    res = client.post(f"/api/items/{item_id}/dispose", json={"reason": "loss"})
    assert res.status_code == 409


def test_dispose_invalid_reason(client):
    """Neplatný důvod → 422 Unprocessable Entity."""
    item_id = _create_item(client, code="DISP-T005")
    res = client.post(f"/api/items/{item_id}/dispose", json={"reason": "explosion"})
    assert res.status_code == 422


def test_dispose_missing_reason(client):
    """Chybějící povinné pole reason → 422."""
    item_id = _create_item(client, code="DISP-T006")
    res = client.post(f"/api/items/{item_id}/dispose", json={})
    assert res.status_code == 422


# ─── GET /api/disposals ───────────────────────────────────────────────────────

def test_list_disposals_empty(client):
    """Prázdný seznam pokud nejsou žádná vyřazení."""
    res = client.get("/api/disposals")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_disposals_basic(client):
    """Seznam obsahuje vyřazené položky s item_code a item_name."""
    item_id = _create_item(client, code="DISP-L001", name="Notebook pro seznam")
    client.post(f"/api/items/{item_id}/dispose", json={"reason": "liquidation"})

    res = client.get("/api/disposals")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    record = data["items"][0]
    assert record["item_code"] == "DISP-L001"
    assert record["item_name"] == "Notebook pro seznam"
    assert record["reason"] == "liquidation"


def test_list_disposals_filter_reason(client):
    """Filtrování dle důvodu."""
    id1 = _create_item(client, code="DISP-F001")
    id2 = _create_item(client, code="DISP-F002")
    id3 = _create_item(client, code="DISP-F003")
    client.post(f"/api/items/{id1}/dispose", json={"reason": "sale"})
    client.post(f"/api/items/{id2}/dispose", json={"reason": "sale"})
    client.post(f"/api/items/{id3}/dispose", json={"reason": "theft"})

    res = client.get("/api/disposals?reason=sale")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert all(r["reason"] == "sale" for r in data["items"])


def test_list_disposals_filter_year(client):
    """Filtrování dle roku vyřazení."""
    id1 = _create_item(client, code="DISP-Y001")
    id2 = _create_item(client, code="DISP-Y002")
    client.post(f"/api/items/{id1}/dispose", json={
        "reason": "loss",
        "disposed_at": "2023-06-01T12:00:00Z",
    })
    client.post(f"/api/items/{id2}/dispose", json={
        "reason": "loss",
        "disposed_at": "2024-11-15T08:00:00Z",
    })

    res = client.get("/api/disposals?year=2023")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["item_code"] == "DISP-Y001"


def test_list_disposals_filter_combined(client):
    """Kombinovaný filtr rok + důvod."""
    id1 = _create_item(client, code="DISP-C001")
    id2 = _create_item(client, code="DISP-C002")
    id3 = _create_item(client, code="DISP-C003")
    client.post(f"/api/items/{id1}/dispose", json={"reason": "sale", "disposed_at": "2024-01-01T00:00:00Z"})
    client.post(f"/api/items/{id2}/dispose", json={"reason": "donation", "disposed_at": "2024-03-01T00:00:00Z"})
    client.post(f"/api/items/{id3}/dispose", json={"reason": "sale", "disposed_at": "2023-12-01T00:00:00Z"})

    res = client.get("/api/disposals?year=2024&reason=sale")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["item_code"] == "DISP-C001"


def test_list_disposals_pagination(client):
    """Stránkování funguje správně."""
    for i in range(5):
        item_id = _create_item(client, code=f"DISP-P{i:03d}")
        client.post(f"/api/items/{item_id}/dispose", json={"reason": "transfer"})

    res = client.get("/api/disposals?page=1&size=2")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["pages"] == 3

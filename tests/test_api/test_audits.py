"""API testy pro inventury — scan idempotence, lifecycle."""


def test_create_audit(client):
    res = client.post("/api/audits", json={"name": "Inventura Q1"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Inventura Q1"
    assert data["status"] == "open"


def test_list_audits(client):
    client.post("/api/audits", json={"name": "Audit 1"})
    client.post("/api/audits", json={"name": "Audit 2"})
    res = client.get("/api/audits")
    assert res.status_code == 200
    assert res.json()["total"] >= 2


def test_get_audit(client):
    r = client.post("/api/audits", json={"name": "Get Test"})
    audit_id = r.json()["id"]
    res = client.get(f"/api/audits/{audit_id}")
    assert res.status_code == 200
    assert res.json()["id"] == audit_id


def test_scan_item(client):
    r_item = client.post("/api/items", json={"code": "SCAN-001", "name": "Scanned Item"})
    item_id = r_item.json()["id"]
    r_audit = client.post("/api/audits", json={"name": "Scan Test Audit"})
    audit_id = r_audit.json()["id"]

    res = client.post(f"/api/audits/{audit_id}/scan", json={"item_id": item_id})
    assert res.status_code == 200
    assert res.json()["item_id"] == item_id
    assert res.json()["audit_id"] == audit_id


def test_scan_idempotent(client):
    """Skenování stejné položky 2× musí vrátit stejný výsledek (idempotentní)."""
    r_item = client.post("/api/items", json={"code": "IDEM-001", "name": "Idempotent"})
    item_id = r_item.json()["id"]
    r_audit = client.post("/api/audits", json={"name": "Idempotent Audit"})
    audit_id = r_audit.json()["id"]

    res1 = client.post(f"/api/audits/{audit_id}/scan", json={"item_id": item_id})
    res2 = client.post(f"/api/audits/{audit_id}/scan", json={"item_id": item_id})

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["id"] == res2.json()["id"]  # Same scan record!


def test_close_audit(client):
    r_audit = client.post("/api/audits", json={"name": "Close Test"})
    audit_id = r_audit.json()["id"]
    res = client.post(f"/api/audits/{audit_id}/close")
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_scan_closed_audit(client):
    r_item = client.post("/api/items", json={"code": "CLSD-001", "name": "Item"})
    item_id = r_item.json()["id"]
    r_audit = client.post("/api/audits", json={"name": "To Close"})
    audit_id = r_audit.json()["id"]
    client.post(f"/api/audits/{audit_id}/close")

    res = client.post(f"/api/audits/{audit_id}/scan", json={"item_id": item_id})
    assert res.status_code == 400


def test_audit_report(client):
    r_item = client.post("/api/items", json={"code": "RPT-001", "name": "Report Item"})
    item_id = r_item.json()["id"]
    r_audit = client.post("/api/audits", json={"name": "Report Audit"})
    audit_id = r_audit.json()["id"]
    client.post(f"/api/audits/{audit_id}/scan", json={"item_id": item_id})

    res = client.get(f"/api/audits/{audit_id}/report")
    assert res.status_code == 200
    data = res.json()
    assert data["scanned_count"] >= 1
    assert "missing_items" in data

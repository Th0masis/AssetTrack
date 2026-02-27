"""Testy exportů — PDF a Excel."""


def test_excel_export(client):
    client.post("/api/items", json={"code": "XLS-001", "name": "Excel Item"})
    res = client.get("/api/export/excel")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert len(res.content) > 0


def test_audit_pdf_export(client):
    r_item = client.post("/api/items", json={"code": "PDF-001", "name": "PDF Item"})
    item_id = r_item.json()["id"]
    r_audit = client.post("/api/audits", json={"name": "PDF Export Test"})
    audit_id = r_audit.json()["id"]
    client.post(f"/api/audits/{audit_id}/scan", json={"item_id": item_id})

    res = client.get(f"/api/export/pdf/{audit_id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 0


def test_qr_item_png(client):
    r = client.post("/api/items", json={"code": "QR-001", "name": "QR Item"})
    item_id = r.json()["id"]
    res = client.get(f"/api/qr/item/{item_id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content[:4] == b'\x89PNG'


def test_qr_location_png(client):
    r = client.post("/api/locations", json={"name": "QR Loc", "code": "QRLOC-001"})
    loc_id = r.json()["id"]
    res = client.get(f"/api/qr/location/{loc_id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"


def test_qr_batch_pdf(client):
    r1 = client.post("/api/items", json={"code": "BATCH-001", "name": "Batch 1"})
    r2 = client.post("/api/items", json={"code": "BATCH-002", "name": "Batch 2"})
    ids = f"{r1.json()['id']},{r2.json()['id']}"
    res = client.get(f"/api/qr/batch?ids={ids}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 0


def test_disposals_excel_export(client):
    """Excel export vyřazeného majetku — správný content-type a nenulový obsah."""
    r = client.post("/api/items", json={"code": "DXLS-001", "name": "Disposal Excel Item"})
    item_id = r.json()["id"]
    client.post(f"/api/items/{item_id}/dispose", json={"reason": "liquidation", "document_ref": "LIK-TEST"})

    res = client.get("/api/export/excel/disposals")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert "vyrazeny-majetek.xlsx" in res.headers["content-disposition"]
    assert len(res.content) > 0


def test_disposal_pdf_export(client):
    """PDF protokol o vyřazení — správný content-type, obsahuje PDF hlavičku."""
    r = client.post("/api/items", json={"code": "DPDF-001", "name": "Disposal PDF Item"})
    item_id = r.json()["id"]
    d = client.post(f"/api/items/{item_id}/dispose", json={
        "reason": "sale",
        "document_ref": "PROD-TEST-001",
        "note": "Testovací prodej",
    })
    disposal_id = d.json()["id"]

    res = client.get(f"/api/export/pdf/disposal/{disposal_id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content[:4] == b"%PDF"
    assert len(res.content) > 0


def test_disposal_pdf_not_found(client):
    """PDF protokol pro neexistující disposal → 404."""
    res = client.get("/api/export/pdf/disposal/99999")
    assert res.status_code == 404

"""API testy pro /api/items endpoint."""


def test_create_item(client):
    res = client.post("/api/items", json={"code": "IT-001", "name": "Notebook Dell"})
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "IT-001"
    assert data["name"] == "Notebook Dell"
    assert data["is_active"] is True
    assert "id" in data


def test_list_items(client):
    client.post("/api/items", json={"code": "IT-002", "name": "Monitor"})
    client.post("/api/items", json={"code": "IT-003", "name": "Klávesnice"})
    res = client.get("/api/items")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 2


def test_get_item(client):
    r = client.post("/api/items", json={"code": "IT-010", "name": "Test Item"})
    item_id = r.json()["id"]
    res = client.get(f"/api/items/{item_id}")
    assert res.status_code == 200
    assert res.json()["id"] == item_id


def test_get_item_not_found(client):
    res = client.get("/api/items/99999")
    assert res.status_code == 404


def test_update_item(client):
    r = client.post("/api/items", json={"code": "IT-020", "name": "Old Name"})
    item_id = r.json()["id"]
    res = client.put(f"/api/items/{item_id}", json={"name": "New Name"})
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"


def test_delete_item_soft(client):
    r = client.post("/api/items", json={"code": "IT-030", "name": "To Delete"})
    item_id = r.json()["id"]
    res = client.delete(f"/api/items/{item_id}")
    assert res.status_code == 200
    assert res.json()["is_active"] is False


def test_duplicate_code(client):
    client.post("/api/items", json={"code": "DUP-001", "name": "First"})
    res = client.post("/api/items", json={"code": "DUP-001", "name": "Second"})
    assert res.status_code == 409


def test_search_items(client):
    client.post("/api/items", json={"code": "SRCH-001", "name": "Searchable Item"})
    res = client.get("/api/items?search=Searchable")
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_item_history(client):
    r = client.post("/api/items", json={"code": "HIST-001", "name": "History Item"})
    item_id = r.json()["id"]
    res = client.get(f"/api/items/{item_id}/history")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

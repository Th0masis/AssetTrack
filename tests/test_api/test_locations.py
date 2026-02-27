"""API testy pro /api/locations endpoint."""


def test_create_location(client):
    res = client.post("/api/locations", json={"name": "Serverovna", "code": "LOC-001", "building": "A", "floor": "1"})
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "LOC-001"
    assert data["is_active"] is True


def test_list_locations(client):
    client.post("/api/locations", json={"name": "Kancelář 1", "code": "L001"})
    client.post("/api/locations", json={"name": "Kancelář 2", "code": "L002"})
    res = client.get("/api/locations")
    assert res.status_code == 200
    assert res.json()["total"] >= 2


def test_get_location(client):
    r = client.post("/api/locations", json={"name": "Test Loc", "code": "TL-001"})
    loc_id = r.json()["id"]
    res = client.get(f"/api/locations/{loc_id}")
    assert res.status_code == 200
    assert res.json()["id"] == loc_id


def test_location_not_found(client):
    res = client.get("/api/locations/99999")
    assert res.status_code == 404


def test_update_location(client):
    r = client.post("/api/locations", json={"name": "Old", "code": "UPD-001"})
    loc_id = r.json()["id"]
    res = client.put(f"/api/locations/{loc_id}", json={"name": "Updated"})
    assert res.status_code == 200
    assert res.json()["name"] == "Updated"


def test_delete_location_soft(client):
    r = client.post("/api/locations", json={"name": "ToDelete", "code": "DEL-001"})
    loc_id = r.json()["id"]
    res = client.delete(f"/api/locations/{loc_id}")
    assert res.status_code == 200
    assert res.json()["is_active"] is False


def test_items_at_location(client):
    r_loc = client.post("/api/locations", json={"name": "Sklad", "code": "SKLAD-001"})
    loc_id = r_loc.json()["id"]
    r_item = client.post("/api/items", json={"code": "ITEM-AT-LOC", "name": "Test Item"})
    item_id = r_item.json()["id"]
    client.post("/api/moves", json={"item_id": item_id, "location_id": loc_id})
    res = client.get(f"/api/locations/{loc_id}/items")
    assert res.status_code == 200
    ids = [i["id"] for i in res.json()]
    assert item_id in ids

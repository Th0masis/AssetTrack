"""API testy pro /api/moves — append-only."""


def test_move_item(client):
    r_item = client.post("/api/items", json={"code": "MV-001", "name": "Movable Item"})
    item_id = r_item.json()["id"]
    r_loc = client.post("/api/locations", json={"name": "Lokace A", "code": "MV-LOC-A"})
    loc_id = r_loc.json()["id"]

    res = client.post("/api/moves", json={"item_id": item_id, "location_id": loc_id, "note": "První přesun"})
    assert res.status_code == 201
    data = res.json()
    assert data["item_id"] == item_id
    assert data["location_id"] == loc_id


def test_move_creates_new_assignment(client):
    """Přesun musí vždy vytvořit nový záznam, nikdy updatovat stávající."""
    r_item = client.post("/api/items", json={"code": "MV-002", "name": "Item2"})
    item_id = r_item.json()["id"]
    r_loc1 = client.post("/api/locations", json={"name": "Loc1", "code": "MV-L1"})
    r_loc2 = client.post("/api/locations", json={"name": "Loc2", "code": "MV-L2"})
    loc1_id = r_loc1.json()["id"]
    loc2_id = r_loc2.json()["id"]

    res1 = client.post("/api/moves", json={"item_id": item_id, "location_id": loc1_id})
    res2 = client.post("/api/moves", json={"item_id": item_id, "location_id": loc2_id})

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["id"] != res2.json()["id"]  # Different records!

    # History shows both
    history = client.get(f"/api/items/{item_id}/history").json()
    assert len(history) == 2


def test_move_invalid_item(client):
    r_loc = client.post("/api/locations", json={"name": "L", "code": "MV-ERR-LOC"})
    res = client.post("/api/moves", json={"item_id": 99999, "location_id": r_loc.json()["id"]})
    assert res.status_code == 404


def test_move_invalid_location(client):
    r_item = client.post("/api/items", json={"code": "MV-003", "name": "Item3"})
    res = client.post("/api/moves", json={"item_id": r_item.json()["id"], "location_id": 99999})
    assert res.status_code == 404

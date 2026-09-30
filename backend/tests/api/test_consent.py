def test_consent_request_status_respond(client):
    r = client.post("/consent/request", json={"identity_id": "ARMOR-001"})
    assert r.status_code == 200
    consent_id = r.json()["consent_id"]
    assert r.json()["status"] == "PENDING"

    r = client.get(f"/consent/status/{consent_id}")
    assert r.json()["status"] == "PENDING"

    r = client.post("/consent/respond", json={"consent_id": consent_id, "decision": "APPROVED"})
    assert r.json()["status"] == "GRANTED"

    r = client.get(f"/consent/status/{consent_id}")
    assert r.json()["status"] == "GRANTED"


def test_consent_status_unknown_id_404(client):
    r = client.get("/consent/status/NOPE-999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_consent_respond_invalid_decision(client):
    cid = client.post("/consent/request", json={"identity_id": "ARMOR-001"}).json()["consent_id"]
    r = client.post("/consent/respond", json={"consent_id": cid, "decision": "maybe"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_CONSENT_DECISION"

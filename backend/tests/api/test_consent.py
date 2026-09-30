import base64

import pytest

from app.ai.identity_client import identity_ai_client

IMG = base64.b64encode(b"fake").decode()


@pytest.fixture()
def owner_and_requester(client, make_user, monkeypatch):
    # Fase 1: consent is owner-answered and requires login on both sides.
    monkeypatch.setattr(identity_ai_client, "embed", lambda _b: None)
    owner_h, _ = make_user("owner@example.com")
    requester_h, _ = make_user("requester@example.com")
    client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-001", "image": IMG}, headers=owner_h
    )
    return owner_h, requester_h


def test_consent_request_status_respond(client, owner_and_requester):
    owner_h, requester_h = owner_and_requester
    r = client.post("/consent/request", json={"identity_id": "ARMOR-001"}, headers=requester_h)
    assert r.status_code == 200
    consent_id = r.json()["consent_id"]
    assert r.json()["status"] == "PENDING"

    r = client.get(f"/consent/status/{consent_id}", headers=requester_h)
    assert r.json()["status"] == "PENDING"

    r = client.post(
        "/consent/respond",
        json={"consent_id": consent_id, "decision": "APPROVED"},
        headers=owner_h,
    )
    assert r.json()["status"] == "GRANTED"

    r = client.get(f"/consent/status/{consent_id}", headers=requester_h)
    assert r.json()["status"] == "GRANTED"


def test_consent_status_unknown_id_404(client, owner_and_requester):
    _, requester_h = owner_and_requester
    r = client.get("/consent/status/NOPE-999", headers=requester_h)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_consent_respond_invalid_decision(client, owner_and_requester):
    owner_h, requester_h = owner_and_requester
    cid = client.post(
        "/consent/request", json={"identity_id": "ARMOR-001"}, headers=requester_h
    ).json()["consent_id"]
    r = client.post(
        "/consent/respond", json={"consent_id": cid, "decision": "maybe"}, headers=owner_h
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_CONSENT_DECISION"

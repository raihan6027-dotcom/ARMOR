"""Consent lapis 2 via request_id (Fase 3): the requester never names an identity."""

import pytest

from app.db.database import SessionLocal
from app.models.consent import Consent
from tests.synthetic import face, image

AD = "Buat iklan produk kopi dengan wajah orang ini."


@pytest.fixture()
def people(make_user, enroll):
    raka_h, _ = make_user("raka@example.com")  # owner B in the scenarios
    dimas_h, dimas_id = make_user("dimas@example.com")  # requester A
    raka_id = enroll(raka_h, "raka")
    return {"owner": raka_h, "owner_id": raka_id, "req": dimas_h, "req_id": dimas_id}


def _review_request(client, headers, who="raka"):
    r = client.post("/requests", json={"prompt": AD, "image": image(face(who))}, headers=headers)
    assert r.json()["decision"]["action"] == "REVIEW"
    return r.json()["request_id"]


def test_scenario_4_consent_turns_review_into_allow(client, people):
    request_id = _review_request(client, people["req"])
    r = client.post("/consent/request", json={"request_id": request_id}, headers=people["req"])
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING"

    inbox = client.get("/consent/inbox", headers=people["owner"]).json()["items"]
    assert len(inbox) == 1
    item = inbox[0]
    assert (item["requester_email"], item["intent"], item["media"], item["prompt"]) == (
        "dimas@example.com",
        "COMMERCIAL_USE",
        "FACE",
        AD,
    )
    r = client.post(
        "/consent/respond",
        json={"consent_id": item["consent_id"], "decision": "APPROVED"},
        headers=people["owner"],
    )
    assert r.json()["status"] == "GRANTED"
    status = client.get(f"/consent/request/{request_id}", headers=people["req"]).json()
    assert status["status"] == "GRANTED"

    again = client.post(
        "/requests", json={"prompt": AD, "image": image(face("raka"))}, headers=people["req"]
    )
    assert again.json()["decision"]["action"] == "ALLOW"

    # Consent is scoped: a political poster is a different purpose.
    politics = client.post(
        "/requests",
        json={"prompt": "Buat poster kampanye pemilu orang ini.", "image": image(face("raka"))},
        headers=people["req"],
    )
    assert politics.json()["decision"]["action"] == "REVIEW"


def test_scenario_5_consent_denied_turns_review_into_deny(client, people):
    request_id = _review_request(client, people["req"])
    client.post("/consent/request", json={"request_id": request_id}, headers=people["req"])
    cid = client.get("/consent/inbox", headers=people["owner"]).json()["items"][0]["consent_id"]
    client.post(
        "/consent/respond", json={"consent_id": cid, "decision": "DENIED"}, headers=people["owner"]
    )
    assert (
        client.get(f"/consent/request/{request_id}", headers=people["req"]).json()["status"]
        == "DENIED"
    )
    again = client.post(
        "/requests", json={"prompt": AD, "image": image(face("raka"))}, headers=people["req"]
    ).json()
    assert again["decision"]["action"] == "DENY"
    assert again["decision"]["reason_code"] == "NOT_PERMITTED"


def test_consent_request_response_is_the_same_for_unregistered(client, people):
    registered = _review_request(client, people["req"], "raka")
    unregistered = _review_request(client, people["req"], "citra")
    a = client.post("/consent/request", json={"request_id": registered}, headers=people["req"])
    b = client.post("/consent/request", json={"request_id": unregistered}, headers=people["req"])
    assert a.status_code == b.status_code == 200
    assert {k: v for k, v in a.json().items() if k != "request_id"} == {
        k: v for k, v in b.json().items() if k != "request_id"
    }
    with SessionLocal() as db:
        assert db.query(Consent).count() == 1  # only the registered owner was asked


def test_consent_request_is_not_duplicated(client, people):
    request_id = _review_request(client, people["req"])
    for _ in range(2):
        client.post("/consent/request", json={"request_id": request_id}, headers=people["req"])
    with SessionLocal() as db:
        assert db.query(Consent).count() == 1


def test_consent_only_for_own_review_requests(client, people):
    request_id = _review_request(client, people["req"])
    r = client.post("/consent/request", json={"request_id": request_id}, headers=people["owner"])
    assert r.status_code == 404  # not your request
    allowed = client.post(
        "/requests",
        json={"prompt": "buat avatar kartun saya", "image": image(face("raka"))},
        headers=people["owner"],
    ).json()
    r = client.post(
        "/consent/request", json={"request_id": allowed["request_id"]}, headers=people["owner"]
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONSENT_NOT_APPLICABLE"


def test_inbox_filter_and_owner_only_status(client, people):
    request_id = _review_request(client, people["req"])
    client.post("/consent/request", json={"request_id": request_id}, headers=people["req"])
    assert (
        len(client.get("/consent/inbox?status=pending", headers=people["owner"]).json()["items"])
        == 1
    )
    assert (
        client.get("/consent/inbox?status=answered", headers=people["owner"]).json()["items"] == []
    )
    assert client.get("/consent/inbox", headers=people["req"]).json()["items"] == []
    cid = client.get("/consent/inbox", headers=people["owner"]).json()["items"][0]["consent_id"]
    assert client.get(f"/consent/status/{cid}", headers=people["owner"]).status_code == 200
    assert client.get(f"/consent/status/{cid}", headers=people["req"]).status_code == 404


def test_consent_status_unknown_id_404(client, people):
    r = client.get("/consent/status/NOPE-999", headers=people["owner"])
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_consent_respond_invalid_decision(client, people):
    request_id = _review_request(client, people["req"])
    client.post("/consent/request", json={"request_id": request_id}, headers=people["req"])
    cid = client.get("/consent/inbox", headers=people["owner"]).json()["items"][0]["consent_id"]
    r = client.post(
        "/consent/respond", json={"consent_id": cid, "decision": "maybe"}, headers=people["owner"]
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_CONSENT_DECISION"

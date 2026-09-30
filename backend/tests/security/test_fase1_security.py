"""Fase 1: regression tests for the ten proven security holes.

Each test reproduces an attack from docs/PROMPTS.md Fase 1. They were written
before the fixes and failed against the original code (see
docs/eval/security-fase1.md for the before/after table).
"""

import base64
import uuid

import numpy as np
import pytest

from app.ai.identity_client import identity_ai_client
from app.db.database import SessionLocal
from app.models.consent import Consent
from app.models.request import Request

IMG = base64.b64encode(b"fake-image").decode()
VEC = np.ones(512, dtype=np.float32)


@pytest.fixture(autouse=True)
def _fake_face(monkeypatch):
    # Every image "contains" the same face so matching is deterministic offline.
    monkeypatch.setattr(identity_ai_client, "embed", lambda _b: VEC)


@pytest.fixture()
def accounts(client, make_user):
    owner_h, owner_id = make_user("owner-b@example.com")
    attacker_h, attacker_id = make_user("attacker@example.com")
    r = client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-B", "image": IMG}, headers=owner_h
    )
    assert r.status_code == 200
    return {"owner": owner_h, "owner_id": owner_id, "atk": attacker_h, "atk_id": attacker_id}


# 1 -----------------------------------------------------------------------------
def test_1_cannot_reenroll_someone_elses_identity(client, accounts):
    r = client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-B", "image": IMG}, headers=accounts["atk"]
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"

    # The attacker must still be treated as OTHER, never SELF, so no silent ALLOW.
    r = client.post(
        "/requests",
        json={"identity_id": "ARMOR-B", "prompt": "Buatkan avatar kartun dari wajah ini."},
        headers=accounts["atk"],
    )
    assert r.json()["identity"]["target"] == "OTHER"
    assert r.json()["decision"]["action"] != "ALLOW"


# 2 -----------------------------------------------------------------------------
def test_2_cannot_change_or_read_someone_elses_permissions(client, accounts):
    r = client.post(
        "/permissions",
        json={"identity_id": "ARMOR-B", "action": "commercial_use", "decision": "ALLOW"},
        headers=accounts["atk"],
    )
    assert r.status_code == 403
    r = client.get("/permissions", params={"identity_id": "ARMOR-B"}, headers=accounts["atk"])
    assert r.status_code == 403
    # Owner's permissions are unchanged.
    perms = client.get("/permissions", params={"identity_id": "ARMOR-B"}, headers=accounts["owner"])
    assert perms.json()["permissions"]["commercial_use"] == "REVIEW"


# 3 -----------------------------------------------------------------------------
def test_3a_consent_request_requires_login_and_takes_requester_from_token(client, accounts):
    r = client.post("/consent/request", json={"identity_id": "ARMOR-B"})
    assert r.status_code == 401

    r = client.post(
        "/consent/request",
        json={"identity_id": "ARMOR-B", "requester_id": "SPOOFED-USER"},
        headers=accounts["atk"],
    )
    assert r.status_code == 200
    with SessionLocal() as db:
        row = db.query(Consent).filter(Consent.consent_id == r.json()["consent_id"]).one()
        assert row.requester_id == accounts["atk_id"]


def test_3b_only_owner_can_respond_to_consent(client, accounts):
    cid = client.post(
        "/consent/request", json={"identity_id": "ARMOR-B"}, headers=accounts["atk"]
    ).json()["consent_id"]

    r = client.post("/consent/respond", json={"consent_id": cid, "decision": "APPROVED"})
    assert r.status_code == 401
    r = client.post(
        "/consent/respond",
        json={"consent_id": cid, "decision": "APPROVED"},
        headers=accounts["atk"],
    )
    assert r.status_code == 403
    r = client.post(
        "/consent/respond",
        json={"consent_id": cid, "decision": "DENIED"},
        headers=accounts["owner"],
    )
    assert r.status_code == 200
    assert r.json()["status"] == "DENIED"


# 4 -----------------------------------------------------------------------------
def test_4_identity_lock_is_enforced_by_policy(client, accounts):
    r = client.post("/identity/lock", json={"identity_id": "ARMOR-B"}, headers=accounts["owner"])
    assert r.status_code == 200
    r = client.post(
        "/requests",
        json={"identity_id": "ARMOR-B", "prompt": "Edit ringan foto ini, perbaiki pencahayaan."},
        headers=accounts["atk"],
    )
    assert r.json()["decision"]["action"] == "DENY"
    with SessionLocal() as db:
        row = db.query(Request).filter(Request.request_id == r.json()["request_id"]).one()
        assert row.reason_code == "IDENTITY_LOCKED"  # detail kept for owner/audit only


# 5 -----------------------------------------------------------------------------
def test_5_history_and_logs_only_show_own_requests(client, accounts):
    client.post(
        "/requests",
        json={"identity_id": "ARMOR-B", "prompt": "buat avatar kartun"},
        headers=accounts["owner"],
    )
    for path in ("/requests", "/logs"):
        r = client.get(path, headers=accounts["atk"])
        assert r.status_code == 200
        assert r.json()["total"] == 0, path
    assert client.get("/requests", headers=accounts["owner"]).json()["total"] == 1


# 6 -----------------------------------------------------------------------------
def test_6_ids_are_uuids_and_do_not_collide_after_deletion(client, accounts):
    ids = []
    for _ in range(2):
        r = client.post(
            "/requests",
            json={"identity_id": "X", "prompt": "buat avatar kartun"},
            headers=accounts["owner"],
        )
        assert r.status_code == 200
        ids.append(r.json()["request_id"])
    # Deleting a row made the old count-based generator reissue an existing id.
    with SessionLocal() as db:
        db.query(Request).filter(Request.request_id == ids[0]).delete()
        db.commit()
    r = client.post(
        "/requests",
        json={"identity_id": "X", "prompt": "buat avatar kartun"},
        headers=accounts["owner"],
    )
    assert r.status_code == 200
    ids.append(r.json()["request_id"])
    assert len(set(ids)) == 3

    cid = client.post(
        "/consent/request", json={"identity_id": "ARMOR-B"}, headers=accounts["atk"]
    ).json()["consent_id"]
    for value in (*ids, cid, accounts["owner_id"], accounts["atk_id"]):
        uuid.UUID(value)  # raises ValueError if not a UUID


# 7 -----------------------------------------------------------------------------
def test_7_verify_is_not_an_identity_checking_oracle(client, accounts):
    r = client.post(
        "/identity/verify", json={"identity_id": "ARMOR-B", "image": IMG}, headers=accounts["atk"]
    )
    assert r.status_code == 404
    assert "confidence" not in r.text


# 8 -----------------------------------------------------------------------------
def test_8_profile_of_another_user_is_not_readable(client, accounts):
    r = client.get("/identity/profile", params={"identity_id": "ARMOR-B"}, headers=accounts["atk"])
    assert r.status_code == 404


# 9 -----------------------------------------------------------------------------
def test_9_lock_cannot_claim_an_unregistered_identity_id(client, accounts, make_user):
    r = client.post("/identity/lock", json={"identity_id": "ARMOR-NEW"}, headers=accounts["atk"])
    assert r.status_code == 404
    # The id stays free for its real owner.
    real_h, _ = make_user("real-new@example.com")
    r = client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-NEW", "image": IMG}, headers=real_h
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"


def test_9b_lock_of_someone_elses_identity_is_forbidden(client, accounts):
    r = client.post("/identity/lock", json={"identity_id": "ARMOR-B"}, headers=accounts["atk"])
    assert r.status_code == 403


# 10 ----------------------------------------------------------------------------
def test_10_requester_response_does_not_leak_target_details(client, accounts):
    prompt = "Buat video orang ini sedang mempromosikan produk kopi."
    registered = client.post(
        "/requests", json={"identity_id": "ARMOR-B", "prompt": prompt}, headers=accounts["atk"]
    ).json()
    unregistered = client.post(
        "/requests",
        json={"identity_id": "ARMOR-NOBODY", "prompt": prompt},
        headers=accounts["atk"],
    ).json()

    for body in (registered, unregistered):
        ident = body["identity"]
        assert "match_score" not in ident
        assert "identity_id" not in ident
        assert "verified" not in ident
    assert "ARMOR-B" not in str(registered)
    # Registered vs unregistered must look identical to the requester.
    assert registered["decision"] == unregistered["decision"]
    history = client.get("/requests", headers=accounts["atk"]).json()["items"]
    assert all("identity_id" not in item for item in history)

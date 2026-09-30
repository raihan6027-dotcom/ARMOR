"""Fase 1: regression tests for the ten proven security holes.

Written before the Fase 1 fixes and shown to fail against the original code (see
docs/eval/security-fase1.md). Updated in Fase 3 for the opt-in identity API
(identity ids are created by the server and never accepted from requesters),
keeping every attack: the attacker still tries each hole with the ids and faces
they can get hold of.
"""

import uuid

import pytest

from app.db.database import SessionLocal
from app.models.identity import Identity
from app.models.request import Request
from app.models.request_target import RequestTarget
from tests.synthetic import enroll_images, face, image

CONSENT = {"agreed": True, "text_version": "face-v1"}
AD = "Buat iklan produk kopi dengan wajah ini."


@pytest.fixture()
def accounts(make_user, enroll):
    owner_h, owner_id = make_user("owner-b@example.com")
    attacker_h, attacker_id = make_user("attacker@example.com")
    identity_id = enroll(owner_h, "sinta")
    return {
        "owner": owner_h,
        "owner_id": owner_id,
        "atk": attacker_h,
        "atk_id": attacker_id,
        "B": identity_id,
    }


def _review_request(client, headers):
    r = client.post(
        "/requests", json={"prompt": AD, "image": image(face("sinta"))}, headers=headers
    )
    return r.json()["request_id"]


# 1 -----------------------------------------------------------------------------
def test_1_cannot_take_over_someone_elses_identity(client, accounts):
    # Enrolling B's face from another account is refused (one identity per face).
    r = client.post(
        "/identity/enroll",
        json={"images": enroll_images("sinta"), "consent": CONSENT},
        headers=accounts["atk"],
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "FACE_ALREADY_REGISTERED"
    with SessionLocal() as db:
        owner = db.query(Identity).filter_by(identity_id=accounts["B"]).one().user_id
        assert owner == accounts["owner_id"]

    # The attacker is still OTHER for B's face, never SELF.
    r = client.post(
        "/requests", json={"prompt": AD, "image": image(face("sinta"))}, headers=accounts["atk"]
    )
    assert r.json()["identity"]["target"] == "OTHER"
    assert r.json()["decision"]["action"] != "ALLOW"
    with SessionLocal() as db:
        row = db.query(RequestTarget).filter_by(request_id=r.json()["request_id"]).one()
        assert row.target_type == "OTHER_REGISTERED"


# 2 -----------------------------------------------------------------------------
def test_2_cannot_change_or_read_someone_elses_permissions(client, accounts):
    r = client.post(
        "/permissions",
        json={
            "identity_id": accounts["B"],
            "intent": "COMMERCIAL_USE",
            "media": "FACE",
            "decision": "ALLOW",
        },
        headers=accounts["atk"],
    )
    assert r.status_code == 403
    r = client.get("/permissions", params={"identity_id": accounts["B"]}, headers=accounts["atk"])
    assert r.status_code == 403
    perms = client.get(
        "/permissions", params={"identity_id": accounts["B"]}, headers=accounts["owner"]
    )
    assert perms.json()["permissions"]["FACE"]["COMMERCIAL_USE"] == "REVIEW"


# 3 -----------------------------------------------------------------------------
def test_3a_consent_request_requires_login_and_is_bound_to_the_caller(client, accounts):
    request_id = _review_request(client, accounts["atk"])
    assert client.post("/consent/request", json={"request_id": request_id}).status_code == 401
    # Nobody can file a consent request on someone else's gateway request.
    r = client.post("/consent/request", json={"request_id": request_id}, headers=accounts["owner"])
    assert r.status_code == 404
    r = client.post("/consent/request", json={"request_id": request_id}, headers=accounts["atk"])
    assert r.status_code == 200


def test_3b_only_owner_can_respond_to_consent(client, accounts):
    request_id = _review_request(client, accounts["atk"])
    client.post("/consent/request", json={"request_id": request_id}, headers=accounts["atk"])
    cid = client.get("/consent/inbox", headers=accounts["owner"]).json()["items"][0]["consent_id"]

    # Fase 6: POST /consent/{id}/respond with an action.
    r = client.post(f"/consent/{cid}/respond", json={"action": "APPROVE"})
    assert r.status_code == 401
    r = client.post(f"/consent/{cid}/respond", json={"action": "APPROVE"}, headers=accounts["atk"])
    assert r.status_code == 403
    r = client.post(f"/consent/{cid}/respond", json={"action": "DENY"}, headers=accounts["owner"])
    assert r.status_code == 200
    assert r.json()["status"] == "DENIED"


# 4 -----------------------------------------------------------------------------
def test_4_identity_lock_is_enforced_by_policy(client, accounts):
    r = client.post(
        "/identity/lock", json={"identity_id": accounts["B"]}, headers=accounts["owner"]
    )
    assert r.status_code == 200
    r = client.post(
        "/requests",
        json={
            "prompt": "Edit ringan foto ini, perbaiki pencahayaan.",
            "image": image(face("sinta")),
        },
        headers=accounts["atk"],
    )
    assert r.json()["decision"]["action"] == "DENY"
    with SessionLocal() as db:
        row = db.query(Request).filter(Request.request_id == r.json()["request_id"]).one()
        assert row.reason_code == "IDENTITY_LOCKED"  # detail kept for owner/audit only


# 5 -----------------------------------------------------------------------------
def test_5_history_and_logs_only_show_own_requests(client, accounts):
    client.post("/requests", json={"prompt": "buat avatar kartun"}, headers=accounts["owner"])
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
            "/requests", json={"prompt": "buat avatar kartun"}, headers=accounts["owner"]
        )
        assert r.status_code == 200
        ids.append(r.json()["request_id"])
    # Deleting a row made the old count-based generator reissue an existing id.
    with SessionLocal() as db:
        db.query(Request).filter(Request.request_id == ids[0]).delete()
        db.commit()
    r = client.post("/requests", json={"prompt": "buat avatar kartun"}, headers=accounts["owner"])
    assert r.status_code == 200
    ids.append(r.json()["request_id"])
    assert len(set(ids)) == 3

    request_id = _review_request(client, accounts["atk"])
    client.post("/consent/request", json={"request_id": request_id}, headers=accounts["atk"])
    cid = client.get("/consent/inbox", headers=accounts["owner"]).json()["items"][0]["consent_id"]
    for value in (*ids, cid, accounts["owner_id"], accounts["atk_id"], accounts["B"]):
        uuid.UUID(value)  # raises ValueError if not a UUID


# 7 -----------------------------------------------------------------------------
def test_7_verify_is_not_an_identity_checking_oracle(client, accounts):
    r = client.post(
        "/identity/verify",
        json={"identity_id": accounts["B"], "image": image(face("sinta"))},
        headers=accounts["atk"],
    )
    assert r.status_code == 404
    assert "score" not in r.text


# 8 -----------------------------------------------------------------------------
def test_8_profile_of_another_user_is_not_readable(client, accounts):
    r = client.get(
        "/identity/profile", params={"identity_id": accounts["B"]}, headers=accounts["atk"]
    )
    assert r.status_code == 404


# 9 -----------------------------------------------------------------------------
def test_9_lock_cannot_claim_an_unregistered_identity_id(client, accounts):
    unused = str(uuid.uuid4())
    r = client.post("/identity/lock", json={"identity_id": unused}, headers=accounts["atk"])
    assert r.status_code == 404
    with SessionLocal() as db:
        assert db.query(Identity).filter_by(identity_id=unused).count() == 0


def test_9b_lock_of_someone_elses_identity_is_forbidden(client, accounts):
    r = client.post("/identity/lock", json={"identity_id": accounts["B"]}, headers=accounts["atk"])
    assert r.status_code == 403


# 10 ----------------------------------------------------------------------------
def test_10_requester_response_does_not_leak_target_details(client, accounts):
    registered = client.post(
        "/requests", json={"prompt": AD, "image": image(face("sinta"))}, headers=accounts["atk"]
    ).json()
    unregistered = client.post(
        "/requests", json={"prompt": AD, "image": image(face("citra"))}, headers=accounts["atk"]
    ).json()

    for body in (registered, unregistered):
        text = str(body["identity"])
        for leak in ("identity_id", "score", "verified", "REGISTERED"):
            assert leak not in text
    assert accounts["B"] not in str(registered)
    # Registered vs unregistered must look identical to the requester.
    for key in ("identity", "decision"):
        assert registered[key] == unregistered[key]
    history = client.get("/requests", headers=accounts["atk"]).json()["items"]
    assert all("identity_id" not in item for item in history)

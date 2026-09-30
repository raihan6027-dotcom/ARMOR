"""Consent lapis 2 (Fase 3 + 6): request per request_id, owner inbox, answers with
scope and validity, automatic re-evaluation, single use, expiry, revoke, block,
and the per-day rate limit."""

from datetime import timedelta

import pytest

from app.core.timeutil import now
from app.db.database import SessionLocal
from app.models.consent import Consent
from app.models.request import Request
from tests.synthetic import face, image

AD = "Buat iklan produk kopi dengan wajah orang ini."


@pytest.fixture()
def people(make_user, enroll):
    raka_h, _ = make_user("raka@example.com")  # owner (B in the scenarios)
    dimas_h, dimas_id = make_user("dimas@example.com")  # requester (A)
    raka_id = enroll(raka_h, "raka")
    return {"owner": raka_h, "owner_id": raka_id, "req": dimas_h, "req_id": dimas_id}


def _ask(client, headers, prompt=AD, who="raka"):
    r = client.post(
        "/requests", json={"prompt": prompt, "image": image(face(who))}, headers=headers
    )
    return r.json()


def _review_and_request_consent(client, people, prompt=AD):
    req = _ask(client, people["req"], prompt)
    assert req["decision"]["action"] == "REVIEW"
    assert req["status"] == "HELD"
    r = client.post(
        "/consent/request", json={"request_id": req["request_id"]}, headers=people["req"]
    )
    assert r.status_code == 200, r.text
    cid = client.get("/consent/inbox", headers=people["owner"]).json()["items"][0]["consent_id"]
    return req["request_id"], cid


def _answer(client, people, cid, **body):
    return client.post(f"/consent/{cid}/respond", json=body, headers=people["owner"])


# --- Scenario 4 and 5 (Lampiran A) -------------------------------------------------


def test_scenario_4_approval_releases_the_held_request_automatically(client, people):
    request_id, cid = _review_and_request_consent(client, people)
    inbox = client.get("/consent/inbox", headers=people["owner"]).json()
    assert inbox["pending"] == 1
    item = inbox["items"][0]
    assert (item["requester_email"], item["intent"], item["media"], item["prompt"]) == (
        "dimas@example.com",
        "COMMERCIAL_USE",
        "FACE",
        AD,
    )
    r = _answer(client, people, cid, action="APPROVE", validity="DAYS_7")
    assert r.status_code == 200
    assert (r.json()["status"], r.json()["state"], r.json()["validity"]) == (
        "GRANTED",
        "GRANTED",
        "DAYS_7",
    )
    # The held request changed to ALLOW without being sent again.
    detail = client.get(f"/requests/{request_id}", headers=people["req"]).json()
    assert (detail["status"], detail["decision"]["action"]) == ("FINAL", "ALLOW")
    assert (
        client.get(f"/consent/request/{request_id}", headers=people["req"]).json()["status"]
        == "GRANTED"
    )
    kinds = [n["kind"] for n in client.get("/notifications", headers=people["req"]).json()["items"]]
    assert {"CONSENT_ANSWERED", "REQUEST_UPDATED"} <= set(kinds)

    # A 7-day consent also covers a new request for the same purpose...
    assert _ask(client, people["req"])["decision"]["action"] == "ALLOW"
    # ...but not another purpose.
    assert (
        _ask(client, people["req"], "Buat poster kampanye pemilu orang ini.")["decision"]["action"]
        == "REVIEW"
    )


def test_scenario_5_denial_turns_the_held_request_into_deny(client, people):
    request_id, cid = _review_and_request_consent(client, people)
    _answer(client, people, cid, action="DENY")
    detail = client.get(f"/requests/{request_id}", headers=people["req"]).json()
    assert detail["decision"]["action"] == "DENY"
    assert detail["decision"]["reason_code"] == "NOT_PERMITTED"  # never "consent denied"
    assert (
        client.get(f"/consent/request/{request_id}", headers=people["req"]).json()["status"]
        == "DENIED"
    )


# --- Validity -------------------------------------------------------------------------


def test_single_use_consent_is_spent_by_the_first_allow(client, people):
    request_id, cid = _review_and_request_consent(client, people)
    _answer(client, people, cid, action="APPROVE", validity="ONCE")
    assert (
        client.get(f"/requests/{request_id}", headers=people["req"]).json()["decision"]["action"]
        == "ALLOW"
    )
    state = client.get(f"/consent/{cid}", headers=people["owner"]).json()["state"]
    assert state == "USED"
    assert _ask(client, people["req"])["decision"]["action"] == "REVIEW"


def test_expired_consent_counts_as_none(client, people):
    _, cid = _review_and_request_consent(client, people)
    _answer(client, people, cid, action="APPROVE", validity="DAYS_1")
    assert _ask(client, people["req"])["decision"]["action"] == "ALLOW"
    with SessionLocal() as db:
        c = db.query(Consent).filter_by(consent_id=cid).one()
        c.expires_at = now() - timedelta(minutes=1)
        db.commit()
    assert client.get(f"/consent/{cid}", headers=people["owner"]).json()["state"] == "EXPIRED"
    assert _ask(client, people["req"])["decision"]["action"] == "REVIEW"


def test_until_date_validity(client, people):
    _, cid = _review_and_request_consent(client, people)
    until = (now() + timedelta(days=3)).date().isoformat()
    r = _answer(client, people, cid, action="APPROVE", validity="UNTIL", until=until)
    assert r.status_code == 200
    assert r.json()["expires_at"].startswith((now() + timedelta(days=4)).date().isoformat())


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"action": "APPROVE", "validity": "UNTIL"}, "UNTIL_REQUIRED"),
        ({"action": "APPROVE", "validity": "UNTIL", "until": "2020-01-01"}, "UNTIL_IN_PAST"),
    ],
)
def test_invalid_until(client, people, body, code):
    _, cid = _review_and_request_consent(client, people)
    r = _answer(client, people, cid, **body)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == code


def test_owner_can_narrow_the_scope_when_approving(client, people):
    request_id, cid = _review_and_request_consent(client, people)
    # Approve only POLITICAL_USE: the commercial request stays held.
    r = _answer(client, people, cid, action="APPROVE", intent="POLITICAL_USE", validity="DAYS_1")
    assert r.json()["intent"] == "POLITICAL_USE"
    assert client.get(f"/requests/{request_id}", headers=people["req"]).json()["status"] == "HELD"


def test_revoke_granted_consent(client, people):
    _, cid = _review_and_request_consent(client, people)
    _answer(client, people, cid, action="APPROVE", validity="DAYS_30")
    assert _ask(client, people["req"])["decision"]["action"] == "ALLOW"
    r = client.post(f"/consent/{cid}/revoke", headers=people["owner"])
    assert r.json()["state"] == "REVOKED"
    assert _ask(client, people["req"])["decision"]["action"] == "REVIEW"
    assert client.post(f"/consent/{cid}/revoke", headers=people["req"]).status_code == 403


def test_revoke_only_granted(client, people):
    _, cid = _review_and_request_consent(client, people)
    r = client.post(f"/consent/{cid}/revoke", headers=people["owner"])
    assert r.status_code == 409


def test_answer_only_once(client, people):
    _, cid = _review_and_request_consent(client, people)
    _answer(client, people, cid, action="DENY")
    r = _answer(client, people, cid, action="APPROVE")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONSENT_ALREADY_ANSWERED"


# --- Block and rate limit --------------------------------------------------------------


def test_block_sender(client, people):
    _, cid = _review_and_request_consent(client, people)
    _answer(client, people, cid, action="BLOCK")
    req = _ask(client, people["req"], "Buat poster kampanye pemilu orang ini.")
    r = client.post(
        "/consent/request", json={"request_id": req["request_id"]}, headers=people["req"]
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "CONSENT_BLOCKED"


def test_rate_limit_three_per_identity_per_day(client, people):
    prompts = [
        "Buat poster kampanye pemilu orang ini.",
        "Buat iklan sepatu dengan orang ini.",
        "Buat parodi karikatur orang ini.",
        "Buat iklan minuman dengan orang ini.",
    ]
    codes = []
    for p in prompts:
        req = _ask(client, people["req"], p)
        assert req["decision"]["action"] == "REVIEW", p
        r = client.post(
            "/consent/request", json={"request_id": req["request_id"]}, headers=people["req"]
        )
        codes.append(r.status_code)
    assert codes == [200, 200, 200, 429]


# --- Uniform answers and access -----------------------------------------------------------


def test_consent_request_response_is_the_same_for_unregistered(client, people):
    registered = _ask(client, people["req"])["request_id"]
    unregistered = _ask(client, people["req"], who="citra")["request_id"]
    a = client.post("/consent/request", json={"request_id": registered}, headers=people["req"])
    b = client.post("/consent/request", json={"request_id": unregistered}, headers=people["req"])
    assert a.status_code == b.status_code == 200
    assert {k: v for k, v in a.json().items() if k != "request_id"} == {
        k: v for k, v in b.json().items() if k != "request_id"
    }
    with SessionLocal() as db:
        assert db.query(Consent).count() == 1  # only the registered owner was asked


def test_consent_request_is_not_duplicated(client, people):
    req = _ask(client, people["req"])
    for _ in range(2):
        client.post(
            "/consent/request", json={"request_id": req["request_id"]}, headers=people["req"]
        )
    with SessionLocal() as db:
        assert db.query(Consent).count() == 1


def test_consent_only_for_own_review_requests(client, people):
    req = _ask(client, people["req"])
    r = client.post(
        "/consent/request", json={"request_id": req["request_id"]}, headers=people["owner"]
    )
    assert r.status_code == 404
    allowed = _ask(client, people["owner"], "buat avatar kartun saya")
    r = client.post(
        "/consent/request", json={"request_id": allowed["request_id"]}, headers=people["owner"]
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONSENT_NOT_APPLICABLE"


def test_inbox_filter_and_owner_only_detail(client, people):
    _, cid = _review_and_request_consent(client, people)
    assert (
        len(client.get("/consent/inbox?status=pending", headers=people["owner"]).json()["items"])
        == 1
    )
    assert (
        client.get("/consent/inbox?status=answered", headers=people["owner"]).json()["items"] == []
    )
    assert client.get("/consent/inbox", headers=people["req"]).json()["items"] == []
    assert client.get(f"/consent/{cid}", headers=people["owner"]).status_code == 200
    assert client.get(f"/consent/{cid}", headers=people["req"]).status_code == 404
    notes = client.get("/notifications", headers=people["owner"]).json()
    assert notes["unread"] >= 1
    assert notes["items"][0]["kind"] == "CONSENT_REQUEST"


def test_consent_unknown_id_404(client, people):
    r = client.get("/consent/NOPE-999", headers=people["owner"])
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_consent_respond_invalid_action(client, people):
    _, cid = _review_and_request_consent(client, people)
    r = _answer(client, people, cid, action="maybe")
    assert r.status_code == 422


def test_request_row_keeps_original_intent_for_reevaluation(client, people):
    request_id, _ = _review_and_request_consent(client, people)
    with SessionLocal() as db:
        row = db.query(Request).filter_by(request_id=request_id).one()
        assert row.intent_original == "COMMERCIAL_USE"
        assert row.status == "HELD"

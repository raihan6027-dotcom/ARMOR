"""End-to-end orchestration through POST /requests (the ARMOR gateway).

Runs entirely on the deterministic fallback path (no Gemini key, no face model)
so the three canonical ARMOR scenarios are reproducible offline.
"""

import base64

import pytest

from app.ai.identity_client import identity_ai_client

IMG_B64 = base64.b64encode(b"fake").decode()


@pytest.fixture(autouse=True)
def _no_face_download(monkeypatch):
    # Enrollment must not trigger an InsightFace model download during tests.
    monkeypatch.setattr(identity_ai_client, "embed", lambda _b: None)


def test_scenario_a_self_personal_allow(client, auth):
    headers, _ = auth
    # Enroll an identity owned by the requester -> trusted SELF.
    client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-SELF", "image": IMG_B64}, headers=headers
    )

    r = client.post(
        "/requests",
        json={
            "identity_id": "ARMOR-SELF",
            "prompt": "Buatkan avatar kartun menggunakan wajah saya.",
        },
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["identity"]["target"] == "SELF"
    assert body["intent"]["label"] == "PERSONAL_CREATION"
    assert body["decision"]["action"] == "ALLOW"


def test_scenario_b_other_commercial_review(client, auth):
    headers, _ = auth
    r = client.post(
        "/requests",
        json={
            "identity_id": "ARMOR-OTHER",  # not owned by requester -> OTHER
            "prompt": "Buat video orang ini sedang mempromosikan produk X.",
        },
        headers=headers,
    )
    body = r.json()
    assert body["identity"]["target"] == "OTHER"
    assert body["intent"]["label"] == "COMMERCIAL_USE"
    assert body["risk"]["level"] == "MEDIUM"  # Fase 2 fallback, see test_intent_risk
    assert body["decision"]["action"] == "REVIEW"


def test_scenario_c_other_impersonation_deny(client, auth):
    headers, _ = auth
    r = client.post(
        "/requests",
        json={
            "identity_id": "ARMOR-OTHER-2",
            "prompt": "Buat video orang ini mengatakan sesuatu yang tidak pernah dia katakan.",
        },
        headers=headers,
    )
    body = r.json()
    assert body["intent"]["label"] == "IMPERSONATION"
    assert body["decision"]["action"] == "DENY"


def test_history_records_requests(client, auth):
    headers, _ = auth
    client.post(
        "/requests", json={"identity_id": "X", "prompt": "buat avatar kartun"}, headers=headers
    )
    client.post(
        "/requests", json={"identity_id": "Y", "prompt": "promosikan produk ini"}, headers=headers
    )
    r = client.get("/requests", headers=headers)
    body = r.json()
    assert body["total"] >= 2
    assert len(body["items"]) >= 2
    assert body["items"][0]["decision"] in ("ALLOW", "REVIEW", "DENY")


def test_requests_require_auth(client):
    r = client.post("/requests", json={"identity_id": "X", "prompt": "hi"})
    assert r.status_code == 401


def _enroll(client, headers, identity_id):
    client.post(
        "/identity/enroll", json={"identity_id": identity_id, "image": IMG_B64}, headers=headers
    )


AD = {"identity_id": "ARMOR-B", "prompt": "Buat iklan produk kopi dengan wajah orang ini."}


def test_consent_scope_turns_review_into_allow(client, make_user):
    # Lampiran A skenario 4 on the pre-Fase-3 gateway: A asks to use the face of B
    # in an ad -> REVIEW; B approves (scope COMMERCIAL_USE x FACE) -> ALLOW.
    b_h, _ = make_user("b@example.com")
    a_h, _ = make_user("a@example.com")
    _enroll(client, b_h, "ARMOR-B")

    assert client.post("/requests", json=AD, headers=a_h).json()["decision"]["action"] == "REVIEW"
    cid = client.post(
        "/consent/request",
        json={"identity_id": "ARMOR-B", "intent": "COMMERCIAL_USE", "media": "FACE"},
        headers=a_h,
    ).json()["consent_id"]
    client.post("/consent/respond", json={"consent_id": cid, "decision": "APPROVED"}, headers=b_h)
    assert client.post("/requests", json=AD, headers=a_h).json()["decision"]["action"] == "ALLOW"

    # Consent for one purpose does not carry over to another.
    politics = {"identity_id": "ARMOR-B", "prompt": "Buat poster kampanye pemilu orang ini."}
    r = client.post("/requests", json=politics, headers=a_h).json()
    assert r["decision"]["action"] == "REVIEW"


def test_consent_denied_turns_review_into_deny(client, make_user):
    # Lampiran A skenario 5.
    b_h, _ = make_user("b@example.com")
    a_h, _ = make_user("a@example.com")
    _enroll(client, b_h, "ARMOR-B")
    cid = client.post(
        "/consent/request",
        json={"identity_id": "ARMOR-B", "intent": "COMMERCIAL_USE"},
        headers=a_h,
    ).json()["consent_id"]
    client.post("/consent/respond", json={"consent_id": cid, "decision": "DENIED"}, headers=b_h)
    r = client.post("/requests", json=AD, headers=a_h).json()
    assert r["decision"]["action"] == "DENY"
    assert r["decision"]["reason_code"] == "NOT_PERMITTED"  # uniform: no "consent denied"


def test_requester_gets_safe_prompt_suggestion_on_deny(client, auth):
    # Lampiran A skenario 6.
    headers, _ = auth
    r = client.post(
        "/requests",
        json={
            "identity_id": "SOMEONE",
            "prompt": "Buat orang ini memakai baju tahanan dan diborgol.",
        },
        headers=headers,
    ).json()
    assert r["decision"]["action"] == "DENY"
    assert r["decision"]["reason_code"] == "HARMFUL_DEFAMATION"
    assert "tahanan" in r["decision"]["reason"]
    assert r["decision"]["suggestion"] == "Buat karikatur superhero dari foto ini."


def test_lock_commercial_political_blocks_ads_but_not_edits(client, make_user):
    b_h, _ = make_user("b@example.com")
    a_h, _ = make_user("a@example.com")
    _enroll(client, b_h, "ARMOR-B")
    client.post(
        "/identity/lock",
        json={"identity_id": "ARMOR-B", "level": "COMMERCIAL_POLITICAL", "media": "FACE"},
        headers=b_h,
    )
    assert client.post("/requests", json=AD, headers=a_h).json()["decision"]["action"] == "DENY"
    edit = {"identity_id": "ARMOR-B", "prompt": "Edit ringan, perbaiki pencahayaan foto ini."}
    assert client.post("/requests", json=edit, headers=a_h).json()["decision"]["action"] == "ALLOW"

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
    assert body["risk"]["level"] in ("HIGH", "CRITICAL")
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

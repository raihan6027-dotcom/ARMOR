import base64

import pytest

from app.ai.identity_client import identity_ai_client


@pytest.fixture(autouse=True)
def _owned_identity(client, auth, monkeypatch):
    # Fase 1: permissions are owner-only, so the caller first owns ARMOR-001.
    monkeypatch.setattr(identity_ai_client, "embed", lambda _b: None)
    headers, _ = auth
    img = base64.b64encode(b"fake").decode()
    client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-001", "image": img}, headers=headers
    )


def test_default_permissions(client, auth):
    headers, _ = auth
    r = client.get("/permissions", params={"identity_id": "ARMOR-001"}, headers=headers)
    assert r.status_code == 200
    perms = r.json()["permissions"]
    assert perms["personal_creation"] == "ALLOW"
    assert perms["impersonation"] == "DENY"
    assert perms["commercial_use"] == "REVIEW"


def test_override_permission(client, auth):
    headers, _ = auth
    r = client.post(
        "/permissions",
        json={"identity_id": "ARMOR-001", "action": "commercial_use", "decision": "ALLOW"},
        headers=headers,
    )
    assert r.status_code == 200

    r = client.get("/permissions", params={"identity_id": "ARMOR-001"}, headers=headers)
    assert r.json()["permissions"]["commercial_use"] == "ALLOW"


def test_permission_invalid_decision_422(client, auth):
    headers, _ = auth
    r = client.post(
        "/permissions",
        json={"identity_id": "ARMOR-001", "action": "commercial_use", "decision": "PERHAPS"},
        headers=headers,
    )
    assert r.status_code == 422


def test_permissions_require_auth(client):
    r = client.get("/permissions", params={"identity_id": "ARMOR-001"})
    assert r.status_code == 401

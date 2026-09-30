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
    # Fase 2: permissions are per intent x media (CLAUDE.md bagian 6).
    headers, _ = auth
    r = client.get("/permissions", params={"identity_id": "ARMOR-001"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    face, voice = body["permissions"]["FACE"], body["permissions"]["VOICE"]
    assert face["PERSONAL_CREATION"] == "ALLOW"
    assert face["IMPERSONATION"] == "DENY"
    assert face["COMMERCIAL_USE"] == "REVIEW"
    assert set(voice.values()) == {"DENY"}  # voice cloning defaults to DENY
    assert set(body["locked_intents"]) == {
        "IMPERSONATION",
        "DEFAMATION",
        "SEXUAL_EXPLICIT",
        "DECEPTIVE",
    }


def test_override_permission(client, auth):
    headers, _ = auth
    r = client.post(
        "/permissions",
        json={
            "identity_id": "ARMOR-001",
            "intent": "COMMERCIAL_USE",
            "media": "FACE",
            "decision": "ALLOW",
        },
        headers=headers,
    )
    assert r.status_code == 200

    r = client.get("/permissions", params={"identity_id": "ARMOR-001"}, headers=headers)
    perms = r.json()["permissions"]
    assert perms["FACE"]["COMMERCIAL_USE"] == "ALLOW"
    assert perms["VOICE"]["COMMERCIAL_USE"] == "DENY"  # media are independent


def test_harmful_intents_cannot_be_unlocked(client, auth):
    headers, _ = auth
    r = client.post(
        "/permissions",
        json={"identity_id": "ARMOR-001", "intent": "DEFAMATION", "decision": "ALLOW"},
        headers=headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INTENT_LOCKED"


def test_uncertain_is_not_a_permission(client, auth):
    headers, _ = auth
    r = client.post(
        "/permissions",
        json={"identity_id": "ARMOR-001", "intent": "UNCERTAIN", "decision": "ALLOW"},
        headers=headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_INTENT"


def test_permission_invalid_decision_422(client, auth):
    headers, _ = auth
    r = client.post(
        "/permissions",
        json={"identity_id": "ARMOR-001", "intent": "COMMERCIAL_USE", "decision": "PERHAPS"},
        headers=headers,
    )
    assert r.status_code == 422


def test_permissions_require_auth(client):
    r = client.get("/permissions", params={"identity_id": "ARMOR-001"})
    assert r.status_code == 401

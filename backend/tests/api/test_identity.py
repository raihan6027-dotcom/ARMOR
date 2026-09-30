import base64

import numpy as np
import pytest

from app.ai.identity_client import identity_ai_client

IMG_B64 = base64.b64encode(b"fake-image-bytes").decode()

VEC_A = np.zeros(512, dtype=np.float32)
VEC_A[:256] = 1.0
VEC_B = np.zeros(512, dtype=np.float32)
VEC_B[256:] = 1.0  # orthogonal to VEC_A


@pytest.fixture()
def face_model(monkeypatch):
    """Patch the embedder so tests never load/download InsightFace."""
    holder = {"vec": VEC_A}
    monkeypatch.setattr(identity_ai_client, "embed", lambda _b: holder["vec"])
    return holder


def test_enroll_then_verify_match(client, auth, face_model):
    headers, _ = auth
    r = client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-001", "image": IMG_B64}, headers=headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    r = client.post(
        "/identity/verify", json={"identity_id": "ARMOR-001", "image": IMG_B64}, headers=headers
    )
    body = r.json()
    assert body["match"] is True
    assert body["confidence"] >= 0.4


def test_verify_mismatch(client, auth, face_model):
    headers, _ = auth
    client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-001", "image": IMG_B64}, headers=headers
    )
    face_model["vec"] = VEC_B  # different face on verify
    r = client.post(
        "/identity/verify", json={"identity_id": "ARMOR-001", "image": IMG_B64}, headers=headers
    )
    assert r.json()["match"] is False


def test_verify_model_unavailable_is_not_a_match(client, auth, monkeypatch):
    headers, _ = auth
    monkeypatch.setattr(identity_ai_client, "embed", lambda _b: None)
    client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-002", "image": IMG_B64}, headers=headers
    )
    r = client.post(
        "/identity/verify", json={"identity_id": "ARMOR-002", "image": IMG_B64}, headers=headers
    )
    body = r.json()
    assert body["match"] is False
    assert body["ai_available"] is False


def test_profile_and_lock(client, auth, face_model):
    headers, _ = auth
    client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-003", "image": IMG_B64}, headers=headers
    )

    r = client.get("/identity/profile", params={"identity_id": "ARMOR-003"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["enrolled"] is True

    r = client.post("/identity/lock", json={"identity_id": "ARMOR-003"}, headers=headers)
    assert r.json()["status"] == "locked"


def test_identity_requires_auth(client):
    r = client.post("/identity/verify", json={"identity_id": "X", "image": IMG_B64})
    assert r.status_code == 401


def test_lock_level_per_media(client, auth, face_model):
    headers, _ = auth
    client.post(
        "/identity/enroll", json={"identity_id": "ARMOR-L", "image": IMG_B64}, headers=headers
    )
    r = client.post(
        "/identity/lock",
        json={"identity_id": "ARMOR-L", "level": "COMMERCIAL_POLITICAL", "media": "FACE"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["face_lock"], body["voice_lock"], body["status"]) == (
        "COMMERCIAL_POLITICAL",
        "NONE",
        "locked",
    )
    r = client.post(
        "/identity/lock",
        json={"identity_id": "ARMOR-L", "level": "ALL", "media": "VOICE"},
        headers=headers,
    )
    assert r.json()["voice_lock"] == "ALL"
    r = client.post(
        "/identity/lock", json={"identity_id": "ARMOR-L", "level": "NONE"}, headers=headers
    )
    body = r.json()
    assert (body["face_lock"], body["voice_lock"], body["status"]) == ("NONE", "NONE", "active")
    profile = client.get("/identity/profile", params={"identity_id": "ARMOR-L"}, headers=headers)
    assert profile.json()["face_lock"] == "NONE"

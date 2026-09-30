"""Fase 3: opt-in face enrollment, own-face verification, Lock, revoke, delete,
and data export. Uses the synthetic camera (tests/synthetic.py)."""

import numpy as np
import pytest

from app.core.crypto import decrypt_embedding
from app.db.database import SessionLocal
from app.models.biometric_consent import BiometricConsent
from app.models.case import Case
from app.models.identity import Identity
from tests.synthetic import enroll_images, face, image, person_vec

CONSENT = {"agreed": True, "text_version": "face-v1"}


def _enroll(client, headers, images, consent=CONSENT):
    return client.post(
        "/identity/enroll", json={"images": images, "consent": consent}, headers=headers
    )


# --- Enrollment ---------------------------------------------------------------


def test_enroll_three_poses_stores_only_encrypted_mean_embedding(client, auth):
    headers, user_id = auth
    r = _enroll(client, headers, enroll_images("raka"))
    assert r.status_code == 201
    identity_id = r.json()["identity_id"]
    with SessionLocal() as db:
        row = db.query(Identity).filter(Identity.identity_id == identity_id).one()
        assert row.user_id == user_id
        # Stored value is a Fernet token, not a readable vector.
        assert row.face_embedding.startswith("gAAAA")
        vec = decrypt_embedding(row.face_embedding)
        assert vec.shape == (512,)
        assert float(np.dot(vec, person_vec("raka"))) > 0.99
        # No column anywhere holds the photos.
        assert not any("image" in c.name or "photo" in c.name for c in Identity.__table__.columns)
        consent = db.query(BiometricConsent).filter_by(identity_id=identity_id).one()
        assert (consent.media, consent.text_version, consent.revoked_at) == (
            "FACE",
            "face-v1",
            None,
        )


def test_enroll_requires_explicit_consent(client, auth):
    headers, _ = auth
    r = _enroll(
        client, headers, enroll_images("raka"), {"agreed": False, "text_version": "face-v1"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "CONSENT_REQUIRED"
    with SessionLocal() as db:
        assert db.query(Identity).count() == 0


def test_enroll_rejects_outdated_consent_text(client, auth):
    headers, _ = auth
    r = _enroll(client, headers, enroll_images("raka"), {"agreed": True, "text_version": "face-v0"})
    assert r.json()["error"]["code"] == "CONSENT_TEXT_OUTDATED"
    assert r.json()["error"]["details"]["current_version"] == "face-v1"


def test_enroll_requires_exactly_three_captures(client, auth):
    headers, _ = auth
    assert _enroll(client, headers, enroll_images("raka")[:2]).status_code == 422


@pytest.mark.parametrize(
    ("bad_capture", "code"),
    [
        (image(), "FACE_NOT_FOUND"),
        (image(face("raka"), face("sinta")), "MULTIPLE_FACES"),
        (image(face("raka", size=30)), "FACE_QUALITY_LOW"),
        (image(face("raka", blur=5)), "FACE_QUALITY_LOW"),
        (image(face("raka", yaw=70)), "FACE_QUALITY_LOW"),
    ],
)
def test_enroll_rejects_bad_captures(client, auth, bad_capture, code):
    headers, _ = auth
    images = enroll_images("raka")
    images[1] = bad_capture
    r = _enroll(client, headers, images)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == code
    assert r.json()["error"]["details"]["capture"] == 1


def test_enroll_reports_quality_issues(client, auth):
    headers, _ = auth
    images = enroll_images("raka")
    images[0] = image(face("raka", size=20, blur=1))
    issues = _enroll(client, headers, images).json()["error"]["details"]["issues"]
    assert set(issues) == {"FACE_TOO_SMALL", "FACE_BLURRY"}


def test_enroll_rejects_captures_of_different_people(client, auth):
    headers, _ = auth
    images = [image(face("raka", yaw=-15)), image(face("raka")), image(face("sinta", yaw=15))]
    r = _enroll(client, headers, images)
    assert r.json()["error"]["code"] == "POSES_DIFFERENT_PERSON"


def test_enroll_rejects_three_identical_angles(client, auth):
    # A printed photo or a screen held still gives the same angle every time.
    headers, _ = auth
    r = _enroll(client, headers, enroll_images("raka", yaws=(0.0, 1.0, 2.0)))
    assert r.json()["error"]["code"] == "POSE_SPREAD_TOO_SMALL"


def test_face_already_registered_is_refused_and_opens_dispute(client, make_user, enroll):
    owner_h, _ = make_user("raka@example.com")
    identity_id = enroll(owner_h, "raka")
    impostor_h, impostor_id = make_user("impostor@example.com")
    r = _enroll(client, impostor_h, enroll_images("raka"))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "FACE_ALREADY_REGISTERED"
    case_id = r.json()["error"]["details"]["case_id"]
    with SessionLocal() as db:
        case = db.query(Case).filter_by(case_id=case_id).one()
        assert (case.kind, case.status, case.reporter_id, case.identity_id) == (
            "DISPUTE",
            "SUBMITTED",
            impostor_id,
            identity_id,
        )
        assert db.query(Identity).count() == 1  # nothing created for the impostor


def test_reenroll_own_face_updates_same_identity(client, auth, enroll):
    headers, _ = auth
    first = enroll(headers, "raka")
    second = enroll(headers, "raka")
    assert first == second
    with SessionLocal() as db:
        assert db.query(Identity).count() == 1
        assert db.query(BiometricConsent).count() == 2  # every agreement is recorded


def test_enroll_model_unavailable(client, auth, face_model_down):
    headers, _ = auth
    r = _enroll(client, headers, enroll_images("raka"))
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "FACE_MODEL_UNAVAILABLE"


def test_enroll_without_embedding_key_fails_closed(client, auth, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "armor_embedding_key", "")
    headers, _ = auth
    r = _enroll(client, headers, enroll_images("raka"))
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "EMBEDDING_KEY_MISSING"


def test_enroll_rejects_oversized_image(client, auth, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_image_mb", 0.00001)
    headers, _ = auth
    r = _enroll(client, headers, enroll_images("raka"))
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_enroll_requires_auth(client):
    assert _enroll(client, {}, enroll_images("raka")).status_code == 401


# --- Own-face verification and profile ------------------------------------------


@pytest.mark.parametrize(
    ("capture", "status", "match"),
    [
        (image(face("raka")), "verified", True),
        (image(face("raka", cos=0.40)), "unclear", False),  # inside the gray zone
        (image(face("sinta")), "mismatch", False),
        (image(), "no_face", False),
    ],
)
def test_verify_own_face(client, auth, enroll, capture, status, match):
    headers, _ = auth
    enroll(headers, "raka")
    r = client.post("/identity/verify", json={"image": capture}, headers=headers)
    assert r.status_code == 200
    assert (r.json()["status"], r.json()["match"]) == (status, match)


def test_verify_before_enrolling_is_404(client, auth):
    headers, _ = auth
    r = client.post("/identity/verify", json={"image": image(face("raka"))}, headers=headers)
    assert r.status_code == 404


def test_profile_and_lock(client, auth, enroll):
    headers, _ = auth
    identity_id = enroll(headers, "raka")
    r = client.get("/identity/profile", headers=headers)
    assert r.status_code == 200
    assert r.json()["identity_id"] == identity_id
    assert (r.json()["face_enrolled"], r.json()["voice_enrolled"]) == (True, False)

    r = client.post("/identity/lock", json={"identity_id": identity_id}, headers=headers)
    assert r.json()["status"] == "locked"


def test_lock_level_per_media(client, auth, enroll):
    headers, _ = auth
    identity_id = enroll(headers, "raka")
    r = client.post(
        "/identity/lock",
        json={"identity_id": identity_id, "level": "COMMERCIAL_POLITICAL", "media": "FACE"},
        headers=headers,
    )
    body = r.json()
    assert (body["face_lock"], body["voice_lock"], body["status"]) == (
        "COMMERCIAL_POLITICAL",
        "NONE",
        "locked",
    )
    r = client.post(
        "/identity/lock",
        json={"identity_id": identity_id, "level": "ALL", "media": "VOICE"},
        headers=headers,
    )
    assert r.json()["voice_lock"] == "ALL"
    r = client.post(
        "/identity/lock", json={"identity_id": identity_id, "level": "NONE"}, headers=headers
    )
    body = r.json()
    assert (body["face_lock"], body["voice_lock"], body["status"]) == ("NONE", "NONE", "active")


# --- Revoke, delete, export -------------------------------------------------------


def test_revoke_face_deletes_embedding_and_stamps_consent(client, auth, enroll):
    headers, _ = auth
    identity_id = enroll(headers, "raka")
    r = client.post("/identity/me/revoke", params={"media": "FACE"}, headers=headers)
    assert r.status_code == 200
    with SessionLocal() as db:
        row = db.query(Identity).filter_by(identity_id=identity_id).one()
        assert row.face_embedding is None
        assert db.query(BiometricConsent).one().revoked_at is not None


def test_revoked_face_is_no_longer_matched(client, make_user, enroll):
    raka_h, _ = make_user("raka@example.com")
    identity_id = enroll(raka_h, "raka")
    client.post("/identity/lock", json={"identity_id": identity_id}, headers=raka_h)
    dimas_h, _ = make_user("dimas@example.com")
    edit = {"prompt": "Edit ringan, perbaiki pencahayaan foto ini.", "image": image(face("raka"))}
    assert (
        client.post("/requests", json=edit, headers=dimas_h).json()["decision"]["action"] == "DENY"
    )
    client.post("/identity/me/revoke", params={"media": "FACE"}, headers=raka_h)
    # Without an embedding the face is simply unregistered: lapis 1 rules only.
    assert (
        client.post("/requests", json=edit, headers=dimas_h).json()["decision"]["action"] == "ALLOW"
    )


def test_revoke_requires_enrolled_identity(client, auth):
    headers, _ = auth
    r = client.post("/identity/me/revoke", params={"media": "VOICE"}, headers=headers)
    assert r.status_code == 404


def test_delete_all_identity_data(client, auth, enroll):
    headers, _ = auth
    identity_id = enroll(headers, "raka")
    client.post(
        "/permissions",
        json={"identity_id": identity_id, "intent": "COMMERCIAL_USE", "decision": "ALLOW"},
        headers=headers,
    )
    r = client.delete("/identity/me", headers=headers)
    assert r.json()["deleted_identities"] == 1
    with SessionLocal() as db:
        assert db.query(Identity).count() == 0
        assert db.query(BiometricConsent).count() == 0
    assert client.get("/identity/profile", headers=headers).status_code == 404
    # The face can be enrolled again from scratch.
    enroll(headers, "raka")


def test_me_data_export_has_no_raw_embedding(client, auth, enroll):
    headers, user_id = auth
    identity_id = enroll(headers, "raka")
    client.post(
        "/requests",
        json={"prompt": "buat avatar kartun", "image": image(face("raka"))},
        headers=headers,
    )
    r = client.get("/me/data", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["account"]["user_id"] == user_id
    assert data["identities"][0]["identity_id"] == identity_id
    assert data["identities"][0]["face_embedding_stored"] is True
    assert data["biometric_consents"][0]["text_version"] == "face-v1"
    assert len(data["requests_made"]) == 1
    assert "retention" in data
    text = r.text
    assert "gAAAA" not in text and "password" not in text.lower()


def test_identity_requires_auth(client):
    r = client.post("/identity/verify", json={"image": image(face("x"))})
    assert r.status_code == 401

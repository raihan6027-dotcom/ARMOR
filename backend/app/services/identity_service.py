"""Opt-in identities: face enrollment, matching, Lock, and the owner's data rights.

* Enrollment takes three captures at different angles, all passing the quality
  gate, all of the same person, with enough yaw spread to make a still photo of
  a photo unlikely to pass. It requires a recorded lapis 1 consent. The mean
  embedding is stored encrypted; the photos are discarded.
* A face that already matches another identity is refused and a dispute case is
  opened (one identity per face).
* Matching answers only SELF / OTHER_REGISTERED / OTHER_UNREGISTERED / UNCLEAR,
  never a name. Embeddings of unregistered faces are dropped immediately.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.ai.face import DetectedFace, cosine, face_ai, l2_normalize
from app.core.config import settings
from app.core.crypto import decrypt_embedding, encrypt_embedding
from app.core.exceptions import ArmorError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.uploads import read_upload
from app.models.biometric_consent import BiometricConsent
from app.models.consent import Consent
from app.models.identity import Identity
from app.models.permission import Permission
from app.schema.common import BiometricMedia, IdentityTarget, LockLevel
from app.services import audit_service

logger = get_logger("identity_service")

ENROLL_CAPTURES = 3


def _utcnow() -> datetime:
    return datetime.now(UTC)


def decode_image(image_b64: str, field: str = "image") -> bytes:
    """Base64 image, validated by size and content type (magic bytes)."""
    return read_upload(image_b64, "image", field)


# --- Lookups ---------------------------------------------------------------------


def _find(db: Session, identity_id: str) -> Optional[Identity]:
    return db.query(Identity).filter(Identity.identity_id == identity_id).first()


def get_owned(db: Session, identity_id: str, user_id: str, *, hide_existence: bool) -> Identity:
    """Return an identity only if `user_id` owns it.

    hide_existence=True (read endpoints) answers 404 for both "missing" and "not
    yours" so the endpoint cannot be used to probe which identities exist.
    hide_existence=False (mutations) answers 404 for missing and 403 for not yours.
    """
    identity = _find(db, identity_id)
    if identity is None:
        raise NotFoundError(f"Identity '{identity_id}' not found.")
    if identity.user_id != user_id:
        if hide_existence:
            raise NotFoundError(f"Identity '{identity_id}' not found.")
        raise ForbiddenError("Only the identity owner may do this.")
    return identity


def own_identity(db: Session, user_id: str) -> Optional[Identity]:
    """The user's own (non-child) identity, if enrolled."""
    return (
        db.query(Identity).filter(Identity.user_id == user_id, Identity.is_child.is_(False)).first()
    )


def require_own_identity(db: Session, user_id: str) -> Identity:
    identity = own_identity(db, user_id)
    if identity is None:
        raise NotFoundError("You have not enrolled an identity yet.")
    return identity


def require_not_frozen(identity: Identity) -> None:
    """A reviewer froze this identity during a false-enrollment dispute: its owner
    controls are paused until the case is resolved (protection keeps working)."""
    if identity.frozen:
        raise ArmorError(
            "IDENTITY_FROZEN",
            "This identity is frozen while a dispute is reviewed.",
            423,
        )


def lock_level(identity: Identity, media: BiometricMedia) -> LockLevel:
    raw = identity.face_lock if media is BiometricMedia.FACE else identity.voice_lock
    try:
        return LockLevel(raw)
    except ValueError:
        return LockLevel.ALL  # unreadable lock state fails closed


# --- Matching ----------------------------------------------------------------------


@dataclass
class FaceMatch:
    target: IdentityTarget
    identity: Optional[Identity]
    score: Optional[float]


def registered_face_embeddings(db: Session) -> list[tuple[Identity, np.ndarray]]:
    rows = db.query(Identity).filter(Identity.face_embedding.is_not(None)).all()
    return [(row, decrypt_embedding(row.face_embedding)) for row in rows]


def best_match(
    embedding: np.ndarray, index: list[tuple[Identity, np.ndarray]]
) -> tuple[Optional[Identity], float]:
    best: tuple[Optional[Identity], float] = (None, -1.0)
    for identity, vec in index:
        s = cosine(embedding, vec)
        if s > best[1]:
            best = (identity, s)
    return best


def classify_face(
    face: DetectedFace, requester_user_id: str, index: list[tuple[Identity, np.ndarray]]
) -> FaceMatch:
    """SELF / OTHER_REGISTERED / OTHER_UNREGISTERED / UNCLEAR for one face.

    Low quality or a score inside the gray zone (threshold +/- margin) is UNCLEAR,
    which the policy treats as REVIEW at best (CLAUDE.md bagian 7, gagal aman).
    """
    if not face.quality_ok:
        return FaceMatch(IdentityTarget.UNCLEAR, None, None)
    identity, score = best_match(face.embedding, index)
    hi = settings.face_match_threshold + settings.face_gray_margin
    lo = settings.face_match_threshold - settings.face_gray_margin
    if identity is None or score < lo:
        return FaceMatch(IdentityTarget.OTHER_UNREGISTERED, None, None)
    if score < hi:
        return FaceMatch(IdentityTarget.UNCLEAR, None, round(score, 4))
    if identity.user_id == requester_user_id and not identity.is_child:
        return FaceMatch(IdentityTarget.SELF, identity, round(score, 4))
    return FaceMatch(IdentityTarget.OTHER_REGISTERED, identity, round(score, 4))


# --- Enrollment --------------------------------------------------------------------


def _analyze_capture(image_bytes: bytes, index: int) -> DetectedFace:
    faces = face_ai.analyze(image_bytes)
    if faces is None:
        raise ArmorError(
            "FACE_MODEL_UNAVAILABLE",
            "The face model is not available, so enrollment cannot run right now.",
            503,
        )
    if not faces:
        raise ArmorError(
            "FACE_NOT_FOUND", "No face was found in a capture.", 422, {"capture": index}
        )
    if len(faces) > 1:
        raise ArmorError(
            "MULTIPLE_FACES",
            "A capture contains more than one face. Only you should be in frame.",
            422,
            {"capture": index},
        )
    face = faces[0]
    if not face.quality_ok:
        raise ArmorError(
            "FACE_QUALITY_LOW",
            "A capture is too small, blurry, or turned too far away.",
            422,
            {"capture": index, "issues": face.issues},
        )
    return face


def _check_same_person(faces: list[DetectedFace]) -> None:
    for i in range(len(faces)):
        for j in range(i + 1, len(faces)):
            if cosine(faces[i].embedding, faces[j].embedding) < settings.face_same_person_threshold:
                raise ArmorError(
                    "POSES_DIFFERENT_PERSON",
                    "The captures do not look like the same person.",
                    422,
                    {"captures": [i, j]},
                )


def _check_pose_spread(faces: list[DetectedFace]) -> None:
    yaws = [f.yaw for f in faces]
    spread = max(yaws) - min(yaws)
    if spread < settings.face_min_pose_spread_deg:
        raise ArmorError(
            "POSE_SPREAD_TOO_SMALL",
            "Turn your head slightly left and right between captures.",
            422,
            {"spread_deg": round(spread, 1), "required_deg": settings.face_min_pose_spread_deg},
        )


def check_enrollment_captures(images: list[bytes]) -> np.ndarray:
    """All enrollment defenses that need no database: one clear face per capture,
    the same person in all three, and enough change of angle between them.
    Returns the L2-normalized mean embedding; raises ArmorError otherwise.
    Also used by ml/face_eval/attacks.py so the evaluation tests this exact code."""
    faces = [_analyze_capture(img, i) for i, img in enumerate(images)]
    _check_same_person(faces)
    _check_pose_spread(faces)
    return l2_normalize(np.mean([f.embedding for f in faces], axis=0))


def duplicate_of(mean: np.ndarray, others: list[tuple[Identity, np.ndarray]]):
    """One identity per face. The gray zone counts as a match here, so a borderline
    lookalike goes to a human (dispute) instead of creating a second identity."""
    match, score = best_match(mean, others)
    if match is not None and score >= settings.face_match_threshold - settings.face_gray_margin:
        return match
    return None


def _record_consent(
    db: Session, user_id: str, identity_id: str, media: BiometricMedia, version: str
) -> BiometricConsent:
    record = BiometricConsent(
        record_id=str(uuid.uuid4()),
        user_id=user_id,
        identity_id=identity_id,
        media=media.value,
        text_version=version,
    )
    db.add(record)
    return record


def require_consent(agreed: bool, text_version: str, media: BiometricMedia) -> str:
    current = (
        settings.consent_text_face if media is BiometricMedia.FACE else settings.consent_text_voice
    )
    if not agreed:
        raise ArmorError(
            "CONSENT_REQUIRED",
            "Biometric processing needs your explicit agreement first.",
            422,
        )
    if text_version != current:
        raise ArmorError(
            "CONSENT_TEXT_OUTDATED",
            "The consent text you agreed to is not the current version.",
            422,
            {"current_version": current},
        )
    return current


def enroll_face(
    db: Session,
    user_id: str,
    images: list[bytes],
    consent_agreed: bool,
    consent_version: str,
    display_name: Optional[str] = None,
) -> Identity:
    version = require_consent(consent_agreed, consent_version, BiometricMedia.FACE)
    if len(images) != ENROLL_CAPTURES:
        raise ArmorError("CAPTURES_REQUIRED", "Exactly three captures are required.", 422)

    mean = check_enrollment_captures(images)

    existing = own_identity(db, user_id)
    others = [
        (ident, vec)
        for ident, vec in registered_face_embeddings(db)
        if existing is None or ident.identity_id != existing.identity_id
    ]
    match = duplicate_of(mean, others)
    if match is not None:
        from app.services import case_service  # local import: avoids an import cycle

        case = case_service.open_dispute_from_enrollment(
            db, user_id, match.identity_id, BiometricMedia.FACE.value, None
        )
        audit_service.record(
            db,
            "ENROLL_REFUSED_DUPLICATE",
            user_id,
            {"case_id": case.case_id, "identity_id": match.identity_id, "media": "FACE"},
        )
        db.commit()
        logger.info("enrollment refused: duplicate face, dispute case opened")
        raise ArmorError(
            "FACE_ALREADY_REGISTERED",
            "This face is already registered to another account. You can file a dispute.",
            409,
            {"case_id": case.case_id},
        )

    identity = existing
    if identity is None:
        identity = Identity(identity_id=str(uuid.uuid4()), user_id=user_id)
        db.add(identity)
    if display_name:
        identity.display_name = display_name
    identity.face_embedding = encrypt_embedding(mean)
    identity.face_enrolled_at = _utcnow()
    _record_consent(db, user_id, identity.identity_id, BiometricMedia.FACE, version)
    audit_service.record(
        db,
        "ENROLLED",
        user_id,
        {"identity_id": identity.identity_id, "media": "FACE", "consent_text": version},
    )
    db.commit()
    db.refresh(identity)
    return identity


def verify_own_face(db: Session, identity: Identity, image_bytes: bytes) -> dict:
    """Does this photo show the owner's own enrolled face? Owner-only."""
    if identity.face_embedding is None:
        return {"match": False, "score": None, "status": "not_enrolled", "ai_available": True}
    faces = face_ai.analyze(image_bytes)
    if faces is None:
        return {"match": False, "score": None, "status": "model_unavailable", "ai_available": False}
    if not faces:
        return {"match": False, "score": None, "status": "no_face", "ai_available": True}
    score = cosine(faces[0].embedding, decrypt_embedding(identity.face_embedding))
    hi = settings.face_match_threshold + settings.face_gray_margin
    lo = settings.face_match_threshold - settings.face_gray_margin
    status = "verified" if score >= hi else ("unclear" if score >= lo else "mismatch")
    return {
        "match": status == "verified",
        "score": round(score, 4),
        "status": status,
        "ai_available": True,
    }


# --- Owner controls ----------------------------------------------------------------


def lock(
    db: Session,
    identity_id: str,
    user_id: str,
    level: LockLevel = LockLevel.ALL,
    media: Optional[BiometricMedia] = None,
) -> Identity:
    """Set the Lock level of an identity the caller owns, per media (None = both).
    Unregistered ids can never be claimed."""
    identity = get_owned(db, identity_id, user_id, hide_existence=False)
    require_not_frozen(identity)
    if media in (None, BiometricMedia.FACE):
        identity.face_lock = level.value
    if media in (None, BiometricMedia.VOICE):
        identity.voice_lock = level.value
    unlocked = (identity.face_lock, identity.voice_lock) == (LockLevel.NONE.value,) * 2
    identity.status = "active" if unlocked else "locked"
    audit_service.record(
        db,
        "LOCK_CHANGED",
        user_id,
        {
            "identity_id": identity_id,
            "face_lock": identity.face_lock,
            "voice_lock": identity.voice_lock,
        },
    )
    db.commit()
    db.refresh(identity)
    return identity


def revoke_media(db: Session, user_id: str, media: BiometricMedia) -> Identity:
    """Withdraw lapis 1 consent for one media: stamp the record and delete that
    media's embedding immediately (CLAUDE.md bagian 9, pencabutan per media)."""
    identity = require_own_identity(db, user_id)
    now = _utcnow()
    for record in (
        db.query(BiometricConsent)
        .filter(
            BiometricConsent.identity_id == identity.identity_id,
            BiometricConsent.media == media.value,
            BiometricConsent.revoked_at.is_(None),
        )
        .all()
    ):
        record.revoked_at = now
    if media is BiometricMedia.FACE:
        identity.face_embedding = None
        identity.face_enrolled_at = None
    else:
        identity.voice_embedding = None
        identity.voice_enrolled_at = None
    audit_service.record(
        db,
        "BIOMETRIC_CONSENT_REVOKED",
        user_id,
        {"identity_id": identity.identity_id, "media": media.value},
    )
    db.commit()
    db.refresh(identity)
    return identity


def delete_all(db: Session, user_id: str) -> int:
    """Delete every identity the user owns and everything attached to them."""
    identities = db.query(Identity).filter(Identity.user_id == user_id).all()
    ids = [i.identity_id for i in identities]
    if ids:
        db.query(Permission).filter(Permission.identity_id.in_(ids)).delete(
            synchronize_session=False
        )
        db.query(Consent).filter(Consent.identity_id.in_(ids)).delete(synchronize_session=False)
        db.query(BiometricConsent).filter(BiometricConsent.identity_id.in_(ids)).delete(
            synchronize_session=False
        )
        for identity in identities:
            db.delete(identity)
        audit_service.record(db, "IDENTITY_DELETED", user_id, {"identity_ids": ids})
    db.commit()
    return len(ids)

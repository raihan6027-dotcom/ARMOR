"""Identity enrollment / verification, backed by InsightFace + the ArcFace registry.

Embeddings enrolled at runtime are stored (JSON) in the DB. Verification compares
a fresh embedding to the enrolled one, falling back to the pre-deployment registry.
When the face model is unavailable, results are flagged (`ai_available=False`) and
never reported as a positive match.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.ai.identity_client import identity_ai_client
from app.ai.registry import face_registry
from app.core.config import settings
from app.core.exceptions import ArmorError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.identity import Identity
from app.schema.common import IdentityTarget

logger = get_logger("identity_service")


def decode_image(image_b64: str) -> bytes:
    if not image_b64:
        raise ArmorError("INVALID_IMAGE", "No image provided.", 422)
    # Tolerate data URLs: "data:image/jpeg;base64,...."
    if "," in image_b64 and image_b64.strip().startswith("data:"):
        image_b64 = image_b64.split(",", 1)[1]
    try:
        return base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ArmorError("INVALID_IMAGE", f"Image is not valid base64: {exc}", 422) from exc


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


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


def enroll(
    db: Session,
    identity_id: str,
    image_bytes: bytes,
    display_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> tuple[Identity, bool]:
    """Create/update an identity. Returns (identity, ai_available).

    An identity that already belongs to another account can never be re-enrolled
    (that used to hand its ownership, and SELF decisions, to the caller).
    """
    identity = _find(db, identity_id)
    if identity is not None and identity.user_id != user_id:
        raise ForbiddenError("This identity is registered to another account.")

    embedding = identity_ai_client.embed(image_bytes)
    ai_available = embedding is not None

    if identity is None:
        identity = Identity(identity_id=identity_id, status="active")
        db.add(identity)

    identity.user_id = user_id
    if display_name:
        identity.display_name = display_name
    if embedding is not None:
        identity.embedding_reference = json.dumps(embedding.astype(float).tolist())

    db.commit()
    db.refresh(identity)
    return identity, ai_available


def _stored_embedding(identity: Identity) -> Optional[np.ndarray]:
    if not identity.embedding_reference:
        return None
    try:
        return np.asarray(json.loads(identity.embedding_reference), dtype=np.float32)
    except (json.JSONDecodeError, ValueError):
        return None


def verify(db: Session, identity_id: str, image_bytes: bytes) -> dict:
    """Verify a face against the claimed identity. Returns match/confidence/ai_available."""
    query = identity_ai_client.embed(image_bytes)
    if query is None:
        return {
            "match": False,
            "confidence": 0.0,
            "ai_available": False,
            "status": "model_unavailable",
        }

    identity = db.query(Identity).filter(Identity.identity_id == identity_id).first()

    score: Optional[float] = None
    stored = _stored_embedding(identity) if identity else None
    if stored is not None:
        score = _cosine(query, stored)
    else:
        score = face_registry.score_against(query, identity_id)

    if score is None:
        # No enrolled embedding and not in the registry.
        return {"match": False, "confidence": 0.0, "ai_available": True, "status": "not_enrolled"}

    match = score >= settings.face_match_threshold
    return {
        "match": bool(match),
        "confidence": round(score, 4),
        "ai_available": True,
        "status": "verified" if match else "mismatch",
    }


def determine_target(
    db: Session, requester_user_id: Optional[str], identity_id: str, image_bytes: Optional[bytes]
) -> dict:
    """For orchestration: classify SELF vs OTHER and whether the face is verified.

    SELF requires that the identity is owned by the requesting user AND (when an
    image is supplied) the face matches. Otherwise OTHER.
    """
    identity = db.query(Identity).filter(Identity.identity_id == identity_id).first()
    owned_by_requester = bool(
        identity and requester_user_id and identity.user_id == requester_user_id
    )

    face_matches: Optional[bool] = None
    score: Optional[float] = None
    ai_available = True
    if image_bytes:
        result = verify(db, identity_id, image_bytes)
        face_matches = result["match"]
        score = result["confidence"]
        ai_available = result["ai_available"]

    if owned_by_requester:
        # The authenticated owner is acting on their own registered identity: this is
        # a trusted SELF claim (account-level verification). A supplied face that does
        # NOT match still downgrades verification.
        target = IdentityTarget.SELF
        verified = True if image_bytes is None else bool(face_matches)
    else:
        target = IdentityTarget.OTHER
        verified = bool(face_matches)

    return {
        "target": target.value,
        "verified": verified,
        "match_score": score,
        "ai_available": ai_available,
        "known": identity is not None,
        "locked": bool(identity is not None and identity.status == "locked"),
    }


def get_profile(db: Session, identity_id: str, user_id: str) -> Identity:
    return get_owned(db, identity_id, user_id, hide_existence=True)


def lock(db: Session, identity_id: str, user_id: str) -> Identity:
    """Lock an identity the caller owns. Unregistered ids can no longer be claimed."""
    identity = get_owned(db, identity_id, user_id, hide_existence=False)
    identity.status = "locked"
    db.commit()
    db.refresh(identity)
    return identity

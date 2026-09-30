from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.identity import Identity
from app.models.user import User
from app.schema.common import BiometricMedia
from app.schema.identity import (
    DeleteIdentityResponse,
    IdentityEnrollRequest,
    IdentityEnrollResponse,
    IdentityLockRequest,
    IdentityLockResponse,
    IdentityProfileResponse,
    IdentityVerifyRequest,
    IdentityVerifyResponse,
    RevokeResponse,
)
from app.services import identity_service

router = APIRouter(prefix="/identity", tags=["Identity"])


def _profile(identity: Identity) -> IdentityProfileResponse:
    return IdentityProfileResponse(
        identity_id=identity.identity_id,
        status=identity.status,
        display_name=identity.display_name,
        is_child=identity.is_child,
        face_enrolled=identity.face_embedding is not None,
        voice_enrolled=identity.voice_embedding is not None,
        face_lock=identity_service.lock_level(identity, BiometricMedia.FACE),
        voice_lock=identity_service.lock_level(identity, BiometricMedia.VOICE),
    )


def _owned_or_own(db: Session, identity_id: str | None, user: User) -> Identity:
    if identity_id:
        return identity_service.get_owned(db, identity_id, user.user_id, hide_existence=True)
    return identity_service.require_own_identity(db, user.user_id)


@router.post("/enroll", response_model=IdentityEnrollResponse, status_code=201)
def enroll_identity(
    request: IdentityEnrollRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Enroll your own face from three captures at different angles.

    Requires lapis 1 consent to the current face consent text. Photos are only
    processed in memory; only an encrypted mean embedding is stored.
    """
    images = [identity_service.decode_image(img) for img in request.images]
    identity = identity_service.enroll_face(
        db,
        current.user_id,
        images,
        consent_agreed=request.consent.agreed,
        consent_version=request.consent.text_version,
        display_name=request.display_name,
    )
    return IdentityEnrollResponse(
        identity_id=identity.identity_id,
        status=identity.status,
        face_enrolled=True,
        message="Wajah terdaftar. Foto tidak disimpan.",
    )


@router.post("/verify", response_model=IdentityVerifyResponse)
def verify_identity(
    request: IdentityVerifyRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    # Only your own identity: otherwise this endpoint is an oracle for "is this
    # face registered as X?" against anyone's identity.
    identity = _owned_or_own(db, request.identity_id, current)
    image_bytes = identity_service.decode_image(request.image)
    result = identity_service.verify_own_face(db, identity, image_bytes)
    return IdentityVerifyResponse(identity_id=identity.identity_id, **result)


@router.get("/profile", response_model=IdentityProfileResponse)
def get_identity_profile(
    identity_id: str | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return _profile(_owned_or_own(db, identity_id, current))


@router.post("/lock", response_model=IdentityLockResponse)
def lock_identity(
    request: IdentityLockRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    identity = identity_service.lock(
        db, request.identity_id, current.user_id, request.level, request.media
    )
    return IdentityLockResponse(
        identity_id=identity.identity_id,
        status=identity.status,
        face_lock=identity_service.lock_level(identity, BiometricMedia.FACE),
        voice_lock=identity_service.lock_level(identity, BiometricMedia.VOICE),
        message="Identity lock updated.",
    )


@router.post("/me/revoke", response_model=RevokeResponse)
def revoke_media(
    media: BiometricMedia = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Withdraw consent for one media; its embedding is deleted immediately."""
    identity = identity_service.revoke_media(db, current.user_id, media)
    return RevokeResponse(
        identity_id=identity.identity_id,
        media=media,
        revoked_at=datetime.now(UTC),
        message="Persetujuan dicabut dan data biometrik media ini dihapus.",
    )


@router.delete("/me", response_model=DeleteIdentityResponse)
def delete_my_identities(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Delete all identities you own, with their embeddings, permissions and consents."""
    n = identity_service.delete_all(db, current.user_id)
    return DeleteIdentityResponse(deleted_identities=n, message="Semua data identitas dihapus.")

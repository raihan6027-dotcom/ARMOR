from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.database import get_db
from app.models.identity import Identity
from app.models.user import User
from app.schema.common import BiometricMedia
from app.schema.identity import (
    IdentityEnrollRequest,
    IdentityEnrollResponse,
    IdentityLockRequest,
    IdentityLockResponse,
    IdentityProfileResponse,
    IdentityVerifyRequest,
    IdentityVerifyResponse,
)
from app.services import identity_service

router = APIRouter(prefix="/identity", tags=["Identity"])


@router.post("/enroll", response_model=IdentityEnrollResponse)
def enroll_identity(
    request: IdentityEnrollRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    image_bytes = identity_service.decode_image(request.image)
    identity, ai_available = identity_service.enroll(
        db, request.identity_id, image_bytes, request.display_name, user_id=current.user_id
    )
    message = (
        "Identity enrolled successfully."
        if ai_available
        else "Identity registered, but the face model was unavailable so no embedding was stored."
    )
    return IdentityEnrollResponse(
        identity_id=identity.identity_id, status=identity.status, message=message
    )


@router.post("/verify", response_model=IdentityVerifyResponse)
def verify_identity(
    request: IdentityVerifyRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    # Only your own identity: otherwise this endpoint is an oracle for "is this
    # face registered as X?" against anyone's identity.
    identity_service.get_owned(db, request.identity_id, current.user_id, hide_existence=True)
    image_bytes = identity_service.decode_image(request.image)
    result = identity_service.verify(db, request.identity_id, image_bytes)
    return IdentityVerifyResponse(
        match=result["match"],
        confidence=result["confidence"],
        identity_id=request.identity_id,
        status=result["status"],
        ai_available=result["ai_available"],
    )


@router.get("/profile", response_model=IdentityProfileResponse)
def get_identity_profile(
    identity_id: str | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if identity_id:
        identity = identity_service.get_profile(db, identity_id, current.user_id)
    else:
        identity = db.query(Identity).filter(Identity.user_id == current.user_id).first()
        if identity is None:
            raise NotFoundError("No identity enrolled for this user.")
    return IdentityProfileResponse(
        identity_id=identity.identity_id,
        status=identity.status,
        enrolled=identity.embedding_reference is not None,
        display_name=identity.display_name,
        face_lock=identity_service.lock_level(identity, BiometricMedia.FACE),
        voice_lock=identity_service.lock_level(identity, BiometricMedia.VOICE),
    )


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

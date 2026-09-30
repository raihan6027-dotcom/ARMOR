from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schema.common import BiometricMedia, LockLevel


class ConsentAgreement(BaseModel):
    """Lapis 1: explicit agreement to a specific version of docs/consent-text/."""

    agreed: bool
    text_version: str


class IdentityEnrollRequest(BaseModel):
    # Exactly three captures: straight, slightly left, slightly right (base64).
    images: list[str] = Field(min_length=3, max_length=3)
    consent: ConsentAgreement
    display_name: Optional[str] = Field(default=None, max_length=80)


class IdentityEnrollResponse(BaseModel):
    identity_id: str
    status: str
    face_enrolled: bool
    message: str


class IdentityVerifyRequest(BaseModel):
    image: str  # base64-encoded face image
    identity_id: Optional[str] = None  # default: your own identity


class IdentityVerifyResponse(BaseModel):
    identity_id: str
    match: bool
    score: Optional[float] = None
    status: str  # verified | unclear | mismatch | no_face | not_enrolled | model_unavailable
    ai_available: bool = True


class IdentityProfileResponse(BaseModel):
    identity_id: str
    status: str
    display_name: Optional[str] = None
    is_child: bool = False
    face_enrolled: bool
    voice_enrolled: bool
    face_lock: LockLevel = LockLevel.NONE
    voice_lock: LockLevel = LockLevel.NONE


class IdentityLockRequest(BaseModel):
    identity_id: str
    level: LockLevel = LockLevel.ALL
    # None = apply the level to both FACE and VOICE.
    media: Optional[BiometricMedia] = None


class IdentityLockResponse(BaseModel):
    identity_id: str
    status: str
    face_lock: LockLevel
    voice_lock: LockLevel
    message: str


class RevokeResponse(BaseModel):
    identity_id: str
    media: BiometricMedia
    revoked_at: datetime
    message: str


class DeleteIdentityResponse(BaseModel):
    deleted_identities: int
    message: str

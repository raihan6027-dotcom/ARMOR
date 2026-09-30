from typing import Optional

from pydantic import BaseModel

from app.schema.common import BiometricMedia, LockLevel


class IdentityEnrollRequest(BaseModel):
    identity_id: str
    image: str  # base64-encoded face image
    display_name: Optional[str] = None


class IdentityEnrollResponse(BaseModel):
    identity_id: str
    status: str
    message: str


class IdentityVerifyRequest(BaseModel):
    identity_id: str
    image: str  # base64-encoded face image


class IdentityVerifyResponse(BaseModel):
    match: bool
    confidence: float
    identity_id: str
    status: str
    ai_available: bool = True


class IdentityProfileResponse(BaseModel):
    identity_id: str
    status: str
    enrolled: bool
    display_name: Optional[str] = None
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

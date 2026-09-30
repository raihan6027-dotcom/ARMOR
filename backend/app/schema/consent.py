from typing import Optional

from pydantic import BaseModel

from app.schema.common import BiometricMedia, ConsentStatus, Intent


class ConsentRequest(BaseModel):
    """Ask for consent on one of your own requests that is waiting for review."""

    request_id: str
    intent: Optional[Intent] = None  # default: the request's intent
    media: Optional[BiometricMedia] = None  # default: the media each target governs


class ConsentRequestResponse(BaseModel):
    request_id: str
    status: ConsentStatus
    message: str = "Permintaan persetujuan dikirim jika diperlukan."


class ConsentRequestStatusResponse(BaseModel):
    request_id: str
    status: ConsentStatus


class ConsentStatusResponse(BaseModel):
    consent_id: str
    identity_id: str
    status: ConsentStatus
    request_id: Optional[str] = None
    intent: Optional[str] = None
    media: Optional[str] = None


class ConsentInboxItem(BaseModel):
    consent_id: str
    identity_id: str
    requester_email: Optional[str] = None
    intent: Optional[str] = None
    media: Optional[str] = None
    prompt: Optional[str] = None
    media_type: Optional[str] = None
    status: ConsentStatus
    created_at: Optional[str] = None


class ConsentInboxResponse(BaseModel):
    items: list[ConsentInboxItem]


class ConsentRespondRequest(BaseModel):
    consent_id: str
    decision: str  # APPROVED | DENIED (also accepts GRANTED/DENY etc; normalized)


class ConsentRespondResponse(BaseModel):
    consent_id: str
    status: ConsentStatus
    message: str = "Consent response recorded successfully"

from datetime import datetime
from typing import Literal, Optional

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


class ConsentItem(BaseModel):
    consent_id: str
    identity_id: str
    requester_email: Optional[str] = None
    intent: Optional[str] = None
    media: Optional[str] = None
    prompt: Optional[str] = None
    media_type: Optional[str] = None
    status: ConsentStatus
    # PENDING | GRANTED | DENIED | REVOKED | EXPIRED | USED
    state: str
    validity: Optional[str] = None
    expires_at: Optional[str] = None
    answered_at: Optional[str] = None
    created_at: Optional[str] = None


class ConsentInboxResponse(BaseModel):
    items: list[ConsentItem]
    pending: int


class ConsentAnswer(BaseModel):
    """APPROVE with a scope and validity, DENY, or BLOCK (deny and block the sender)."""

    action: Literal["APPROVE", "DENY", "BLOCK"]
    intent: Optional[Intent] = None  # narrow the scope; default = what was asked
    media: Optional[BiometricMedia] = None
    validity: Literal["ONCE", "DAYS_1", "DAYS_7", "DAYS_30", "UNTIL"] = "ONCE"
    until: Optional[datetime] = None  # required when validity = UNTIL

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "action": "APPROVE",
                    "intent": "COMMERCIAL_USE",
                    "media": "FACE",
                    "validity": "DAYS_7",
                },
                {"action": "BLOCK"},
            ]
        }
    }

from typing import Optional

from pydantic import BaseModel

from app.schema.common import BiometricMedia, ConsentStatus, Intent


class ConsentRequest(BaseModel):
    identity_id: str
    request_id: Optional[str] = None
    intent: Optional[Intent] = None
    media: Optional[BiometricMedia] = None


class ConsentRequestResponse(BaseModel):
    consent_id: str
    identity_id: str
    status: ConsentStatus
    message: str = "Consent request created successfully"


class ConsentStatusResponse(BaseModel):
    consent_id: str
    identity_id: str
    status: ConsentStatus
    request_id: Optional[str] = None


class ConsentRespondRequest(BaseModel):
    consent_id: str
    decision: str  # APPROVED | DENIED (also accepts GRANTED/DENY etc; normalized)


class ConsentRespondResponse(BaseModel):
    consent_id: str
    status: ConsentStatus
    message: str = "Consent response recorded successfully"

from typing import Optional

from pydantic import BaseModel


class DecisionRequest(BaseModel):
    risk_level: str
    consent: str
    permission: str
    identity_target: str = "OTHER"
    identity_verified: bool = False
    intent: Optional[str] = None


class DecisionResponse(BaseModel):
    decision: str
    reason_code: str
    reason: str

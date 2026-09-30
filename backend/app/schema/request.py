from typing import Optional

from pydantic import BaseModel

from app.schema.common import Decision, Intent, RiskLevel


class RequestCreate(BaseModel):
    identity_id: str
    prompt: str
    image: Optional[str] = None  # base64-encoded image (optional context for the AI)


# --- Structured sub-blocks of the decision response ---
class IdentityBlock(BaseModel):
    """Requester-safe: only whether the media is the requester (SELF) or someone
    else. Never the target identity id, match score, or verification flag."""

    target: str


class IntentBlock(BaseModel):
    label: Intent
    confidence: float
    ai_available: bool


class RiskBlock(BaseModel):
    score: Optional[int] = None
    level: Optional[RiskLevel] = None
    ai_available: bool


class DecisionBlock(BaseModel):
    action: Decision
    reason_code: str
    reason: str


class RequestDecisionResponse(BaseModel):
    request_id: str
    identity: IdentityBlock
    intent: IntentBlock
    risk: RiskBlock
    decision: DecisionBlock


class RequestHistoryItem(BaseModel):
    request_id: str
    intent: Optional[str]
    risk_level: Optional[str]
    decision: str
    reason_code: Optional[str]
    created_at: str


class RequestHistoryResponse(BaseModel):
    items: list[RequestHistoryItem]
    total: int

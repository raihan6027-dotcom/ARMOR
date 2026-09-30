from typing import Optional

from pydantic import BaseModel

from app.schema.common import ConsentStatus, Decision, Intent, PermissionDecision, RiskLevel


class RequestCreate(BaseModel):
    identity_id: str
    prompt: str
    image: Optional[str] = None  # base64-encoded image (optional context for the AI)


# --- Structured sub-blocks of the decision response ---
class IdentityBlock(BaseModel):
    identity_id: str
    verified: bool
    target: str
    match_score: Optional[float] = None


class IntentBlock(BaseModel):
    label: Intent
    confidence: float
    ai_available: bool


class ConsentBlock(BaseModel):
    status: ConsentStatus


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
    consent: ConsentBlock
    risk: RiskBlock
    permission: Optional[PermissionDecision] = None
    decision: DecisionBlock


class RequestHistoryItem(BaseModel):
    request_id: str
    identity_id: Optional[str]
    intent: Optional[str]
    risk_level: Optional[str]
    decision: str
    reason_code: Optional[str]
    created_at: str


class RequestHistoryResponse(BaseModel):
    items: list[RequestHistoryItem]
    total: int

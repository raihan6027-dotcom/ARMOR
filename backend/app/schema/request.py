from typing import Optional

from pydantic import BaseModel, Field

from app.schema.common import Decision, Intent, MediaType, RiskLevel


class RequestCreate(BaseModel):
    """Who is in the media is found by ARMOR, never named by the client."""

    prompt: str = Field(min_length=1, max_length=2000)
    image: Optional[str] = None  # base64-encoded image (optional context for the AI)
    # Defaults to IMAGE when an image is attached, TEXT_ONLY otherwise.
    media_type: Optional[MediaType] = None


# --- Structured sub-blocks of the decision response ---
class PersonBlock(BaseModel):
    source: str  # FACE | VOICE | TEXT
    target: str  # SELF | OTHER (never registered/unregistered)
    quality_ok: bool  # the face/voice was clear enough to check


class IdentityBlock(BaseModel):
    """Requester-safe: SELF / OTHER / NONE summary plus one entry per person found.
    Never a target identity id, whether it is registered, or a match score."""

    target: str
    people: list[PersonBlock] = []


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
    # Public code (e.g. ALLOWED, NEEDS_REVIEW, HARMFUL_DEFAMATION, NOT_PERMITTED).
    reason_code: str
    reason: str
    suggestion: Optional[str] = None
    label_required: bool = False


class RequestDecisionResponse(BaseModel):
    request_id: str
    media_type: MediaType
    identity: IdentityBlock
    intent: IntentBlock
    risk: RiskBlock
    decision: DecisionBlock
    checks_unavailable: list[str] = []


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

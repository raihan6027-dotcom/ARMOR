from typing import Optional

from pydantic import BaseModel, Field

from app.schema.common import Decision, Intent, MediaType, RiskLevel


class RequestCreate(BaseModel):
    """Who is in the media is found by ARMOR, never named by the client.
    Send at most one of image, video, audio (base64); none = text only."""

    prompt: str = Field(min_length=1, max_length=2000)
    image: Optional[str] = None
    video: Optional[str] = None
    audio: Optional[str] = None
    # Derived from the attached media when omitted.
    media_type: Optional[MediaType] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "Buat karikatur superhero dari foto ini.",
                    "image": "<base64 PNG/JPEG>",
                }
            ]
        }
    }


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
    # Content features that raised the score most (never who is registered).
    top_features: list[dict] = []


class DecisionBlock(BaseModel):
    action: Decision
    # Public code (e.g. ALLOWED, NEEDS_REVIEW, HARMFUL_DEFAMATION, NOT_PERMITTED).
    reason_code: str
    reason: str
    suggestion: Optional[str] = None
    label_required: bool = False


class RequestDecisionResponse(BaseModel):
    request_id: str
    status: str  # FINAL | HELD (waiting for consent or review)
    media_type: MediaType
    identity: IdentityBlock
    intent: IntentBlock
    risk: RiskBlock
    decision: DecisionBlock
    checks_unavailable: list[str] = []
    timing_ms: dict[str, int] = {}

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "7d1c2f7e-5d8b-4e3f-9a51-2b9c0f1e6a10",
                    "status": "FINAL",
                    "media_type": "IMAGE",
                    "identity": {
                        "target": "OTHER",
                        "people": [{"source": "FACE", "target": "OTHER", "quality_ok": True}],
                    },
                    "intent": {"label": "DEFAMATION", "confidence": 0.94, "ai_available": True},
                    "risk": {"score": 95, "level": "CRITICAL", "ai_available": False},
                    "decision": {
                        "action": "DENY",
                        "reason_code": "HARMFUL_DEFAMATION",
                        "reason": "Konten yang membuat orang lain terlihat seperti tahanan "
                        "dapat mencemarkan nama baiknya.",
                        "suggestion": "Buat karikatur superhero dari foto ini.",
                        "label_required": False,
                    },
                    "checks_unavailable": [],
                    "timing_ms": {"router": 0, "face": 41, "intent": 3, "risk": 1, "policy": 2},
                }
            ]
        }
    }


class RequestDetail(BaseModel):
    request_id: str
    status: str
    prompt: str
    media_type: Optional[str] = None
    decision: DecisionBlock
    created_at: str
    updated_at: Optional[str] = None


class RequestHistoryItem(BaseModel):
    request_id: str
    status: Optional[str] = None
    intent: Optional[str]
    risk_level: Optional[str]
    decision: str
    reason_code: Optional[str]
    created_at: str


class RequestHistoryResponse(BaseModel):
    items: list[RequestHistoryItem]
    total: int

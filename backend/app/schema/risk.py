from typing import Optional

from pydantic import BaseModel, Field

from app.schema.common import Intent, MediaType


class RiskRequest(BaseModel):
    identity_target: str = "NONE"  # SELF | OTHER_REGISTERED | OTHER_UNREGISTERED | UNCLEAR | NONE
    intent: Intent
    prompt: str = ""
    media_type: MediaType = MediaType.IMAGE
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class RiskFactor(BaseModel):
    feature: str
    value: object = None
    effect: Optional[float] = None  # score points attributable to this feature


class RiskResponse(BaseModel):
    risk_level: str
    risk_score: int
    ai_available: bool = True
    model_version: Optional[str] = None
    top_features: list[RiskFactor] = []
    features: dict = {}

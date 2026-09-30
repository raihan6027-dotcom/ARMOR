from typing import Optional

from pydantic import BaseModel


class RiskRequest(BaseModel):
    identity_target: str
    intent: str
    prompt: Optional[str] = None


class RiskResponse(BaseModel):
    risk_level: str
    risk_score: int
    ai_available: bool = True

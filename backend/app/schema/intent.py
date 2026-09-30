from typing import Optional

from pydantic import BaseModel


class IntentRequest(BaseModel):
    prompt: str
    identity_id: Optional[str] = None
    image: Optional[str] = None  # optional base64 image context


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    target_identity: Optional[str] = None
    ai_available: bool = True

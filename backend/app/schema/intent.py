from pydantic import BaseModel


class IntentRequest(BaseModel):
    prompt: str


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    ai_available: bool = True

from fastapi import APIRouter

from app.ai.client import AIClient
from app.schema.intent import IntentRequest, IntentResponse

router = APIRouter(tags=["Intent"])
ai_client = AIClient()


def _analyze(request: IntentRequest) -> IntentResponse:
    result = ai_client.analyze_intent(request.prompt)
    return IntentResponse(
        intent=result["intent"],
        confidence=result["confidence"],
        ai_available=result["available"],
    )


# Original contract (preserved).
@router.post("/ai/analyze-intent", response_model=IntentResponse)
def analyze_intent(request: IntentRequest):
    return _analyze(request)


# PRD alias.
@router.post("/analyze/intent", response_model=IntentResponse)
def analyze_intent_alias(request: IntentRequest):
    return _analyze(request)

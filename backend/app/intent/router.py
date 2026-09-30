from fastapi import APIRouter

from app.ai.client import AIClient
from app.schema.intent import IntentRequest, IntentResponse
from app.services.identity_service import decode_image

router = APIRouter(tags=["Intent"])
ai_client = AIClient()


def _analyze(request: IntentRequest) -> IntentResponse:
    image_bytes = decode_image(request.image) if request.image else None
    result = ai_client.analyze_intent(request.prompt, image_bytes=image_bytes)
    return IntentResponse(
        intent=result["intent"],
        confidence=result["confidence"],
        target_identity=request.identity_id,
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

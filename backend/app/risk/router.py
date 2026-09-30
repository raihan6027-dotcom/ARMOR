from fastapi import APIRouter

from app.ai.client import AIClient
from app.schema.risk import RiskRequest, RiskResponse
from app.services.identity_service import decode_image

router = APIRouter(tags=["Risk"])
ai_client = AIClient()


def _analyze(request: RiskRequest) -> RiskResponse:
    image_bytes = decode_image(request.image) if request.image else None
    result = ai_client.analyze_risk(
        identity_target=request.identity_target,
        intent=request.intent,
        prompt=request.prompt,
        image_bytes=image_bytes,
    )
    return RiskResponse(
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        ai_available=result["available"],
    )


# Original contract (preserved).
@router.post("/risk", response_model=RiskResponse)
def analyze_risk(request: RiskRequest):
    return _analyze(request)


# PRD alias.
@router.post("/analyze/risk", response_model=RiskResponse)
def analyze_risk_alias(request: RiskRequest):
    return _analyze(request)

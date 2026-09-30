from fastapi import APIRouter

from app.ai.client import AIClient
from app.schema.risk import RiskRequest, RiskResponse

router = APIRouter(tags=["Risk"])
ai_client = AIClient()


def _analyze(request: RiskRequest) -> RiskResponse:
    result = ai_client.analyze_risk(
        identity_target=request.identity_target,
        intent=request.intent,
        prompt=request.prompt,
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

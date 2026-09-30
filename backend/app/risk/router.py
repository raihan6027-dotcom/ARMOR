from fastapi import APIRouter

from app.ai.client import AIClient
from app.schema.risk import RiskRequest, RiskResponse

router = APIRouter(tags=["Risk"])
ai_client = AIClient()


def _analyze(request: RiskRequest) -> RiskResponse:
    features = ai_client.risk_features(
        request.prompt,
        request.intent.value,
        request.confidence,
        request.identity_target,
        request.media_type.value,
    )
    result = ai_client.analyze_risk(features)
    return RiskResponse(
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        ai_available=result["available"],
        model_version=result["model_version"],
        top_features=result["top_features"],
        features=result["features"],
    )


@router.post("/risk", response_model=RiskResponse)
def analyze_risk(request: RiskRequest):
    """Content risk only: consent and permissions are never inputs."""
    return _analyze(request)


@router.post("/analyze/risk", response_model=RiskResponse)
def analyze_risk_alias(request: RiskRequest):
    return _analyze(request)

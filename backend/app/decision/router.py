from fastapi import APIRouter

from app.policy.engine import evaluate_policy
from app.schema.decision import DecisionRequest, DecisionResponse

router = APIRouter(prefix="/decision", tags=["Decision"])


@router.post("", response_model=DecisionResponse)
def decide(request: DecisionRequest):
    """Stateless deterministic policy evaluation over pre-computed signals."""
    decision, reason_code, reason = evaluate_policy(
        risk_level=request.risk_level,
        consent=request.consent,
        permission=request.permission,
        identity_target=request.identity_target,
        identity_verified=request.identity_verified,
        intent=request.intent,
    )
    return DecisionResponse(decision=decision, reason_code=reason_code, reason=reason)

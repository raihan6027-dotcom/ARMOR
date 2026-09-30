from fastapi import APIRouter

from app.policy.engine import PolicyInput, TargetInput, evaluate
from app.schema.decision import DecisionRequest, DecisionResponse

router = APIRouter(prefix="/decision", tags=["Decision"])


@router.post("", response_model=DecisionResponse)
def decide(request: DecisionRequest):
    """Stateless deterministic policy evaluation over pre-computed signals."""
    result = evaluate(
        PolicyInput(
            targets=[TargetInput(**t.model_dump()) for t in request.targets],
            intent=request.intent,
            risk_level=request.risk_level,
            media_type=request.media_type,
            intent_confidence=request.intent_confidence,
            realism=request.realism,
            unavailable=tuple(request.unavailable),
            prompt=request.prompt,
        )
    )
    return DecisionResponse(
        decision=result.decision,
        reason_code=result.reason_code,
        reason=result.reason,
        suggestion=result.suggestion,
        requester_code=result.requester_code,
        requester_message=result.requester_message,
        effective_intent=result.effective_intent,
        label_required=result.label_required,
        per_target_detail=[d.as_dict() for d in result.per_target_detail],
    )

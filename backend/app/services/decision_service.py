"""Request orchestration: the ARMOR AI-safety gateway pipeline.

Coordinates identity verification -> intent analysis (AI) -> permission lookup ->
consent lookup -> risk analysis (AI) -> deterministic policy -> persisted decision.
The AI supplies structured *information* only; the policy engine owns the verdict.
"""
from __future__ import annotations

import time
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.client import AIClient
from app.core.logging import get_logger
from app.models.request import Request
from app.policy.engine import evaluate_policy
from app.schema.common import Intent, RiskLevel, normalize_intent
from app.services import consent_service, identity_service, permission_service

logger = get_logger("orchestration")
ai_client = AIClient()


def _next_request_id(db: Session) -> str:
    count = db.query(Request).count()
    return f"REQ-{count + 1:03d}"


def orchestrate(
    db: Session,
    requester_user_id: Optional[str],
    identity_id: str,
    prompt: str,
    image_bytes: Optional[bytes] = None,
) -> dict:
    started = time.perf_counter()

    # 1-2. Identity: SELF vs OTHER and verification.
    ident = identity_service.determine_target(db, requester_user_id, identity_id, image_bytes)

    # 3. Intent (AI).
    intent_res = ai_client.analyze_intent(prompt, image_bytes=image_bytes)
    intent = normalize_intent(intent_res["intent"])

    # 4. Permission for this intent.
    permission = permission_service.resolve_for_intent(db, identity_id, intent)

    # 5. Consent status on record.
    consent = consent_service.latest_status_for(db, identity_id, requester_user_id)

    # 6. Risk (AI), with identity/intent/consent context.
    risk_res = ai_client.analyze_risk(
        identity_target=ident["target"],
        intent=intent.value,
        consent=consent.value,
        prompt=prompt,
        image_bytes=image_bytes,
    )
    risk_level = risk_res.get("risk_level")

    # 7. Deterministic decision.
    decision, reason_code, reason = evaluate_policy(
        risk_level=risk_level,
        consent=consent.value,
        permission=permission.value,
        identity_target=ident["target"],
        identity_verified=ident["verified"],
        intent=intent.value,
    )

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # 8. Persist history.
    request_id = _next_request_id(db)
    row = Request(
        request_id=request_id,
        requester_id=requester_user_id,
        identity_id=identity_id,
        prompt=prompt,
        identity_verified=ident["verified"],
        identity_target=ident["target"],
        intent=intent.value,
        intent_confidence=intent_res.get("confidence"),
        risk_score=risk_res.get("risk_score"),
        risk_level=risk_level,
        consent_status=consent.value,
        permission=permission.value,
        decision=decision,
        reason_code=reason_code,
        reason=reason,
        processing_ms=elapsed_ms,
    )
    db.add(row)
    db.commit()

    logger.info(
        "request_id=%s identity=%s intent=%s risk=%s consent=%s permission=%s "
        "decision=%s reason=%s ms=%d",
        request_id, identity_id, intent.value, risk_level, consent.value,
        permission.value, decision, reason_code, elapsed_ms,
    )

    ai_available = intent_res.get("available", False) or risk_res.get("available", False)
    risk_level_enum = RiskLevel(risk_level) if risk_level in RiskLevel._value2member_map_ else None

    return {
        "request_id": request_id,
        "identity": {
            "identity_id": identity_id,
            "verified": ident["verified"],
            "target": ident["target"],
            "match_score": ident["match_score"],
        },
        "intent": {
            "label": intent,
            "confidence": intent_res.get("confidence", 0.0),
            "ai_available": intent_res.get("available", False),
        },
        "consent": {"status": consent},
        "risk": {
            "score": risk_res.get("risk_score"),
            "level": risk_level_enum,
            "ai_available": risk_res.get("available", False),
        },
        "permission": permission,
        "decision": {
            "action": decision,
            "reason_code": reason_code,
            "reason": reason,
        },
    }


def history(db: Session, requester_user_id: Optional[str] = None, limit: int = 50) -> dict:
    q = db.query(Request)
    if requester_user_id:
        q = q.filter(Request.requester_id == requester_user_id)
    total = q.count()
    rows = q.order_by(Request.created_at.desc()).limit(limit).all()
    items = [
        {
            "request_id": r.request_id,
            "identity_id": r.identity_id,
            "intent": r.intent,
            "risk_level": r.risk_level,
            "decision": r.decision,
            "reason_code": r.reason_code,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
    return {"items": items, "total": total}

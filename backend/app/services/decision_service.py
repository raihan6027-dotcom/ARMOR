"""Request orchestration: the ARMOR AI-safety gateway pipeline.

Coordinates identity verification -> intent analysis (AI) -> permission lookup ->
consent lookup -> risk analysis (AI) -> deterministic policy -> persisted decision.
The AI supplies structured *information* only; the policy engine owns the verdict.

The full decision (reason code, target identity, match score) is stored for the
identity owner and the audit log. The requester only ever receives a
requester-safe view that looks the same whether or not the person in the media
is registered with ARMOR (CLAUDE.md bagian 7, "Pesan seragam").
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.client import AIClient
from app.core.logging import get_logger
from app.models.request import Request
from app.policy.engine import evaluate_policy
from app.schema.common import Decision, IdentityTarget, RiskLevel, normalize_intent
from app.services import consent_service, identity_service, permission_service

logger = get_logger("orchestration")
ai_client = AIClient()

# Requester-facing outcome per decision when the target is someone else. The
# wording must not reveal whether that person is registered, has locked their
# identity, or has answered a consent request.
_REQUESTER_VIEW: dict[str, tuple[str, str]] = {
    Decision.ALLOW.value: ("ALLOWED", "Permintaan ini boleh diproses."),
    Decision.REVIEW.value: (
        "REVIEW_REQUIRED",
        "Permintaan ini perlu ditinjau sebelum diproses.",
    ),
    Decision.DENY.value: (
        "NOT_PERMITTED",
        "Permintaan ini tidak dapat diproses karena berisiko merugikan orang yang ada di dalamnya.",
    ),
}


def _new_request_id() -> str:
    return str(uuid.uuid4())


def requester_decision(decision: str, reason_code: str, reason: str, target: str) -> dict:
    """What the requester may see. Their own identity (SELF) gets the full reason."""
    if target == IdentityTarget.SELF.value:
        return {"action": decision, "reason_code": reason_code, "reason": reason}
    code, message = _REQUESTER_VIEW[decision]
    return {"action": decision, "reason_code": code, "reason": message}


def orchestrate(
    db: Session,
    requester_user_id: str,
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

    # 5. Consent status on record for this requester.
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
        identity_locked=ident["locked"],
    )

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # 8. Persist the full decision (owner + audit view).
    request_id = _new_request_id()
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
        "request_id=%s intent=%s risk=%s consent=%s permission=%s decision=%s reason=%s ms=%d",
        request_id,
        intent.value,
        risk_level,
        consent.value,
        permission.value,
        decision,
        reason_code,
        elapsed_ms,
    )

    risk_level_enum = RiskLevel(risk_level) if risk_level in RiskLevel._value2member_map_ else None

    # 9. Requester-safe response: no target identity id, match score, verification
    #    flag, owner permission or consent state; uniform decision text.
    return {
        "request_id": request_id,
        "identity": {"target": ident["target"]},
        "intent": {
            "label": intent,
            "confidence": intent_res.get("confidence", 0.0),
            "ai_available": intent_res.get("available", False),
        },
        "risk": {
            "score": risk_res.get("risk_score"),
            "level": risk_level_enum,
            "ai_available": risk_res.get("available", False),
        },
        "decision": requester_decision(decision, reason_code, reason, ident["target"]),
    }


def history(db: Session, requester_user_id: str, limit: int = 50) -> dict:
    """The caller's own requests only, in the requester-safe view."""
    q = db.query(Request).filter(Request.requester_id == requester_user_id)
    total = q.count()
    rows = q.order_by(Request.created_at.desc()).limit(limit).all()
    items = []
    for r in rows:
        view = requester_decision(
            r.decision, r.reason_code or "", r.reason or "", r.identity_target or ""
        )
        items.append(
            {
                "request_id": r.request_id,
                "intent": r.intent,
                "risk_level": r.risk_level,
                "decision": r.decision,
                "reason_code": view["reason_code"],
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
        )
    return {"items": items, "total": total}

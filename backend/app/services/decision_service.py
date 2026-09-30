"""Request orchestration: the ARMOR AI-safety gateway pipeline.

identity -> intent (AI) -> risk (AI) -> per-target owner settings (lock,
permission, consent) -> deterministic policy engine -> persisted decision.
The AI supplies structured *information* only; the policy engine owns the verdict.

The full decision (internal reason code, per-target detail, identity id, score)
is stored for the identity owner and the audit log. The requester only ever
receives the requester view produced by the policy engine, which looks the same
whether or not another person in the media is registered.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.client import AIClient
from app.core.logging import get_logger
from app.models.request import Request
from app.policy.defaults import permission_media
from app.policy.engine import PolicyInput, TargetInput, evaluate
from app.schema.common import (
    IdentityTarget,
    MediaType,
    RiskLevel,
    TargetSource,
    normalize_intent,
    normalize_risk,
)
from app.services import consent_service, identity_service, permission_service

logger = get_logger("orchestration")
ai_client = AIClient()


def _new_request_id() -> str:
    return str(uuid.uuid4())


def public_target(target: IdentityTarget) -> str:
    """Requester-facing target: never distinguishes registered from unregistered."""
    return "SELF" if target is IdentityTarget.SELF else "OTHER"


def _build_target(
    db: Session,
    ident: dict,
    requester_user_id: str,
    source: TargetSource,
    media_type: MediaType,
    intent,
) -> TargetInput:
    identity = ident["identity"]
    target_type: IdentityTarget = ident["target"]
    t = TargetInput(
        source=source,
        target_type=target_type,
        identity_id=identity.identity_id if identity is not None else None,
        score=ident["score"],
    )
    if target_type is IdentityTarget.OTHER_REGISTERED:
        media = permission_media(source, media_type)
        t.lock_level = identity_service.lock_level(identity, media)
        t.permission = permission_service.resolve(db, identity.identity_id, intent, media)
        t.consent = consent_service.latest_status_for(
            db, identity.identity_id, requester_user_id, intent.value, media.value
        )
    return t


def orchestrate(
    db: Session,
    requester_user_id: str,
    identity_id: str,
    prompt: str,
    image_bytes: Optional[bytes] = None,
    media_type: Optional[MediaType] = None,
) -> dict:
    started = time.perf_counter()
    if media_type is None:
        media_type = MediaType.IMAGE if image_bytes else MediaType.TEXT_ONLY
    source = TargetSource.FACE if image_bytes else TargetSource.TEXT
    unavailable: list[str] = []

    # 1. Identity: who is in the request.
    ident = identity_service.determine_target(db, requester_user_id, identity_id, image_bytes)
    if not ident["face_available"]:
        unavailable.append("face")

    # 2. Intent (AI).
    intent_res = ai_client.analyze_intent(prompt, image_bytes=image_bytes)
    intent = normalize_intent(intent_res["intent"])

    # 3. Risk (AI): content features only, never consent or permission.
    risk_res = ai_client.analyze_risk(
        identity_target=ident["target"].value,
        intent=intent.value,
        prompt=prompt,
        image_bytes=image_bytes,
    )
    risk_level = normalize_risk(risk_res.get("risk_level"))

    # 4. Owner settings for the target, then the deterministic decision.
    target = _build_target(db, ident, requester_user_id, source, media_type, intent)
    result = evaluate(
        PolicyInput(
            targets=[target],
            intent=intent,
            intent_confidence=intent_res.get("confidence"),
            risk_level=risk_level,
            media_type=media_type,
            unavailable=tuple(unavailable),
            prompt=prompt,
        )
    )

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # 5. Persist the full decision (owner + audit view).
    request_id = _new_request_id()
    db.add(
        Request(
            request_id=request_id,
            requester_id=requester_user_id,
            identity_id=target.identity_id,
            prompt=prompt,
            media_type=media_type.value,
            identity_verified=ident["target"] is IdentityTarget.SELF,
            identity_target=ident["target"].value,
            intent=result.effective_intent.value,
            intent_confidence=intent_res.get("confidence"),
            risk_score=risk_res.get("risk_score"),
            risk_level=risk_level.value if risk_level else None,
            consent_status=target.consent.value,
            permission=target.permission.value if target.permission else None,
            decision=result.decision.value,
            reason_code=result.reason_code,
            reason=result.reason,
            suggestion=result.suggestion,
            requester_code=result.requester_code,
            requester_message=result.requester_message,
            per_target_detail=json.dumps([d.as_dict() for d in result.per_target_detail]),
            processing_ms=elapsed_ms,
        )
    )
    db.commit()

    logger.info(
        "request_id=%s media=%s intent=%s risk=%s decision=%s reason=%s ms=%d",
        request_id,
        media_type.value,
        result.effective_intent.value,
        risk_level.value if risk_level else None,
        result.decision.value,
        result.reason_code,
        elapsed_ms,
    )

    # 6. Requester-safe response.
    return {
        "request_id": request_id,
        "media_type": media_type,
        "identity": {"target": public_target(ident["target"])},
        "intent": {
            "label": intent,
            "confidence": intent_res.get("confidence", 0.0),
            "ai_available": intent_res.get("available", False),
        },
        "risk": {
            "score": risk_res.get("risk_score"),
            "level": risk_level if risk_level in RiskLevel else None,
            "ai_available": risk_res.get("available", False),
        },
        "decision": {
            "action": result.decision,
            "reason_code": result.requester_code,
            "reason": result.requester_message,
            "suggestion": result.suggestion,
            "label_required": result.label_required,
        },
    }


def history(db: Session, requester_user_id: str, limit: int = 50) -> dict:
    """The caller's own requests only, in the requester-safe view."""
    q = db.query(Request).filter(Request.requester_id == requester_user_id)
    total = q.count()
    rows = q.order_by(Request.created_at.desc()).limit(limit).all()
    items = [
        {
            "request_id": r.request_id,
            "intent": r.intent,
            "risk_level": r.risk_level,
            "decision": r.decision,
            "reason_code": r.requester_code,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
    return {"items": items, "total": total}

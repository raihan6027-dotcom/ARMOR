"""Request orchestration: the ARMOR AI-safety gateway pipeline.

media -> Face AI (every face) -> targets -> intent (AI) -> risk (AI) -> per-target
owner settings (lock, permission, consent, trusted circle, guardian) ->
deterministic policy engine -> persisted decision.

The AI supplies structured *information* only; the policy engine owns the verdict.
The client never names who is in the media: targets come only from matching the
media against opt-in enrollments (CLAUDE.md bagian 2).

The full decision (internal reason code, per-target identity and score) is stored
for the identity owner and audit. The requester only receives the requester view,
which looks the same whether or not another person in the media is registered.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.client import AIClient
from app.ai.face import face_ai
from app.core.logging import get_logger
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.policy.defaults import permission_media
from app.policy.engine import PolicyInput, TargetInput, evaluate
from app.schema.common import (
    IdentityTarget,
    Intent,
    MediaType,
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
    """Requester-facing target: never distinguishes registered, unregistered or
    gray-zone matches."""
    return "SELF" if target is IdentityTarget.SELF else "OTHER"


def _owner_settings(
    db: Session,
    t: TargetInput,
    identity,
    requester_user_id: str,
    media_type: MediaType,
    intent: Intent,
) -> None:
    """Resolve lock, permission, consent and guardian flag for a registered target."""
    t.guardian_child = bool(identity.is_child)
    if t.target_type is not IdentityTarget.OTHER_REGISTERED:
        return
    media = permission_media(t.source, media_type)
    t.lock_level = identity_service.lock_level(identity, media)
    t.permission = permission_service.resolve(db, identity.identity_id, intent, media)
    t.consent = consent_service.latest_status_for(
        db, identity.identity_id, requester_user_id, intent.value, media.value
    )


def _face_targets(
    db: Session, image_bytes: bytes, requester_user_id: str
) -> tuple[list[tuple[TargetInput, object, bool]], bool]:
    """Returns ([(target, identity, quality_ok)], face_ai_available)."""
    faces = face_ai.analyze(image_bytes)
    if faces is None:
        return [], False
    index = identity_service.registered_face_embeddings(db) if faces else []
    out = []
    for face in faces:
        match = identity_service.classify_face(face, requester_user_id, index)
        target = TargetInput(
            source=TargetSource.FACE,
            target_type=match.target,
            identity_id=match.identity.identity_id if match.identity else None,
            score=match.score,
        )
        out.append((target, match.identity, face.quality_ok))
        # The embedding of an unregistered face is not kept anywhere.
        face.embedding = None
    return out, True


def orchestrate(
    db: Session,
    requester_user_id: str,
    prompt: str,
    image_bytes: Optional[bytes] = None,
    media_type: Optional[MediaType] = None,
) -> dict:
    started = time.perf_counter()
    if media_type is None:
        media_type = MediaType.IMAGE if image_bytes else MediaType.TEXT_ONLY
    unavailable: list[str] = []

    # 1. Who is in the media (Face AI over every face).
    found: list[tuple[TargetInput, object, bool]] = []
    if image_bytes:
        found, face_ok = _face_targets(db, image_bytes, requester_user_id)
        if not face_ok:
            unavailable.append("face")

    # 2. Intent (AI) and 3. risk (AI): prompt only, never media, never consent.
    intent_res = ai_client.analyze_intent(prompt)
    intent = normalize_intent(intent_res["intent"])
    worst_target = next(
        (t.target_type.value for t, _, _ in found if t.target_type is not IdentityTarget.SELF),
        IdentityTarget.SELF.value if found else "NONE",
    )
    risk_res = ai_client.analyze_risk(
        identity_target=worst_target, intent=intent.value, prompt=prompt
    )
    risk_level = normalize_risk(risk_res.get("risk_level"))

    # 4. Owner settings per registered target, then the deterministic decision.
    targets = []
    for t, identity, _ in found:
        if identity is not None:
            _owner_settings(db, t, identity, requester_user_id, media_type, intent)
        targets.append(t)
    result = evaluate(
        PolicyInput(
            targets=targets,
            intent=intent,
            intent_confidence=intent_res.get("confidence"),
            risk_level=risk_level,
            media_type=media_type,
            unavailable=tuple(unavailable),
            prompt=prompt,
        )
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # 5. Persist the full decision (owner + audit view). No media is stored.
    request_id = _new_request_id()
    db.add(
        Request(
            request_id=request_id,
            requester_id=requester_user_id,
            prompt=prompt,
            media_type=media_type.value,
            intent=result.effective_intent.value,
            intent_confidence=intent_res.get("confidence"),
            risk_score=risk_res.get("risk_score"),
            risk_level=risk_level.value if risk_level else None,
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
    for d in result.per_target_detail:
        db.add(
            RequestTarget(
                request_id=request_id,
                source=d.source.value,
                target_type=d.target_type.value,
                identity_id=d.identity_id,
                score=d.score,
                decision=d.decision.value,
                reason_code=d.reason_code,
            )
        )
    db.commit()

    logger.info(
        "request_id=%s media=%s targets=%d intent=%s risk=%s decision=%s reason=%s ms=%d",
        request_id,
        media_type.value,
        len(targets),
        result.effective_intent.value,
        risk_level.value if risk_level else None,
        result.decision.value,
        result.reason_code,
        elapsed_ms,
    )

    # 6. Requester-safe response.
    people = [
        {"source": t.source.value, "target": public_target(t.target_type), "quality_ok": q}
        for t, _, q in found
    ]
    if not people:
        summary = "NONE"
    elif all(p["target"] == "SELF" for p in people):
        summary = "SELF"
    else:
        summary = "OTHER"
    return {
        "request_id": request_id,
        "media_type": media_type,
        "identity": {"target": summary, "people": people},
        "intent": {
            "label": intent,
            "confidence": intent_res.get("confidence", 0.0),
            "ai_available": intent_res.get("available", False),
        },
        "risk": {
            "score": risk_res.get("risk_score"),
            "level": risk_level,
            "ai_available": risk_res.get("available", False),
        },
        "decision": {
            "action": result.decision,
            "reason_code": result.requester_code,
            "reason": result.requester_message,
            "suggestion": result.suggestion,
            "label_required": result.label_required,
        },
        "checks_unavailable": unavailable,
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

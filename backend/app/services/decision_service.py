"""The ARMOR gateway pipeline (POST /requests).

    media -> Media Router -> Face AI (every face) -> targets
    prompt -> Intent AI -> Risk AI (content features)
    targets + owner settings (lock, permission, consent, trusted circle, guardian)
      -> deterministic policy engine + ARMOR Explain -> decision log + audit -> response

One call per component per request; every stage is timed. The client never
names who is in the media: targets come only from matching the media against
opt-in enrollments (CLAUDE.md bagian 2).

A REVIEW decision is HELD. When an owner answers a consent request, the held
request is re-evaluated automatically from its stored inputs with the owners'
current settings, and the requester is notified of the new decision.

The full decision (internal reason code, per-target identity and score) is kept
for the identity owner and audit. The requester only receives the requester
view, which looks the same whether or not another person is registered.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.client import AIClient
from app.ai.face import face_ai
from app.ai.router import MediaInput, plan
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.ratelimit import limiter
from app.core.timeutil import now
from app.models.identity import Identity
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.policy.defaults import permission_media
from app.policy.engine import POLICY_VERSION, PolicyInput, PolicyResult, TargetInput, evaluate
from app.schema.common import (
    Decision,
    IdentityTarget,
    Intent,
    MediaType,
    RiskLevel,
    TargetSource,
    normalize_intent,
    normalize_risk,
)
from app.services import (
    audit_service,
    circle_service,
    consent_service,
    feedback_service,
    identity_service,
    notify_service,
    permission_service,
)

logger = get_logger("orchestration")
ai_client = AIClient()

_TARGET_PRIORITY = (
    IdentityTarget.OTHER_REGISTERED,
    IdentityTarget.OTHER_UNREGISTERED,
    IdentityTarget.UNCLEAR,
    IdentityTarget.SELF,
)


class _Timer:
    def __init__(self) -> None:
        self.ms: dict[str, int] = {}

    @contextmanager
    def stage(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.ms[name] = self.ms.get(name, 0) + int((time.perf_counter() - start) * 1000)


def public_target(target: IdentityTarget) -> str:
    """Requester-facing target: never distinguishes registered, unregistered or gray zone."""
    return "SELF" if target is IdentityTarget.SELF else "OTHER"


def _worst_target(types: list[IdentityTarget]) -> str:
    """The most exposed person in the request, as a Risk AI feature."""
    for candidate in _TARGET_PRIORITY:
        if candidate in types:
            return candidate.value
    return "NONE"


def _public_factors(top: list[dict]) -> list[dict]:
    """Risk explanation for the requester, minus anything about who is registered."""
    return [f for f in top if f["feature"] != "target_type"]


def _owner_settings(
    db: Session,
    t: TargetInput,
    identity: Identity,
    requester_user_id: str,
    media_type: MediaType,
    intent: Intent,
) -> list:
    """Resolve lock, permission, consent, trusted circle and guardian flag for one
    registered target. Returns the consent rows the decision may rely on."""
    t.guardian_child = bool(identity.is_child)
    if t.target_type is not IdentityTarget.OTHER_REGISTERED:
        return []
    media = permission_media(t.source, media_type)
    t.lock_level = identity_service.lock_level(identity, media)
    t.permission = permission_service.resolve(db, identity.identity_id, intent, media)
    t.consent, row = consent_service.resolve(
        db, identity.identity_id, requester_user_id, intent.value, media.value
    )
    t.in_trusted_circle = circle_service.covers(
        db, identity.identity_id, requester_user_id, intent, media.value
    )
    return [row] if row is not None else []


def _face_targets(
    db: Session, image_bytes: bytes, requester_user_id: str
) -> tuple[list[tuple[TargetInput, Optional[Identity], bool]], bool]:
    faces = face_ai.analyze(image_bytes)
    if faces is None:
        return [], False
    index = identity_service.registered_face_embeddings(db) if faces else []
    out = []
    for face in faces:
        match = identity_service.classify_face(face, requester_user_id, index)
        out.append(
            (
                TargetInput(
                    source=TargetSource.FACE,
                    target_type=match.target,
                    identity_id=match.identity.identity_id if match.identity else None,
                    score=match.score,
                ),
                match.identity,
                face.quality_ok,
            )
        )
        face.embedding = None  # an unregistered face's embedding is not kept anywhere
    return out, True


def _decide(
    db: Session,
    requester_user_id: str,
    targets: list[tuple[TargetInput, Optional[Identity]]],
    intent: Intent,
    confidence: float,
    risk_level: Optional[RiskLevel],
    media_type: MediaType,
    realism: Optional[float],
    unavailable: list[str],
    prompt: str,
) -> tuple[PolicyResult, list]:
    consents = []
    for t, identity in targets:
        if identity is not None:
            consents += _owner_settings(db, t, identity, requester_user_id, media_type, intent)
    result = evaluate(
        PolicyInput(
            targets=[t for t, _ in targets],
            intent=intent,
            intent_confidence=confidence,
            risk_level=risk_level,
            media_type=media_type,
            realism=realism,
            unavailable=tuple(unavailable),
            prompt=prompt,
        )
    )
    return result, consents


def _apply(row: Request, result: PolicyResult) -> None:
    row.decision = result.decision.value
    row.intent = result.effective_intent.value
    row.reason_code = result.reason_code
    row.reason = result.reason
    row.suggestion = result.suggestion
    row.requester_code = result.requester_code
    row.requester_message = result.requester_message
    row.per_target_detail = json.dumps([d.as_dict() for d in result.per_target_detail])
    row.status = "HELD" if result.decision is Decision.REVIEW else "FINAL"


def _after_decision(
    db: Session, row: Request, result: PolicyResult, consents: list, event: str
) -> None:
    """Spend single-use consent, tell owners about blocked attempts, write the audit log."""
    if result.decision is Decision.ALLOW:
        consent_service.mark_used(db, consents)
    owners_notified = set()
    for d in result.per_target_detail:
        if (
            result.decision is Decision.DENY
            and d.target_type is IdentityTarget.OTHER_REGISTERED
            and d.identity_id
        ):
            owner = db.query(Identity).filter(Identity.identity_id == d.identity_id).first()
            if owner is not None and owner.user_id not in owners_notified:
                owners_notified.add(owner.user_id)
                notify_service.notify(
                    db,
                    owner.user_id,
                    "USE_BLOCKED",
                    "Upaya penggunaan identitasmu diblokir",
                    "ARMOR menolak sebuah permintaan yang memakai identitasmu.",
                    {"request_id": row.request_id},
                )
    audit_service.record(
        db,
        event,
        row.requester_id,
        {
            "request_id": row.request_id,
            "decision": row.decision,
            "reason_code": row.reason_code,
            "status": row.status,
            "targets": [
                {
                    "type": d.target_type.value,
                    "identity_id": d.identity_id,
                    "decision": d.decision.value,
                }
                for d in result.per_target_detail
            ],
            "model_version": json.loads(row.model_version or "{}"),
        },
    )


def orchestrate(
    db: Session,
    requester_user_id: str,
    prompt: str,
    image_bytes: Optional[bytes] = None,
    media_type: Optional[MediaType] = None,
    video_bytes: Optional[bytes] = None,
    audio_bytes: Optional[bytes] = None,
    allow_training: bool = False,
) -> dict:
    limiter.check(f"gateway:{requester_user_id}", settings.gateway_requests_per_minute, 60)
    started = time.perf_counter()
    timer = _Timer()

    # 1. Media Router.
    with timer.stage("router"):
        route = plan(
            MediaInput(
                media_type=media_type or MediaType.TEXT_ONLY,
                image=image_bytes,
                video=video_bytes,
                audio=audio_bytes,
            )
        )
    unavailable = list(route.unavailable)

    # 2. Who is in the media.
    found: list[tuple[TargetInput, Optional[Identity], bool]] = []
    if "face" in route.run and image_bytes:
        with timer.stage("face"):
            found, face_ok = _face_targets(db, image_bytes, requester_user_id)
        if not face_ok:
            unavailable.append("face")

    # 3. Intent and 4. risk: prompt and content features only.
    with timer.stage("intent"):
        intent_res = ai_client.analyze_intent(prompt)
    intent = normalize_intent(intent_res["intent"])
    with timer.stage("risk"):
        features = ai_client.risk_features(
            prompt,
            intent.value,
            intent_res.get("confidence", 0.0),
            _worst_target([t.target_type for t, _, _ in found]),
            route.media_type.value,
        )
        risk_res = ai_client.analyze_risk(features)
    risk_level = normalize_risk(risk_res.get("risk_level"))

    # 5. Owner settings and the deterministic decision.
    with timer.stage("policy"):
        result, consents = _decide(
            db,
            requester_user_id,
            [(t, identity) for t, identity, _ in found],
            intent,
            intent_res.get("confidence", 0.0),
            risk_level,
            route.media_type,
            features.realism,
            unavailable,
            prompt,
        )

    versions = {
        "intent": intent_res.get("model_version"),
        "risk": risk_res.get("model_version"),
        "policy": POLICY_VERSION,
    }
    if "face" in route.run:
        versions["face"] = f"insightface-{settings.insightface_model}"

    # 6. Persist the full decision (owner + audit view). No media is stored.
    request_id = str(uuid.uuid4())
    with timer.stage("persist"):
        row = Request(
            request_id=request_id,
            requester_id=requester_user_id,
            prompt=prompt,
            media_type=route.media_type.value,
            allow_training=allow_training,
            intent_original=intent.value,
            intent_confidence=intent_res.get("confidence"),
            risk_score=risk_res.get("risk_score"),
            risk_level=risk_level.value if risk_level else None,
            unavailable=json.dumps(unavailable),
            risk_features=json.dumps(
                {"features": features.as_dict(), "top": risk_res.get("top_features", [])}
            ),
            model_version=json.dumps(versions, sort_keys=True),
        )
        _apply(row, result)
        db.add(row)
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
        _after_decision(db, row, result, consents, "DECISION")
        row.processing_ms = int((time.perf_counter() - started) * 1000)
        db.commit()
    row.stage_ms = json.dumps(timer.ms)
    db.commit()

    logger.info(
        "request_id=%s media=%s targets=%d intent=%s risk=%s decision=%s reason=%s ms=%d",
        request_id,
        route.media_type.value,
        len(found),
        result.effective_intent.value,
        risk_level.value if risk_level else None,
        result.decision.value,
        result.reason_code,
        row.processing_ms,
    )

    people = [
        {"source": t.source.value, "target": public_target(t.target_type), "quality_ok": q}
        for t, _, q in found
    ]
    return {
        "request_id": request_id,
        "status": row.status,
        "media_type": route.media_type,
        "identity": {"target": _summary(people), "people": people},
        "intent": {
            "label": intent,
            "confidence": intent_res.get("confidence", 0.0),
            "ai_available": intent_res.get("available", False),
        },
        "risk": {
            "score": risk_res.get("risk_score"),
            "level": risk_level,
            "ai_available": risk_res.get("available", False),
            "top_features": _public_factors(risk_res.get("top_features", [])),
        },
        "decision": _public_decision(row, result.label_required),
        "checks_unavailable": unavailable,
        "timing_ms": timer.ms,
    }


def _summary(people: list[dict]) -> str:
    if not people:
        return "NONE"
    return "SELF" if all(p["target"] == "SELF" for p in people) else "OTHER"


def _public_decision(row: Request, label_required: bool | None = None) -> dict:
    return {
        "action": row.decision,
        "reason_code": row.requester_code,
        "reason": row.requester_message,
        "suggestion": row.suggestion,
        "label_required": (
            row.decision == Decision.ALLOW.value if label_required is None else label_required
        ),
    }


def reevaluate(db: Session, request_id: str) -> Optional[Request]:
    """Re-decide a HELD request from its stored inputs with the owners' current
    settings (after a consent answer). No media is needed: targets were stored."""
    row = db.query(Request).filter(Request.request_id == request_id).first()
    if row is None or row.status != "HELD":
        return row
    stored = (
        db.query(RequestTarget)
        .filter(RequestTarget.request_id == request_id)
        .order_by(RequestTarget.id)
        .all()
    )
    targets: list[tuple[TargetInput, Optional[Identity]]] = []
    for s in stored:
        identity = (
            db.query(Identity).filter(Identity.identity_id == s.identity_id).first()
            if s.identity_id
            else None
        )
        target_type = IdentityTarget(s.target_type)
        if target_type is IdentityTarget.OTHER_REGISTERED and identity is None:
            target_type = IdentityTarget.OTHER_UNREGISTERED  # enrollment deleted meanwhile
        targets.append(
            (
                TargetInput(
                    source=TargetSource(s.source),
                    target_type=target_type,
                    identity_id=s.identity_id if identity else None,
                    score=s.score,
                ),
                identity,
            )
        )
    feats = json.loads(row.risk_features or "{}").get("features", {})
    previous = row.decision
    result, consents = _decide(
        db,
        row.requester_id,
        targets,
        Intent(row.intent_original or row.intent),
        row.intent_confidence or 0.0,
        normalize_risk(row.risk_level),
        MediaType(row.media_type or MediaType.IMAGE.value),
        feats.get("realism"),
        json.loads(row.unavailable or "[]"),
        row.prompt,
    )
    _apply(row, result)
    row.updated_at = now()
    for s, d in zip(stored, result.per_target_detail, strict=True):
        s.decision, s.reason_code = d.decision.value, d.reason_code
    _after_decision(db, row, result, consents, "DECISION_REEVALUATED")
    if row.status == "FINAL":
        feedback_service.record(db, row, "REVIEW_RESOLVED")
    if row.decision != previous:
        notify_service.notify(
            db,
            row.requester_id,
            "REQUEST_UPDATED",
            "Status permintaanmu berubah",
            row.requester_message or "",
            {"request_id": row.request_id, "decision": row.decision},
        )
    db.commit()
    db.refresh(row)
    return row


def get_own(db: Session, request_id: str, requester_user_id: str) -> dict:
    row = db.query(Request).filter(Request.request_id == request_id).first()
    if row is None or row.requester_id != requester_user_id:
        raise NotFoundError(f"Request '{request_id}' not found.")
    return {
        "request_id": row.request_id,
        "status": row.status,
        "prompt": row.prompt,
        "media_type": row.media_type,
        "decision": _public_decision(row),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def history(db: Session, requester_user_id: str, limit: int = 50) -> dict:
    """The caller's own requests only, in the requester-safe view."""
    q = db.query(Request).filter(Request.requester_id == requester_user_id)
    total = q.count()
    rows = q.order_by(Request.created_at.desc(), Request.id.desc()).limit(limit).all()
    items = [
        {
            "request_id": r.request_id,
            "status": r.status,
            "intent": r.intent,
            "risk_level": r.risk_level,
            "decision": r.decision,
            "reason_code": r.requester_code,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
    return {"items": items, "total": total}

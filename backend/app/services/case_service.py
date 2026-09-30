"""Cases: appeals against DENY and false-enrollment disputes (Fase 6 task 9).

Flow: SUBMITTED -> REVIEWING -> RESOLVED. New cases are assigned to the REVIEWER
with the fewest open cases; a REVIEWER sees only cases assigned to them, an ADMIN
sees all. Every reviewer action is written to the audit log.

Appeals: a reviewer does not override the policy engine (CLAUDE.md bagian 2,
prinsip 4). They either UPHOLD the decision or RELABEL it with a corrected intent
and/or risk level; the policy engine then decides again from the corrected
labels. Corrections are kept for the learning loop (Fase 6b).

Disputes: the reporter re-verifies live (three captures, same defenses as
enrollment). If the face matches an identity they do not own, a case opens on
that identity. The reviewer can freeze the identity (owner controls paused,
protection continues), then TRANSFER ownership to the reporter, DELETE the false
enrollment, or REJECT the dispute.
"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ArmorError, ForbiddenError, NotFoundError
from app.models.biometric_consent import BiometricConsent
from app.models.case import Case, CaseEvent
from app.models.consent import Consent
from app.models.identity import Identity
from app.models.owner import CircleMember
from app.models.permission import Permission
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.models.user import User
from app.schema.common import BiometricMedia, Decision, Intent, LockLevel, RiskLevel
from app.services import audit_service, identity_service, notify_service

STATUS_ID = {"SUBMITTED": "Diajukan", "REVIEWING": "Ditinjau", "RESOLVED": "Selesai"}
APPEAL_OUTCOMES = ("UPHOLD", "RELABEL")
DISPUTE_OUTCOMES = ("TRANSFER", "DELETE_ENROLLMENT", "REJECT")


def _assign_reviewer(db: Session) -> Optional[str]:
    reviewers = db.query(User).filter(User.role == "REVIEWER").all()
    if not reviewers:
        return None

    def load(u: User) -> int:
        return (
            db.query(Case)
            .filter(Case.assigned_reviewer_id == u.user_id, Case.status != "RESOLVED")
            .count()
        )

    return min(reviewers, key=lambda u: (load(u), u.created_at)).user_id


def _event(db: Session, case: Case, status: str, note: str | None, actor: str | None) -> None:
    db.add(CaseEvent(case_id=case.case_id, status=status, note=note, actor_id=actor))


def _open(
    db: Session,
    kind: str,
    reporter_id: str,
    note: str | None,
    identity_id: str | None = None,
    request_id: str | None = None,
    media: str | None = None,
    score: float | None = None,
) -> Case:
    case = Case(
        case_id=str(uuid.uuid4()),
        kind=kind,
        reporter_id=reporter_id,
        identity_id=identity_id,
        request_id=request_id,
        media=media,
        verification_score=score,
        note=note,
        assigned_reviewer_id=_assign_reviewer(db),
    )
    db.add(case)
    _event(db, case, "SUBMITTED", None, reporter_id)
    audit_service.record(
        db,
        "CASE_OPENED",
        reporter_id,
        {
            "case_id": case.case_id,
            "kind": kind,
            "request_id": request_id,
            "identity_id": identity_id,
        },
    )
    return case


def open_dispute_from_enrollment(
    db: Session, reporter_id: str, identity_id: str, media: str, score: float | None
) -> Case:
    """Called when an enrollment is refused because the face is already registered."""
    return _open(
        db,
        "DISPUTE",
        reporter_id,
        "Dibuka otomatis: pendaftaran cocok dengan identitas yang sudah ada.",
        identity_id=identity_id,
        media=media,
        score=score,
    )


def create_appeal(db: Session, reporter_id: str, request_id: str, note: str) -> Case:
    req = db.query(Request).filter(Request.request_id == request_id).first()
    if req is None or req.requester_id != reporter_id:
        raise NotFoundError(f"Request '{request_id}' not found.")
    if req.decision != Decision.DENY.value:
        raise ArmorError("APPEAL_NOT_APPLICABLE", "Only a DENY decision can be appealed.", 409)
    open_case = (
        db.query(Case)
        .filter(Case.request_id == request_id, Case.kind == "APPEAL", Case.status != "RESOLVED")
        .first()
    )
    if open_case is not None:
        raise ArmorError(
            "APPEAL_EXISTS",
            "This request already has an open appeal.",
            409,
            {"case_id": open_case.case_id},
        )
    case = _open(db, "APPEAL", reporter_id, note, request_id=request_id)
    db.commit()
    db.refresh(case)
    return case


def create_dispute(
    db: Session,
    reporter_id: str,
    images: list[bytes],
    consent_agreed: bool,
    consent_version: str,
    note: str | None,
) -> Case:
    """Live re-verification of the reporter's own face against registered identities."""
    identity_service.require_consent(consent_agreed, consent_version, BiometricMedia.FACE)
    mean = identity_service.check_enrollment_captures(images)
    others = [
        (ident, vec)
        for ident, vec in identity_service.registered_face_embeddings(db)
        if ident.user_id != reporter_id
    ]
    match, score = identity_service.best_match(mean, others)
    if match is None or score < settings.face_match_threshold - settings.face_gray_margin:
        raise ArmorError(
            "NO_MATCHING_ENROLLMENT",
            "Your face does not match an identity registered to another account.",
            422,
        )
    case = _open(
        db,
        "DISPUTE",
        reporter_id,
        note,
        identity_id=match.identity_id,
        media="FACE",
        score=round(score, 4),
    )
    db.commit()
    db.refresh(case)
    return case


def _get(db: Session, case_id: str) -> Case:
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if case is None:
        raise NotFoundError(f"Case '{case_id}' not found.")
    return case


def _require_reviewer(case: Case, user: User) -> None:
    if user.role == "ADMIN":
        return
    if user.role != "REVIEWER" or case.assigned_reviewer_id != user.user_id:
        raise NotFoundError(f"Case '{case.case_id}' not found.")


def _timeline(db: Session, case: Case) -> list[dict]:
    events = (
        db.query(CaseEvent).filter(CaseEvent.case_id == case.case_id).order_by(CaseEvent.id).all()
    )
    return [
        {
            "status": e.status,
            "label": STATUS_ID.get(e.status, e.status),
            "note": e.note,
            "at": e.created_at.isoformat(),
        }
        for e in events
    ]


def reporter_view(db: Session, case: Case) -> dict:
    """What the reporter sees: status and timeline, never the disputed identity."""
    return {
        "case_id": case.case_id,
        "kind": case.kind,
        "status": case.status,
        "status_label": STATUS_ID[case.status],
        "request_id": case.request_id,
        "note": case.note,
        "outcome": case.outcome,
        "resolution_note": case.resolution_note,
        "timeline": _timeline(db, case),
        "created_at": case.created_at.isoformat(),
    }


def reviewer_view(db: Session, case: Case) -> dict:
    """Case detail for the reviewer. No media: only target types and scores."""
    out = reporter_view(db, case) | {
        "assigned_reviewer_id": case.assigned_reviewer_id,
        "reporter_email": _email(db, case.reporter_id),
        "corrected_intent": case.corrected_intent,
        "corrected_risk": case.corrected_risk,
    }
    if case.kind == "APPEAL":
        req = db.query(Request).filter(Request.request_id == case.request_id).first()
        targets = db.query(RequestTarget).filter(RequestTarget.request_id == case.request_id).all()
        out["request"] = {
            "prompt": req.prompt,
            "media_type": req.media_type,
            "decision": req.decision,
            "reason_code": req.reason_code,
            "reason": req.reason,
            "intent": req.intent_original,
            "intent_confidence": req.intent_confidence,
            "risk_level": req.risk_level,
            "risk_score": req.risk_score,
            "risk_features": json.loads(req.risk_features or "{}"),
            "model_version": json.loads(req.model_version or "{}"),
            "targets": [
                {
                    "source": t.source,
                    "target_type": t.target_type,
                    "score": t.score,
                    "decision": t.decision,
                }
                for t in targets
            ],
        }
        out["audit"] = audit_service.for_subject(db, "request_id", case.request_id)
    else:
        identity = db.query(Identity).filter(Identity.identity_id == case.identity_id).first()
        out["dispute"] = {
            "identity_id": case.identity_id,
            "media": case.media,
            "verification_score": case.verification_score,
            "identity_exists": identity is not None,
            "identity_frozen": bool(identity and identity.frozen),
            "current_owner_email": _email(db, identity.user_id) if identity else None,
        }
        out["audit"] = audit_service.for_subject(db, "case_id", case.case_id)
    return out


def _email(db: Session, user_id: str | None) -> str | None:
    user = db.query(User).filter(User.user_id == user_id).first() if user_id else None
    return user.email if user else None


def list_for(db: Session, user: User) -> list[dict]:
    q = db.query(Case)
    if user.role == "REVIEWER":
        q = q.filter(Case.assigned_reviewer_id == user.user_id)
    elif user.role != "ADMIN":
        q = q.filter(Case.reporter_id == user.user_id)
    rows = q.order_by(Case.created_at).all()
    return [
        {
            "case_id": c.case_id,
            "kind": c.kind,
            "status": c.status,
            "status_label": STATUS_ID[c.status],
            "created_at": c.created_at.isoformat(),
            "priority": "TINGGI" if c.kind == "DISPUTE" else "NORMAL",
        }
        for c in rows
    ]


def detail(db: Session, user: User, case_id: str) -> dict:
    case = _get(db, case_id)
    if case.reporter_id == user.user_id and user.role not in ("REVIEWER", "ADMIN"):
        return reporter_view(db, case)
    _require_reviewer(case, user)
    return reviewer_view(db, case)


def _notify_reporter(db: Session, case: Case) -> None:
    notify_service.notify(
        db,
        case.reporter_id,
        "CASE_STATUS",
        f"Kasus {STATUS_ID[case.status].lower()}",
        f"Status kasusmu sekarang: {STATUS_ID[case.status]}.",
        {"case_id": case.case_id},
    )


def start_review(db: Session, reviewer: User, case_id: str) -> Case:
    case = _get(db, case_id)
    _require_reviewer(case, reviewer)
    if case.status == "RESOLVED":
        raise ArmorError("CASE_RESOLVED", "This case is already resolved.", 409)
    if case.status == "SUBMITTED":
        case.status = "REVIEWING"
        _event(db, case, "REVIEWING", None, reviewer.user_id)
        audit_service.record(db, "CASE_REVIEWING", reviewer.user_id, {"case_id": case.case_id})
        _notify_reporter(db, case)
    db.commit()
    db.refresh(case)
    return case


def freeze(db: Session, reviewer: User, case_id: str) -> Case:
    case = _get(db, case_id)
    _require_reviewer(case, reviewer)
    if case.kind != "DISPUTE":
        raise ArmorError("NOT_A_DISPUTE", "Only a dispute can freeze an identity.", 409)
    identity = db.query(Identity).filter(Identity.identity_id == case.identity_id).first()
    if identity is None:
        raise NotFoundError("The disputed identity no longer exists.")
    identity.frozen = True
    audit_service.record(
        db,
        "IDENTITY_FROZEN",
        reviewer.user_id,
        {"case_id": case.case_id, "identity_id": identity.identity_id},
    )
    if case.status == "SUBMITTED":
        case.status = "REVIEWING"
        _event(db, case, "REVIEWING", "Identitas dibekukan selama peninjauan.", reviewer.user_id)
        _notify_reporter(db, case)
    db.commit()
    db.refresh(case)
    return case


def _relabel(
    db: Session, req: Request, intent: Optional[Intent], risk: Optional[RiskLevel]
) -> None:
    """Re-decide a request with corrected labels. The policy engine decides."""
    from app.services import decision_service  # local import: avoids a cycle

    if intent is not None:
        req.intent_original = intent.value
    if risk is not None:
        req.risk_level = risk.value
    req.status = "HELD"  # let reevaluate() run on it
    db.flush()
    decision_service.reevaluate(db, req.request_id)


def _transfer(db: Session, case: Case, identity: Identity) -> None:
    previous = identity.user_id
    identity.user_id = case.reporter_id
    identity.frozen = False
    identity.face_lock = identity.voice_lock = LockLevel.NONE.value
    identity.status = "active"
    # The false owner's settings do not carry over to the real owner.
    db.query(Permission).filter(Permission.identity_id == identity.identity_id).delete()
    db.query(CircleMember).filter(CircleMember.identity_id == identity.identity_id).delete()
    db.query(Consent).filter(
        Consent.identity_id == identity.identity_id, Consent.status == "PENDING"
    ).delete()
    for rec in db.query(BiometricConsent).filter(
        BiometricConsent.identity_id == identity.identity_id
    ):
        rec.user_id = case.reporter_id
    db.add(
        BiometricConsent(
            record_id=str(uuid.uuid4()),
            user_id=case.reporter_id,
            identity_id=identity.identity_id,
            media=case.media or "FACE",
            text_version=settings.consent_text_face,
        )
    )
    notify_service.notify(
        db,
        previous,
        "CASE_STATUS",
        "Kepemilikan identitas dipindahkan",
        "Peninjau memutuskan identitas yang kamu daftarkan milik orang lain.",
        {"case_id": case.case_id},
    )


def _delete_enrollment(db: Session, case: Case, identity: Identity) -> None:
    previous = identity.user_id
    db.query(Permission).filter(Permission.identity_id == identity.identity_id).delete()
    db.query(CircleMember).filter(CircleMember.identity_id == identity.identity_id).delete()
    db.query(Consent).filter(Consent.identity_id == identity.identity_id).delete()
    db.query(BiometricConsent).filter(BiometricConsent.identity_id == identity.identity_id).delete()
    db.delete(identity)
    notify_service.notify(
        db,
        previous,
        "CASE_STATUS",
        "Pendaftaran identitas dihapus",
        "Peninjau menghapus pendaftaran wajah yang terbukti bukan milikmu.",
        {"case_id": case.case_id},
    )


def resolve(
    db: Session,
    reviewer: User,
    case_id: str,
    outcome: str,
    note: str | None,
    corrected_intent: Optional[Intent] = None,
    corrected_risk: Optional[RiskLevel] = None,
) -> Case:
    case = _get(db, case_id)
    _require_reviewer(case, reviewer)
    if case.status == "RESOLVED":
        raise ArmorError("CASE_RESOLVED", "This case is already resolved.", 409)
    allowed = APPEAL_OUTCOMES if case.kind == "APPEAL" else DISPUTE_OUTCOMES
    if outcome not in allowed:
        raise ArmorError("INVALID_OUTCOME", f"Outcome must be one of {allowed}.", 422)

    case.corrected_intent = corrected_intent.value if corrected_intent else None
    case.corrected_risk = corrected_risk.value if corrected_risk else None
    if case.kind == "APPEAL":
        req = db.query(Request).filter(Request.request_id == case.request_id).first()
        if outcome == "RELABEL":
            if corrected_intent is None and corrected_risk is None:
                raise ArmorError(
                    "RELABEL_NEEDS_LABEL", "Give the corrected intent and/or risk level.", 422
                )
            _relabel(db, req, corrected_intent, corrected_risk)
    else:
        identity = db.query(Identity).filter(Identity.identity_id == case.identity_id).first()
        if identity is None and outcome != "REJECT":
            raise NotFoundError("The disputed identity no longer exists.")
        if outcome == "TRANSFER":
            if identity_service.own_identity(db, case.reporter_id) is not None:
                raise ArmorError(
                    "REPORTER_HAS_IDENTITY", "The reporter already owns an identity.", 409
                )
            _transfer(db, case, identity)
        elif outcome == "DELETE_ENROLLMENT":
            _delete_enrollment(db, case, identity)
        elif identity is not None:
            identity.frozen = False

    case.outcome = outcome
    case.resolution_note = note
    case.status = "RESOLVED"
    _event(db, case, "RESOLVED", note, reviewer.user_id)
    audit_service.record(
        db,
        "CASE_RESOLVED",
        reviewer.user_id,
        {
            "case_id": case.case_id,
            "outcome": outcome,
            "request_id": case.request_id,
            "identity_id": case.identity_id,
            "corrected_intent": case.corrected_intent,
            "corrected_risk": case.corrected_risk,
        },
    )
    _notify_reporter(db, case)
    db.commit()
    db.refresh(case)
    return case


def assign(db: Session, admin: User, case_id: str, reviewer_email: str) -> Case:
    if admin.role != "ADMIN":
        raise ForbiddenError("Only an admin can assign cases.")
    case = _get(db, case_id)
    reviewer = (
        db.query(User).filter(User.email == reviewer_email.lower(), User.role == "REVIEWER").first()
    )
    if reviewer is None:
        raise NotFoundError("No reviewer with that e-mail.")
    case.assigned_reviewer_id = reviewer.user_id
    audit_service.record(
        db,
        "CASE_ASSIGNED",
        admin.user_id,
        {"case_id": case.case_id, "reviewer_id": reviewer.user_id},
    )
    db.commit()
    db.refresh(case)
    return case

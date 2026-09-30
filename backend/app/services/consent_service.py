"""Consent lifecycle (lapis 2).

* The requester never names an identity: they ask for consent on one of their own
  REVIEW requests, and ARMOR routes it to the owner of every registered person
  found in it. The answer to the requester does not reveal how many owners (if
  any) were asked.
* Rate limit: at most CONSENT_REQUESTS_PER_DAY requests per requester per
  identity per day. An owner can block a requester.
* The owner answers with a scope (intent, media) and a validity: once, 1, 7 or
  30 days, or until a date. Single-use consent is spent by the first ALLOW that
  relies on it. Expired, used and revoked consent counts as NONE.
* After an answer, the held request is re-evaluated automatically.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ArmorError, ForbiddenError, NotFoundError
from app.core.timeutil import naive, now
from app.models.consent import Consent
from app.models.identity import Identity
from app.models.owner import Block
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.models.user import User
from app.policy.defaults import permission_media
from app.schema.common import (
    BiometricMedia,
    ConsentStatus,
    Decision,
    IdentityTarget,
    Intent,
    MediaType,
    TargetSource,
    normalize_consent,
)
from app.services import audit_service, identity_service, notify_service

VALIDITY_DAYS = {"DAYS_1": 1, "DAYS_7": 7, "DAYS_30": 30}
VALIDITIES = ("ONCE", "DAYS_1", "DAYS_7", "DAYS_30", "UNTIL")


def _own_request(db: Session, request_id: str, user_id: str) -> Request:
    row = db.query(Request).filter(Request.request_id == request_id).first()
    if row is None or row.requester_id != user_id:
        raise NotFoundError(f"Request '{request_id}' not found.")
    return row


def _owner_of(db: Session, identity_id: str) -> Optional[str]:
    identity = db.query(Identity).filter(Identity.identity_id == identity_id).first()
    return identity.user_id if identity else None


def _is_blocked(db: Session, owner_id: str, requester_id: str) -> bool:
    return (
        db.query(Block)
        .filter(Block.owner_id == owner_id, Block.requester_id == requester_id)
        .first()
        is not None
    )


def _sent_today(db: Session, identity_id: str, requester_id: str) -> int:
    return (
        db.query(Consent)
        .filter(
            Consent.identity_id == identity_id,
            Consent.requester_id == requester_id,
            Consent.created_at >= now() - timedelta(days=1),
        )
        .count()
    )


def request_for(
    db: Session,
    request_id: str,
    requester_id: str,
    intent: Optional[Intent] = None,
    media: Optional[BiometricMedia] = None,
) -> int:
    """Ask the owners of every registered person in one of your REVIEW requests.
    Returns how many consent requests were created (never shown to the requester)."""
    req = _own_request(db, request_id, requester_id)
    if req.decision != Decision.REVIEW.value:
        raise ArmorError(
            "CONSENT_NOT_APPLICABLE",
            "Consent can only be requested for a request that is waiting for review.",
            409,
        )
    scope_intent = (intent or Intent(req.intent_original or req.intent)).value
    media_type = MediaType(req.media_type) if req.media_type else MediaType.IMAGE
    targets = (
        db.query(RequestTarget)
        .filter(
            RequestTarget.request_id == request_id,
            RequestTarget.target_type == IdentityTarget.OTHER_REGISTERED.value,
        )
        .all()
    )
    created = blocked = limited = 0
    for t in targets:
        owner = _owner_of(db, t.identity_id)
        if owner is None:
            continue
        if _is_blocked(db, owner, requester_id):
            blocked += 1
            continue
        existing = (
            db.query(Consent)
            .filter(
                Consent.identity_id == t.identity_id,
                Consent.requester_id == requester_id,
                Consent.request_id == request_id,
            )
            .first()
        )
        if existing is not None:
            continue
        if _sent_today(db, t.identity_id, requester_id) >= settings.consent_requests_per_day:
            limited += 1
            continue
        consent = Consent(
            consent_id=str(uuid.uuid4()),
            identity_id=t.identity_id,
            requester_id=requester_id,
            intent=scope_intent,
            media=(media or permission_media(TargetSource(t.source), media_type)).value,
            request_id=request_id,
            status=ConsentStatus.PENDING.value,
        )
        db.add(consent)
        requester = db.query(User).filter(User.user_id == requester_id).first()
        notify_service.notify(
            db,
            owner,
            "CONSENT_REQUEST",
            "Permintaan persetujuan baru",
            f"{requester.email if requester else 'Seseorang'} meminta izin memakai identitasmu "
            f"untuk tujuan {scope_intent}.",
            {"consent_id": consent.consent_id},
        )
        audit_service.record(
            db,
            "CONSENT_REQUESTED",
            requester_id,
            {
                "consent_id": consent.consent_id,
                "request_id": request_id,
                "identity_id": t.identity_id,
            },
        )
        created += 1
    db.commit()
    if targets and created == 0 and blocked == len(targets):
        raise ArmorError("CONSENT_BLOCKED", "The owner does not accept requests from you.", 403)
    if targets and created == 0 and limited:
        raise ArmorError(
            "CONSENT_RATE_LIMITED",
            f"At most {settings.consent_requests_per_day} consent requests per person per day.",
            429,
        )
    return created


def status_for_request(db: Session, request_id: str, requester_id: str) -> ConsentStatus:
    """DENIED if any owner refused, GRANTED when every asked owner agreed, else PENDING."""
    _own_request(db, request_id, requester_id)
    rows = (
        db.query(Consent)
        .filter(Consent.request_id == request_id, Consent.requester_id == requester_id)
        .all()
    )
    statuses = {normalize_consent(r.status) for r in rows}
    if ConsentStatus.DENIED in statuses:
        return ConsentStatus.DENIED
    if statuses and statuses == {ConsentStatus.GRANTED}:
        return ConsentStatus.GRANTED
    return ConsentStatus.PENDING


def _get(db: Session, consent_id: str) -> Consent:
    consent = db.query(Consent).filter(Consent.consent_id == consent_id).first()
    if consent is None:
        raise NotFoundError(f"Consent '{consent_id}' not found.")
    return consent


def get_for_owner(db: Session, consent_id: str, user_id: str) -> Consent:
    consent = _get(db, consent_id)
    if _owner_of(db, consent.identity_id) != user_id:
        raise NotFoundError(f"Consent '{consent_id}' not found.")
    return consent


def effective(consent: Consent) -> ConsentStatus:
    """What the policy engine sees for one consent row."""
    status = normalize_consent(consent.status)
    if status is ConsentStatus.GRANTED:
        if consent.revoked_at is not None or consent.used_at is not None:
            return ConsentStatus.NONE
        if consent.expires_at is not None and consent.expires_at <= now():
            return ConsentStatus.NONE
    return status


def state_label(consent: Consent) -> str:
    """For the inbox: PENDING, GRANTED, DENIED, REVOKED, EXPIRED or USED."""
    if consent.status == ConsentStatus.GRANTED.value:
        if consent.revoked_at is not None:
            return "REVOKED"
        if consent.used_at is not None:
            return "USED"
        if consent.expires_at is not None and consent.expires_at <= now():
            return "EXPIRED"
    return consent.status


def as_owner_dict(db: Session, c: Consent) -> dict:
    requester = db.query(User).filter(User.user_id == c.requester_id).first()
    req = (
        db.query(Request).filter(Request.request_id == c.request_id).first()
        if c.request_id
        else None
    )
    return {
        "consent_id": c.consent_id,
        "identity_id": c.identity_id,
        # The requester asked for consent, so they are identified to the owner.
        "requester_email": requester.email if requester else None,
        "intent": c.intent,
        "media": c.media,
        "prompt": req.prompt if req else None,
        "media_type": req.media_type if req else None,
        "status": c.status,
        "state": state_label(c),
        "validity": c.validity,
        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        "answered_at": c.answered_at.isoformat() if c.answered_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def inbox(db: Session, user_id: str, status: Optional[str] = None) -> list[dict]:
    """Consent requests about identities the user owns, newest first."""
    ids = [i.identity_id for i in db.query(Identity).filter(Identity.user_id == user_id).all()]
    if not ids:
        return []
    q = db.query(Consent).filter(Consent.identity_id.in_(ids))
    if status == "pending":
        q = q.filter(Consent.status == ConsentStatus.PENDING.value)
    elif status == "answered":
        q = q.filter(Consent.status != ConsentStatus.PENDING.value)
    return [as_owner_dict(db, c) for c in q.order_by(Consent.created_at.desc()).all()]


def pending_count(db: Session, user_id: str) -> int:
    ids = [i.identity_id for i in db.query(Identity).filter(Identity.user_id == user_id).all()]
    if not ids:
        return 0
    return (
        db.query(Consent)
        .filter(Consent.identity_id.in_(ids), Consent.status == ConsentStatus.PENDING.value)
        .count()
    )


def _expiry(validity: str, until: Optional[datetime], at: datetime) -> Optional[datetime]:
    if validity == "ONCE":
        return None
    if validity in VALIDITY_DAYS:
        return at + timedelta(days=VALIDITY_DAYS[validity])
    if validity == "UNTIL":
        if until is None:
            raise ArmorError("UNTIL_REQUIRED", "Pick the last day the consent is valid.", 422)
        end = naive(until)
        if end.time() == time(0, 0):
            end = end + timedelta(days=1)  # a date means "through the end of that day"
        if end <= at:
            raise ArmorError("UNTIL_IN_PAST", "That date has already passed.", 422)
        return end
    raise ArmorError("INVALID_VALIDITY", f"Validity must be one of {VALIDITIES}.", 422)


def respond(
    db: Session,
    consent_id: str,
    user_id: str,
    action: str,
    scope_intent: Optional[Intent] = None,
    scope_media: Optional[BiometricMedia] = None,
    validity: str = "ONCE",
    until: Optional[datetime] = None,
) -> Consent:
    """APPROVE (with scope and validity), DENY, or BLOCK (deny and block the requester)."""
    consent = _get(db, consent_id)
    identity = db.query(Identity).filter(Identity.identity_id == consent.identity_id).first()
    if identity is None or identity.user_id != user_id:
        raise ForbiddenError("Only the identity owner may answer this consent request.")
    identity_service.require_not_frozen(identity)
    if consent.status != ConsentStatus.PENDING.value:
        raise ArmorError("CONSENT_ALREADY_ANSWERED", "This request was already answered.", 409)
    action = action.upper()
    stamp = now()
    if action in ("APPROVE", "APPROVED", "GRANT", "GRANTED"):
        if scope_intent is not None:
            consent.intent = scope_intent.value
        if scope_media is not None:
            consent.media = scope_media.value
        consent.validity = validity
        consent.expires_at = _expiry(validity, until, stamp)
        consent.status = ConsentStatus.GRANTED.value
    elif action in ("DENY", "DENIED", "BLOCK"):
        consent.status = ConsentStatus.DENIED.value
        if action == "BLOCK" and not _is_blocked(db, user_id, consent.requester_id):
            db.add(Block(owner_id=user_id, requester_id=consent.requester_id))
    else:
        raise ArmorError("INVALID_CONSENT_DECISION", "Answer with APPROVE, DENY, or BLOCK.", 422)
    consent.answered_at = stamp
    audit_service.record(
        db,
        "CONSENT_ANSWERED",
        user_id,
        {
            "consent_id": consent.consent_id,
            "request_id": consent.request_id,
            "status": consent.status,
            "action": action,
            "intent": consent.intent,
            "media": consent.media,
            "validity": consent.validity,
        },
    )
    held = (
        db.query(Request).filter(Request.request_id == consent.request_id).first()
        if consent.request_id
        else None
    )
    if held is not None:
        from app.services import feedback_service  # local import: keeps the module light

        feedback_service.record(db, held, f"CONSENT_{consent.status}")
    notify_service.notify(
        db,
        consent.requester_id,
        "CONSENT_ANSWERED",
        "Permintaan persetujuan dijawab",
        "Pemilik identitas sudah menjawab permintaanmu. Status permintaanmu diperbarui.",
        {"request_id": consent.request_id},
    )
    db.commit()
    db.refresh(consent)
    if consent.request_id:
        from app.services import decision_service  # local import: avoids an import cycle

        decision_service.reevaluate(db, consent.request_id)
    return consent


def revoke(db: Session, consent_id: str, user_id: str) -> Consent:
    """The owner withdraws consent they already gave; it counts as NONE from now on."""
    consent = _get(db, consent_id)
    identity = db.query(Identity).filter(Identity.identity_id == consent.identity_id).first()
    if identity is None or identity.user_id != user_id:
        raise ForbiddenError("Only the identity owner may revoke this consent.")
    if consent.status != ConsentStatus.GRANTED.value:
        raise ArmorError("CONSENT_NOT_GRANTED", "Only granted consent can be revoked.", 409)
    if consent.revoked_at is None:
        consent.revoked_at = now()
        audit_service.record(db, "CONSENT_REVOKED", user_id, {"consent_id": consent.consent_id})
        db.commit()
        db.refresh(consent)
    return consent


def unblock(db: Session, owner_id: str, requester_email: str) -> None:
    requester = db.query(User).filter(User.email == requester_email).first()
    if requester is not None:
        db.query(Block).filter(
            Block.owner_id == owner_id, Block.requester_id == requester.user_id
        ).delete()
        db.commit()


def resolve(
    db: Session,
    identity_id: str,
    requester_id: str,
    intent: Optional[str] = None,
    media: Optional[str] = None,
) -> tuple[ConsentStatus, Optional[Consent]]:
    """Effective consent this requester holds for an identity, for this scope.
    The most recent answer whose scope covers the intent and media decides."""
    q = db.query(Consent).filter(
        Consent.identity_id == identity_id, Consent.requester_id == requester_id
    )
    if intent is not None:
        q = q.filter(or_(Consent.intent.is_(None), Consent.intent == intent))
    if media is not None:
        q = q.filter(or_(Consent.media.is_(None), Consent.media == media))
    consent = q.order_by(Consent.updated_at.desc(), Consent.id.desc()).first()
    if consent is None:
        return ConsentStatus.NONE, None
    return effective(consent), consent


def latest_status_for(
    db: Session,
    identity_id: str,
    requester_id: str,
    intent: Optional[str] = None,
    media: Optional[str] = None,
) -> ConsentStatus:
    return resolve(db, identity_id, requester_id, intent, media)[0]


def mark_used(db: Session, consents: list[Consent]) -> None:
    """Spend single-use consent that an ALLOW decision relied on."""
    stamp = now()
    for c in consents:
        if c.validity == "ONCE" and c.used_at is None:
            c.used_at = stamp

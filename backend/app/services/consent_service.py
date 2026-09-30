"""Consent lifecycle (lapis 2): request -> pending -> granted/denied.

The requester never names an identity: they ask for consent on one of their own
gateway requests, and ARMOR routes a request to the owner of every registered
person found in it. The response is the same whether zero or several owners were
asked, so it cannot be used to learn who is registered. Only the identity owner
may answer.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import ArmorError, ForbiddenError, NotFoundError
from app.models.consent import Consent
from app.models.identity import Identity
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


def _new_consent_id() -> str:
    return str(uuid.uuid4())


def _own_request(db: Session, request_id: str, user_id: str) -> Request:
    row = db.query(Request).filter(Request.request_id == request_id).first()
    if row is None or row.requester_id != user_id:
        raise NotFoundError(f"Request '{request_id}' not found.")
    return row


def request_for(
    db: Session,
    request_id: str,
    requester_id: str,
    intent: Optional[Intent] = None,
    media: Optional[BiometricMedia] = None,
) -> int:
    """Ask the owners of every registered person in one of your REVIEW requests.

    Returns how many consent requests were created (never shown to the requester).
    """
    req = _own_request(db, request_id, requester_id)
    if req.decision != Decision.REVIEW.value:
        raise ArmorError(
            "CONSENT_NOT_APPLICABLE",
            "Consent can only be requested for a request that is waiting for review.",
            409,
        )
    scope_intent = (intent or Intent(req.intent)).value
    media_type = MediaType(req.media_type) if req.media_type else MediaType.IMAGE
    created = 0
    targets = (
        db.query(RequestTarget)
        .filter(
            RequestTarget.request_id == request_id,
            RequestTarget.target_type == IdentityTarget.OTHER_REGISTERED.value,
        )
        .all()
    )
    for t in targets:
        scope_media = (media or permission_media(TargetSource(t.source), media_type)).value
        exists = (
            db.query(Consent)
            .filter(
                Consent.identity_id == t.identity_id,
                Consent.requester_id == requester_id,
                Consent.request_id == request_id,
                Consent.status == ConsentStatus.PENDING.value,
            )
            .first()
        )
        if exists:
            continue
        db.add(
            Consent(
                consent_id=_new_consent_id(),
                identity_id=t.identity_id,
                requester_id=requester_id,
                intent=scope_intent,
                media=scope_media,
                request_id=request_id,
                status=ConsentStatus.PENDING.value,
            )
        )
        created += 1
    db.commit()
    return created


def status_for_request(db: Session, request_id: str, requester_id: str) -> ConsentStatus:
    """Aggregated answer for the requester: DENIED if any owner refused, GRANTED when
    every asked owner agreed, PENDING otherwise (including when nobody was asked)."""
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


def _owner_of(db: Session, identity_id: str) -> Optional[str]:
    identity = db.query(Identity).filter(Identity.identity_id == identity_id).first()
    return identity.user_id if identity else None


def get_for_owner(db: Session, consent_id: str, user_id: str) -> Consent:
    consent = _get(db, consent_id)
    if _owner_of(db, consent.identity_id) != user_id:
        raise NotFoundError(f"Consent '{consent_id}' not found.")
    return consent


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
    items = []
    for c in q.order_by(Consent.created_at.desc()).all():
        requester = db.query(User).filter(User.user_id == c.requester_id).first()
        req = (
            db.query(Request).filter(Request.request_id == c.request_id).first()
            if c.request_id
            else None
        )
        items.append(
            {
                "consent_id": c.consent_id,
                "identity_id": c.identity_id,
                # The requester asked for consent, so they are identified to the owner.
                "requester_email": requester.email if requester else None,
                "intent": c.intent,
                "media": c.media,
                "prompt": req.prompt if req else None,
                "media_type": req.media_type if req else None,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
        )
    return items


def respond(db: Session, consent_id: str, decision: str, user_id: str) -> Consent:
    consent = _get(db, consent_id)
    owner = _owner_of(db, consent.identity_id)
    if owner is None or owner != user_id:
        raise ForbiddenError("Only the identity owner may answer this consent request.")
    status = normalize_consent(decision)
    if status not in (ConsentStatus.GRANTED, ConsentStatus.DENIED):
        raise ArmorError(
            "INVALID_CONSENT_DECISION",
            "Consent decision must resolve to APPROVED/GRANTED or DENIED.",
            422,
        )
    consent.status = status.value
    db.commit()
    db.refresh(consent)
    return consent


def latest_status_for(
    db: Session,
    identity_id: str,
    requester_id: str,
    intent: Optional[str] = None,
    media: Optional[str] = None,
) -> ConsentStatus:
    """Most recent consent outcome this requester holds for an identity whose scope
    covers the given intent and media (a NULL scope field means "any")."""
    q = db.query(Consent).filter(
        Consent.identity_id == identity_id, Consent.requester_id == requester_id
    )
    if intent is not None:
        q = q.filter(or_(Consent.intent.is_(None), Consent.intent == intent))
    if media is not None:
        q = q.filter(or_(Consent.media.is_(None), Consent.media == media))
    consent = q.order_by(Consent.updated_at.desc()).first()
    if consent is None:
        return ConsentStatus.NONE
    return normalize_consent(consent.status)

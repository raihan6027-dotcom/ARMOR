"""Consent lifecycle: request -> pending -> granted/denied, persisted in the DB."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ArmorError, NotFoundError
from app.models.consent import Consent
from app.schema.common import ConsentStatus, normalize_consent


def _next_consent_id(db: Session) -> str:
    count = db.query(Consent).count()
    return f"CONSENT-{count + 1:03d}"


def create_request(
    db: Session,
    identity_id: str,
    requester_id: Optional[str] = None,
    intent: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Consent:
    consent = Consent(
        consent_id=_next_consent_id(db),
        identity_id=identity_id,
        requester_id=requester_id,
        intent=intent,
        request_id=request_id,
        status=ConsentStatus.PENDING.value,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


def get_status(db: Session, consent_id: str) -> Consent:
    consent = db.query(Consent).filter(Consent.consent_id == consent_id).first()
    if consent is None:
        raise NotFoundError(f"Consent '{consent_id}' not found.")
    return consent


def respond(db: Session, consent_id: str, decision: str) -> Consent:
    consent = get_status(db, consent_id)
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
    db: Session, identity_id: str, requester_id: Optional[str] = None
) -> ConsentStatus:
    """Most recent consent outcome for an identity (optionally by requester)."""
    q = db.query(Consent).filter(Consent.identity_id == identity_id)
    if requester_id:
        q = q.filter(Consent.requester_id == requester_id)
    consent = q.order_by(Consent.updated_at.desc()).first()
    if consent is None:
        return ConsentStatus.UNKNOWN
    return normalize_consent(consent.status)

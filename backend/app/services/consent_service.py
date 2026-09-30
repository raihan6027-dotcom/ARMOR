"""Consent lifecycle: request -> pending -> granted/denied, persisted in the DB.

Only the identity owner may answer a consent request, and the requester is
always the authenticated caller (never a value taken from the request body).
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ArmorError, ForbiddenError, NotFoundError
from app.models.consent import Consent
from app.models.identity import Identity
from app.schema.common import ConsentStatus, normalize_consent


def _new_consent_id() -> str:
    return str(uuid.uuid4())


def create_request(
    db: Session,
    identity_id: str,
    requester_id: str,
    intent: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Consent:
    consent = Consent(
        consent_id=_new_consent_id(),
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


def _get(db: Session, consent_id: str) -> Consent:
    consent = db.query(Consent).filter(Consent.consent_id == consent_id).first()
    if consent is None:
        raise NotFoundError(f"Consent '{consent_id}' not found.")
    return consent


def _owner_of(db: Session, identity_id: str) -> Optional[str]:
    identity = db.query(Identity).filter(Identity.identity_id == identity_id).first()
    return identity.user_id if identity else None


def get_status(db: Session, consent_id: str, user_id: str) -> Consent:
    """Visible to the requester who asked and to the identity owner only."""
    consent = _get(db, consent_id)
    if user_id not in (consent.requester_id, _owner_of(db, consent.identity_id)):
        raise NotFoundError(f"Consent '{consent_id}' not found.")
    return consent


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


def latest_status_for(db: Session, identity_id: str, requester_id: str) -> ConsentStatus:
    """Most recent consent outcome this requester holds for an identity."""
    consent = (
        db.query(Consent)
        .filter(Consent.identity_id == identity_id, Consent.requester_id == requester_id)
        .order_by(Consent.updated_at.desc())
        .first()
    )
    if consent is None:
        return ConsentStatus.UNKNOWN
    return normalize_consent(consent.status)

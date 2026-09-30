"""Trusted circle: people the owner pre-approves for a scope, like a standing consent.

A member counts only for intents and media inside their scope and before their
expiry. Harmful intents can never be in a scope (lapis 1 rules always apply).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ArmorError, NotFoundError
from app.core.timeutil import naive, now
from app.models.owner import CircleMember
from app.models.user import User
from app.schema.common import HARMFUL_INTENTS, BiometricMedia, Intent
from app.services import audit_service, identity_service


def _as_dict(m: CircleMember, email: str | None) -> dict:
    return {
        "member_ref": m.member_ref,
        "identity_id": m.identity_id,
        "email": email,
        "intents": json.loads(m.intents) if m.intents else None,
        "media": m.media,
        "expires_at": m.expires_at.isoformat() if m.expires_at else None,
        "active": m.expires_at is None or m.expires_at > now(),
        "created_at": m.created_at.isoformat(),
    }


def add(
    db: Session,
    owner_id: str,
    identity_id: str,
    email: str,
    intents: Optional[list[Intent]],
    media: Optional[BiometricMedia],
    expires_at: Optional[datetime],
) -> dict:
    identity = identity_service.get_owned(db, identity_id, owner_id, hide_existence=False)
    identity_service.require_not_frozen(identity)
    member = db.query(User).filter(User.email == email.lower().strip()).first()
    if member is None:
        raise NotFoundError("No ARMOR account uses that e-mail.")
    if member.user_id == owner_id:
        raise ArmorError("CIRCLE_SELF", "You do not need to add yourself.", 422)
    if intents:
        bad = [i.value for i in intents if i in HARMFUL_INTENTS or i is Intent.UNCERTAIN]
        if bad:
            raise ArmorError(
                "INTENT_LOCKED",
                "These purposes can never be pre-approved.",
                422,
                {"intents": bad},
            )
    row = (
        db.query(CircleMember)
        .filter(CircleMember.identity_id == identity_id, CircleMember.member_id == member.user_id)
        .first()
    )
    if row is None:
        row = CircleMember(
            member_ref=str(uuid.uuid4()), identity_id=identity_id, member_id=member.user_id
        )
        db.add(row)
    row.intents = json.dumps([i.value for i in intents]) if intents else None
    row.media = media.value if media else None
    row.expires_at = naive(expires_at)
    audit_service.record(
        db,
        "CIRCLE_MEMBER_SET",
        owner_id,
        {"identity_id": identity_id, "member_id": member.user_id, "media": row.media},
    )
    db.commit()
    db.refresh(row)
    return _as_dict(row, member.email)


def list_for(db: Session, owner_id: str, identity_id: str) -> list[dict]:
    identity_service.get_owned(db, identity_id, owner_id, hide_existence=False)
    out = []
    for m in db.query(CircleMember).filter(CircleMember.identity_id == identity_id).all():
        user = db.query(User).filter(User.user_id == m.member_id).first()
        out.append(_as_dict(m, user.email if user else None))
    return out


def remove(db: Session, owner_id: str, member_ref: str) -> None:
    row = db.query(CircleMember).filter(CircleMember.member_ref == member_ref).first()
    if row is None:
        raise NotFoundError("Circle member not found.")
    identity = identity_service.get_owned(db, row.identity_id, owner_id, hide_existence=True)
    identity_service.require_not_frozen(identity)
    audit_service.record(
        db,
        "CIRCLE_MEMBER_REMOVED",
        owner_id,
        {"identity_id": row.identity_id, "member_id": row.member_id},
    )
    db.delete(row)
    db.commit()


def covers(db: Session, identity_id: str, member_id: str, intent: Intent, media: str) -> bool:
    if intent in HARMFUL_INTENTS or intent is Intent.UNCERTAIN:
        return False
    row = (
        db.query(CircleMember)
        .filter(CircleMember.identity_id == identity_id, CircleMember.member_id == member_id)
        .first()
    )
    if row is None:
        return False
    if row.expires_at is not None and row.expires_at <= now():
        return False
    if row.media is not None and row.media != media:
        return False
    return row.intents is None or intent.value in json.loads(row.intents)

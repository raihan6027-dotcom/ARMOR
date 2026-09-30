"""Per-identity permissions: owner-configurable ALLOW/REVIEW/DENY per intent x media.

Rows only store the owner's overrides; everything else falls back to
app/policy/defaults.py. The four harmful intents are fixed at DENY.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ArmorError
from app.models.permission import Permission
from app.policy.defaults import DEFAULTS, LOCKED_INTENTS, default_permission
from app.schema.common import BiometricMedia, Intent, PermissionDecision


def get_permissions(
    db: Session, identity_id: str
) -> dict[BiometricMedia, dict[Intent, PermissionDecision]]:
    perms = {media: dict(table) for media, table in DEFAULTS.items()}
    rows = db.query(Permission).filter(Permission.identity_id == identity_id).all()
    for row in rows:
        try:
            media, intent = BiometricMedia(row.media), Intent(row.intent)
            decision = PermissionDecision(row.decision)
        except ValueError:
            continue
        if intent not in LOCKED_INTENTS:
            perms[media][intent] = decision
    return perms


def set_permission(
    db: Session,
    identity_id: str,
    intent: Intent,
    media: BiometricMedia,
    decision: PermissionDecision,
) -> Permission:
    if intent is Intent.UNCERTAIN:
        raise ArmorError("INVALID_INTENT", "UNCERTAIN is not a purpose you can permit.", 422)
    if intent in LOCKED_INTENTS and decision is not PermissionDecision.DENY:
        raise ArmorError(
            "INTENT_LOCKED",
            "Impersonation, defamation, sexual content, and deception are always refused.",
            422,
        )
    row = (
        db.query(Permission)
        .filter(
            Permission.identity_id == identity_id,
            Permission.intent == intent.value,
            Permission.media == media.value,
        )
        .first()
    )
    if row is None:
        row = Permission(
            identity_id=identity_id,
            intent=intent.value,
            media=media.value,
            decision=decision.value,
        )
        db.add(row)
    else:
        row.decision = decision.value
    db.commit()
    db.refresh(row)
    return row


def resolve(
    db: Session, identity_id: str, intent: Intent, media: BiometricMedia
) -> PermissionDecision:
    if intent in LOCKED_INTENTS or intent is Intent.UNCERTAIN:
        return default_permission(intent, media)
    row = (
        db.query(Permission)
        .filter(
            Permission.identity_id == identity_id,
            Permission.intent == intent.value,
            Permission.media == media.value,
        )
        .first()
    )
    if row is not None:
        try:
            return PermissionDecision(row.decision)
        except ValueError:
            pass
    return default_permission(intent, media)

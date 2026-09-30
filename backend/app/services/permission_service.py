"""Per-identity permissions: owner-configurable ALLOW/REVIEW/DENY per action."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.schema.common import Intent, PermissionDecision

# Baseline permissions applied when an owner has not overridden an action.
DEFAULT_PERMISSIONS: dict[str, PermissionDecision] = {
    "personal_creation": PermissionDecision.ALLOW,
    "editing": PermissionDecision.ALLOW,
    "commercial_use": PermissionDecision.REVIEW,
    "political_use": PermissionDecision.REVIEW,
    "deceptive": PermissionDecision.DENY,
    "defamation": PermissionDecision.DENY,
    "impersonation": PermissionDecision.DENY,
    "voice_cloning": PermissionDecision.DENY,
}

# Canonical intent -> permission action key.
_INTENT_TO_ACTION: dict[Intent, str] = {
    Intent.PERSONAL_CREATION: "personal_creation",
    Intent.PERSONAL_EDITING: "editing",
    Intent.COMMERCIAL_USE: "commercial_use",
    Intent.POLITICAL_USE: "political_use",
    Intent.DECEPTIVE: "deceptive",
    Intent.DEFAMATION: "defamation",
    Intent.IMPERSONATION: "impersonation",
}


def get_permissions(db: Session, identity_id: str) -> dict[str, PermissionDecision]:
    perms = dict(DEFAULT_PERMISSIONS)
    rows = db.query(Permission).filter(Permission.identity_id == identity_id).all()
    for row in rows:
        try:
            perms[row.action] = PermissionDecision(row.decision)
        except ValueError:
            continue
    return perms


def set_permission(
    db: Session, identity_id: str, action: str, decision: PermissionDecision
) -> Permission:
    row = (
        db.query(Permission)
        .filter(Permission.identity_id == identity_id, Permission.action == action)
        .first()
    )
    if row is None:
        row = Permission(identity_id=identity_id, action=action, decision=decision.value)
        db.add(row)
    else:
        row.decision = decision.value
    db.commit()
    db.refresh(row)
    return row


def resolve_for_intent(db: Session, identity_id: str, intent: Intent) -> PermissionDecision:
    action = _INTENT_TO_ACTION.get(intent)
    if action is None:
        return PermissionDecision.REVIEW  # unmapped/uncertain intents need review
    return get_permissions(db, identity_id).get(action, PermissionDecision.REVIEW)

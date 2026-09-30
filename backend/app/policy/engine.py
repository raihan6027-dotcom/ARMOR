"""Deterministic ARMOR policy engine.

This is the authoritative decision layer. It consumes STRUCTURED signals (identity
target/verification, normalized intent, risk level, consent, permission) and applies
fixed rules to produce ALLOW / REVIEW / DENY. No LLM output is trusted as the final
decision here, and any uncertainty (undetermined risk, unverified self, unknown
consent on another's identity) resolves to REVIEW or DENY — never a silent ALLOW.
"""
from __future__ import annotations

from typing import Optional

from app.schema.common import (
    ConsentStatus,
    Decision,
    IdentityTarget,
    Intent,
    PermissionDecision,
    RiskLevel,
    normalize_consent,
    normalize_intent,
    normalize_permission,
    normalize_risk,
)


def evaluate_policy(
    risk_level: Optional[str],
    consent: Optional[str],
    permission: Optional[str],
    identity_target: str = "OTHER",
    identity_verified: bool = False,
    intent: Optional[str] = None,
) -> tuple[str, str, str]:
    """Return (decision, reason_code, human_reason). Inputs may be any casing."""
    risk = normalize_risk(risk_level)
    cons = normalize_consent(consent)
    perm = normalize_permission(permission)
    intent_e = normalize_intent(intent) if intent is not None else None
    try:
        target = IdentityTarget(str(identity_target).upper())
    except ValueError:
        target = IdentityTarget.UNKNOWN

    # 1. Safe fallback: risk could not be determined (e.g. AI unavailable).
    if risk is None:
        return (
            Decision.REVIEW.value,
            "RISK_UNDETERMINED",
            "Risk level could not be determined; the request requires manual review.",
        )

    # 2. Hard denials — explicit refusals and unrecoverable misuse.
    if perm == PermissionDecision.DENY:
        return (
            Decision.DENY.value,
            "PERMISSION_DENIED",
            "The identity owner's permissions do not allow this action.",
        )
    if cons == ConsentStatus.DENIED:
        return (
            Decision.DENY.value,
            "CONSENT_DENIED",
            "The identity owner denied consent for this request.",
        )
    if risk == RiskLevel.CRITICAL:
        return (
            Decision.DENY.value,
            "CRITICAL_RISK",
            "The request presents a critical risk and is not permitted.",
        )
    if target == IdentityTarget.OTHER and intent_e in (Intent.IMPERSONATION, Intent.DEFAMATION):
        return (
            Decision.DENY.value,
            "IDENTITY_MISUSE",
            "Impersonation or defamation of another person's identity is not permitted.",
        )

    # 3. A SELF claim that could not be verified cannot be trusted as low-risk.
    if target == IdentityTarget.SELF and not identity_verified:
        return (
            Decision.REVIEW.value,
            "IDENTITY_UNVERIFIED",
            "The self-identity claim could not be verified; manual review required.",
        )

    # 4. Clear ALLOW: low risk, explicitly permitted, and either the verified owner
    #    themselves or another party with granted consent.
    if risk == RiskLevel.LOW and perm == PermissionDecision.ALLOW:
        if target == IdentityTarget.SELF:
            return (
                Decision.ALLOW.value,
                "SELF_LOW_RISK_ALLOWED",
                "Verified owner, permitted action, and low risk.",
            )
        if cons == ConsentStatus.GRANTED:
            return (
                Decision.ALLOW.value,
                "CONSENTED_LOW_RISK_ALLOWED",
                "Consent granted by the identity owner for a permitted, low-risk action.",
            )

    # 5. High risk is allowed only with an explicit green light from the owner.
    if (
        risk == RiskLevel.HIGH
        and perm == PermissionDecision.ALLOW
        and cons == ConsentStatus.GRANTED
    ):
        return (
            Decision.ALLOW.value,
            "PERMITTED_HIGH_RISK",
            "Elevated risk explicitly permitted and consented by the identity owner.",
        )
    if risk == RiskLevel.HIGH:
        return (
            Decision.REVIEW.value,
            "HIGH_RISK_REVIEW",
            "High risk usage requires the identity owner's review or consent.",
        )

    # 6. Remaining low/medium cases without a clear allow default to REVIEW.
    if target == IdentityTarget.OTHER and cons != ConsentStatus.GRANTED:
        return (
            Decision.REVIEW.value,
            "OTHER_CONSENT_REQUIRED",
            "Using another person's identity requires the owner's consent.",
        )
    return (
        Decision.REVIEW.value,
        "MANUAL_REVIEW_REQUIRED",
        "The request does not satisfy the conditions for automatic approval.",
    )

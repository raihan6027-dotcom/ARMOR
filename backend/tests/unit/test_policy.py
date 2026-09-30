"""Unit tests for the deterministic policy engine."""

from app.policy.engine import evaluate_policy


def test_self_low_allow():
    decision, code, _ = evaluate_policy(
        risk_level="LOW",
        consent="GRANTED",
        permission="ALLOW",
        identity_target="SELF",
        identity_verified=True,
        intent="PERSONAL_CREATION",
    )
    assert decision == "ALLOW"
    assert code == "SELF_LOW_RISK_ALLOWED"


def test_other_unknown_high_review():
    decision, code, _ = evaluate_policy(
        risk_level="HIGH",
        consent="UNKNOWN",
        permission="REVIEW",
        identity_target="OTHER",
        identity_verified=False,
        intent="COMMERCIAL_USE",
    )
    assert decision == "REVIEW"
    assert code == "HIGH_RISK_REVIEW"


def test_other_denied_critical_deny():
    decision, code, _ = evaluate_policy(
        risk_level="CRITICAL",
        consent="DENIED",
        permission="DENY",
        identity_target="OTHER",
        identity_verified=False,
        intent="IMPERSONATION",
    )
    assert decision == "DENY"


def test_undetermined_risk_falls_back_to_review():
    # AI could not produce a valid risk => must NOT auto-allow.
    decision, code, _ = evaluate_policy(
        risk_level=None,
        consent="GRANTED",
        permission="ALLOW",
        identity_target="SELF",
        identity_verified=True,
    )
    assert decision == "REVIEW"
    assert code == "RISK_UNDETERMINED"


def test_unverified_self_is_reviewed():
    decision, code, _ = evaluate_policy(
        risk_level="LOW",
        consent="GRANTED",
        permission="ALLOW",
        identity_target="SELF",
        identity_verified=False,
        intent="PERSONAL_CREATION",
    )
    assert decision == "REVIEW"
    assert code == "IDENTITY_UNVERIFIED"


def test_permission_deny_always_denies():
    decision, _, _ = evaluate_policy(
        risk_level="LOW",
        consent="GRANTED",
        permission="DENY",
        identity_target="SELF",
        identity_verified=True,
        intent="PERSONAL_CREATION",
    )
    assert decision == "DENY"


def test_impersonation_of_other_denied_even_without_permission_flag():
    decision, code, _ = evaluate_policy(
        risk_level="HIGH",
        consent="UNKNOWN",
        permission="REVIEW",
        identity_target="OTHER",
        identity_verified=False,
        intent="IMPERSONATION",
    )
    assert decision == "DENY"
    assert code == "IDENTITY_MISUSE"


def test_consented_other_low_allow():
    decision, code, _ = evaluate_policy(
        risk_level="LOW",
        consent="GRANTED",
        permission="ALLOW",
        identity_target="OTHER",
        identity_verified=True,
        intent="PERSONAL_EDITING",
    )
    assert decision == "ALLOW"
    assert code == "CONSENTED_LOW_RISK_ALLOWED"


def test_lowercase_inputs_are_normalized():
    decision, _, _ = evaluate_policy(
        risk_level="low",
        consent="granted",
        permission="allow",
        identity_target="self",
        identity_verified=True,
        intent="personal_creation",
    )
    assert decision == "ALLOW"

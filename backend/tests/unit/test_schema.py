"""Unit tests for AI-output normalization."""

from app.schema.common import (
    ConsentStatus,
    Intent,
    RiskLevel,
    normalize_consent,
    normalize_intent,
    normalize_permission,
    normalize_risk,
    risk_score_to_level,
)


def test_normalize_intent_exact():
    assert normalize_intent("COMMERCIAL_USE") is Intent.COMMERCIAL_USE


def test_normalize_intent_keywords():
    assert normalize_intent("Buat video ini mempromosikan produk") is Intent.COMMERCIAL_USE
    assert normalize_intent("orang ini mengatakan sesuatu") is Intent.IMPERSONATION
    assert normalize_intent("buat avatar kartun saya") is Intent.PERSONAL_CREATION


def test_normalize_intent_unmappable_is_uncertain():
    assert normalize_intent("qwerty zxcv") is Intent.UNCERTAIN
    assert normalize_intent(None) is Intent.UNCERTAIN


def test_normalize_risk_invalid_returns_none():
    assert normalize_risk("banana") is None
    assert normalize_risk(None) is None
    assert normalize_risk("high") is RiskLevel.HIGH


def test_normalize_consent_maps_approved():
    assert normalize_consent("APPROVED") is ConsentStatus.GRANTED
    assert normalize_consent("denied") is ConsentStatus.DENIED
    # Fase 2: canonical ConsentStatus uses NONE (CLAUDE.md bagian 6).
    assert normalize_consent(None) is ConsentStatus.NONE
    assert normalize_consent("weird") is ConsentStatus.NONE
    assert normalize_consent("UNKNOWN") is ConsentStatus.NONE


def test_normalize_permission_invalid_none():
    assert normalize_permission("ALLOW").value == "ALLOW"
    assert normalize_permission("maybe") is None


def test_risk_score_to_level():
    assert risk_score_to_level(10) is RiskLevel.LOW
    assert risk_score_to_level(50) is RiskLevel.MEDIUM
    assert risk_score_to_level(80) is RiskLevel.HIGH
    assert risk_score_to_level(95) is RiskLevel.CRITICAL
    assert risk_score_to_level(None) is None


def test_intent_enum_has_the_ten_canonical_classes():
    assert [i.value for i in Intent] == [
        "PERSONAL_CREATION",
        "PERSONAL_EDITING",
        "SATIRE_PARODY",
        "COMMERCIAL_USE",
        "POLITICAL_USE",
        "IMPERSONATION",
        "DEFAMATION",
        "SEXUAL_EXPLICIT",
        "DECEPTIVE",
        "UNCERTAIN",
    ]


def test_normalize_intent_new_classes():
    assert normalize_intent("buat parodi lucu tokoh ini") is Intent.SATIRE_PARODY
    assert normalize_intent("buat karikatur superhero dari foto ini") is Intent.SATIRE_PARODY
    assert normalize_intent("buat foto dia telanjang") is Intent.SEXUAL_EXPLICIT
    # Harmful concepts win over permissive ones in the same prompt.
    assert normalize_intent("parodi dia pakai baju tahanan") is Intent.DEFAMATION
    assert normalize_intent("iklan dia bugil") is Intent.SEXUAL_EXPLICIT

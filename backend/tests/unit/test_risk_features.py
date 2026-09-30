"""Documented keyword rules for realism, manipulation, and sensitive context."""

import pytest

from app.ai.risk_features import (
    HIGH,
    LOW,
    MID,
    RiskFeatures,
    feature_group,
    feature_names,
    from_prompt,
    manipulation,
    realism,
    sensitive_context,
    vectorize,
)


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Buat foto fotorealistik dia di pantai", HIGH),
        ("Make it look realistic, 4k", HIGH),
        ("Buat karikatur superhero dari foto ini", LOW),
        ("A cartoon avatar of me", LOW),
        ("Buat foto dia di pantai", MID),
        ("", MID),
        ("Karikatur yang terlihat nyata", HIGH),  # realism wins: stylization claim overridden
    ],
)
def test_realism(prompt, expected):
    assert realism(prompt) == expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Video dia lip-sync mengumumkan mundur", HIGH),
        ("Buat dia seolah mengatakan hal ini", HIGH),
        ("Clone his voice for a message", HIGH),
        ("Someone impersonating the mayor", HIGH),
        ("Cerahkan foto saya", LOW),
        ("Remove background noise from my recording", LOW),
        ("Buat poster iklan kopi", MID),
    ],
)
def test_manipulation(prompt, expected):
    assert manipulation(prompt) == expected


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Poster kampanye pilkada", 1),
        ("Dia minta transfer uang ke rekening baru", 1),
        ("Video bencana gempa", 1),
        ("Foto anak saya di sekolah", 1),
        ("Kids at school", 1),
        ("Just kidding, a birthday party photo", 0),  # no false hit on "kid"/"party"
        ("Style transfer to oil painting", 0),
        ("Avatar kartun saya", 0),
    ],
)
def test_sensitive_context(prompt, expected):
    assert sensitive_context(prompt) == expected


def test_vector_matches_names_and_is_one_hot():
    f = from_prompt("buat iklan fotorealistik", "COMMERCIAL_USE", 0.8, "OTHER_REGISTERED", "VIDEO")
    vec, names = vectorize(f), feature_names()
    assert len(vec) == len(names)
    on = {n for n, v in zip(names, vec, strict=True) if v == 1.0}
    assert {"intent=COMMERCIAL_USE", "target=OTHER_REGISTERED", "media=VIDEO"} <= on
    assert dict(zip(names, vec, strict=True))["realism"] == HIGH
    assert feature_group("intent=COMMERCIAL_USE") == "intent"


def test_unknown_target_and_media_are_normalized():
    f = from_prompt("x", "UNCERTAIN", 0.2, "SOMETHING", "HOLOGRAM")
    assert (f.target_type, f.media) == ("UNCLEAR", "IMAGE")


def test_consent_is_not_a_feature():
    # CLAUDE.md bagian 8: consent and permission are never Risk AI inputs.
    names = " ".join(feature_names()).lower()
    assert "consent" not in names and "permission" not in names
    assert "consent" not in RiskFeatures.__dataclass_fields__

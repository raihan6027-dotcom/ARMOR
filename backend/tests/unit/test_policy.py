"""Table-driven tests for the ARMOR policy engine (CLAUDE.md bagian 7).

The expected tables below are copied from CLAUDE.md, not from app/policy/matrix.py,
so a wrong cell in the implementation fails a test.
"""

import pytest

from app.policy import explain
from app.policy.defaults import (
    FACE_DEFAULTS,
    VOICE_DEFAULTS,
    default_permission,
    lock_applies,
    permission_media,
)
from app.policy.engine import (
    REALISM_THRESHOLD,
    PolicyInput,
    TargetInput,
    effective_intent,
    evaluate,
    is_voice_clone,
)
from app.policy.matrix import MATRIX, Row
from app.schema.common import (
    HARMFUL_INTENTS,
    BiometricMedia,
    ConsentStatus,
    Decision,
    IdentityTarget,
    Intent,
    LockLevel,
    MediaType,
    PermissionDecision,
    RiskLevel,
    TargetSource,
)

A, R, D = Decision.ALLOW, Decision.REVIEW, Decision.DENY
L, M, H, C = RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL
SELF = IdentityTarget.SELF
REG = IdentityTarget.OTHER_REGISTERED
UNREG = IdentityTarget.OTHER_UNREGISTERED
UNCLEAR = IdentityTarget.UNCLEAR


def run(targets, intent=Intent.PERSONAL_EDITING, risk=L, media=MediaType.IMAGE, **kw):
    return evaluate(
        PolicyInput(targets=targets, intent=intent, risk_level=risk, media_type=media, **kw)
    )


def face(target_type, **kw):
    return TargetInput(source=TargetSource.FACE, target_type=target_type, **kw)


# --- Every matrix cell -------------------------------------------------------

# (row builder, {risk: expected decision}) straight from CLAUDE.md bagian 7.
EXPECTED_MATRIX = {
    "self": (lambda: face(SELF), {L: A, M: A, H: R, C: D}),
    "registered_consent": (
        lambda: face(REG, consent=ConsentStatus.GRANTED, permission=PermissionDecision.REVIEW),
        {L: A, M: A, H: R, C: D},
    ),
    "registered_trusted_circle": (
        lambda: face(REG, in_trusted_circle=True, permission=PermissionDecision.REVIEW),
        {L: A, M: A, H: R, C: D},
    ),
    "registered_no_consent": (
        lambda: face(REG, permission=PermissionDecision.REVIEW),
        {L: R, M: R, H: D, C: D},
    ),
    "registered_pending_consent": (
        lambda: face(REG, consent=ConsentStatus.PENDING, permission=PermissionDecision.REVIEW),
        {L: R, M: R, H: D, C: D},
    ),
    "registered_locked": (
        lambda: face(REG, lock_level=LockLevel.ALL, consent=ConsentStatus.GRANTED),
        {L: D, M: D, H: D, C: D},
    ),
    "unregistered": (lambda: face(UNREG), {L: A, M: R, H: D, C: D}),
    "unclear": (lambda: face(UNCLEAR), {L: R, M: R, H: D, C: D}),
    "no_target": (None, {L: A, M: A, H: R, C: D}),
}

CELLS = [
    (name, risk, expected)
    for name, (_, row) in EXPECTED_MATRIX.items()
    for risk, expected in row.items()
]


@pytest.mark.parametrize(("row", "risk", "expected"), CELLS)
def test_every_matrix_cell(row, risk, expected):
    builder, _ = EXPECTED_MATRIX[row]
    targets = [] if builder is None else [builder()]
    assert run(targets, risk=risk).decision is expected


def test_matrix_table_has_all_rows_and_levels():
    assert set(MATRIX) == set(Row)
    for cells in MATRIX.values():
        assert set(cells) == set(RiskLevel)


def test_unregistered_low_allow_requires_label():
    res = run([face(UNREG)], intent=Intent.PERSONAL_CREATION, risk=L)
    assert res.decision is A
    assert res.reason_code == "UNREGISTERED_ALLOWED_LABEL"
    assert res.label_required is True


def test_owner_permission_allow_counts_as_standing_consent():
    # Default FACE permission for PERSONAL_CREATION is ALLOW.
    res = run([face(REG)], intent=Intent.PERSONAL_CREATION, risk=L)
    assert res.decision is A
    assert res.reason_code == "CONSENTED_ALLOWED"


def test_default_review_permission_needs_consent():
    res = run([face(REG)], intent=Intent.COMMERCIAL_USE, risk=M)
    assert res.decision is R
    assert res.reason_code == "CONSENT_REQUIRED"


# --- Lock levels -------------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "intent", "locked"),
    [
        (LockLevel.NONE, Intent.COMMERCIAL_USE, False),
        (LockLevel.COMMERCIAL_POLITICAL, Intent.COMMERCIAL_USE, True),
        (LockLevel.COMMERCIAL_POLITICAL, Intent.POLITICAL_USE, True),
        (LockLevel.COMMERCIAL_POLITICAL, Intent.PERSONAL_EDITING, False),
        (LockLevel.ALL, Intent.PERSONAL_EDITING, True),
    ],
)
def test_lock_levels(level, intent, locked):
    assert lock_applies(level, intent) is locked
    res = run([face(REG, lock_level=level, consent=ConsentStatus.GRANTED)], intent=intent)
    assert (res.reason_code == "IDENTITY_LOCKED") is locked


def test_lock_does_not_apply_to_owner_self():
    res = run([face(SELF, lock_level=LockLevel.ALL)])
    assert res.decision is A


# --- Absolute rules ----------------------------------------------------------


@pytest.mark.parametrize("intent", sorted(HARMFUL_INTENTS, key=lambda i: i.value))
@pytest.mark.parametrize("target_type", [REG, UNREG, UNCLEAR])
def test_absolute_rule_1_harmful_intent_against_others(intent, target_type):
    target = face(
        target_type,
        consent=ConsentStatus.GRANTED,
        permission=PermissionDecision.ALLOW,
        in_trusted_circle=True,
    )
    res = run([target], intent=intent, risk=L)
    assert res.decision is D
    assert res.reason_code == explain.HARMFUL_CODE_BY_INTENT[intent]


@pytest.mark.parametrize("intent", sorted(HARMFUL_INTENTS, key=lambda i: i.value))
def test_harmful_intent_on_self_follows_the_matrix(intent):
    res = run([face(SELF)], intent=intent, risk=M)
    assert res.decision is A


def test_absolute_rule_2_voice_clone_without_consent():
    voice = TargetInput(
        source=TargetSource.VOICE, target_type=REG, permission=PermissionDecision.ALLOW
    )
    res = run([voice], intent=Intent.PERSONAL_CREATION, media=MediaType.AUDIO)
    assert res.decision is D
    assert res.reason_code == "VOICE_CLONE_NO_CONSENT"


def test_voice_clone_of_unregistered_is_always_denied():
    voice = TargetInput(source=TargetSource.VOICE, target_type=UNREG)
    res = run([voice], intent=Intent.PERSONAL_CREATION, media=MediaType.AUDIO)
    assert res.reason_code == "VOICE_CLONE_NO_CONSENT"


def test_voice_clone_with_consent_and_permission_follows_matrix():
    voice = TargetInput(
        source=TargetSource.VOICE,
        target_type=REG,
        consent=ConsentStatus.GRANTED,
        permission=PermissionDecision.REVIEW,
    )
    res = run([voice], intent=Intent.COMMERCIAL_USE, risk=M, media=MediaType.AUDIO)
    assert res.decision is A
    assert res.reason_code == "CONSENTED_ALLOWED"


def test_voice_clone_via_trusted_circle_counts_as_consent():
    voice = TargetInput(
        source=TargetSource.VOICE,
        target_type=REG,
        in_trusted_circle=True,
        permission=PermissionDecision.REVIEW,
    )
    assert run([voice], media=MediaType.AUDIO).decision is A


def test_voice_default_permission_denies_even_with_consent():
    # VOICE defaults are DENY for every intent (CLAUDE.md bagian 6).
    voice = TargetInput(source=TargetSource.VOICE, target_type=REG, consent=ConsentStatus.GRANTED)
    res = run([voice], intent=Intent.COMMERCIAL_USE, media=MediaType.AUDIO)
    assert res.reason_code == "PERMISSION_DENIED"


def test_own_voice_is_not_cloning():
    voice = TargetInput(source=TargetSource.VOICE, target_type=SELF)
    assert run([voice], intent=Intent.PERSONAL_CREATION, media=MediaType.AUDIO).decision is A


@pytest.mark.parametrize(
    ("source", "media", "clone"),
    [
        (TargetSource.VOICE, MediaType.AUDIO, True),
        (TargetSource.VOICE, MediaType.VIDEO, True),
        (TargetSource.VOICE, MediaType.IMAGE, False),
        (TargetSource.TEXT, MediaType.AUDIO, True),
        (TargetSource.TEXT, MediaType.VIDEO, False),
        (TargetSource.FACE, MediaType.AUDIO, False),
    ],
)
def test_is_voice_clone(source, media, clone):
    assert is_voice_clone(TargetInput(source=source, target_type=REG), media) is clone


@pytest.mark.parametrize("target_type", [SELF, REG, UNREG])
def test_absolute_rule_3_guardian_child_always_denied(target_type):
    res = run([face(target_type, guardian_child=True)], intent=Intent.PERSONAL_EDITING)
    assert res.decision is D
    assert res.reason_code == "GUARDIAN_CHILD"


def test_absolute_rule_4_permission_deny():
    res = run(
        [face(REG, permission=PermissionDecision.DENY, consent=ConsentStatus.GRANTED)],
        intent=Intent.PERSONAL_EDITING,
    )
    assert res.reason_code == "PERMISSION_DENIED"


def test_absolute_rule_4_consent_denied():
    res = run(
        [face(REG, permission=PermissionDecision.REVIEW, consent=ConsentStatus.DENIED)],
        intent=Intent.COMMERCIAL_USE,
    )
    assert res.decision is D
    assert res.reason_code == "CONSENT_DENIED"


# --- Fail-safe ---------------------------------------------------------------


def test_fail_safe_component_unavailable_raises_allow_to_review():
    res = run([face(SELF)], unavailable=("face",))
    assert res.decision is R
    assert res.reason_code == "COMPONENT_UNAVAILABLE"
    assert res.requester_code == "CHECK_UNAVAILABLE"  # same public code for everyone


def test_fail_safe_risk_undetermined():
    res = run([face(UNREG)], risk=None)
    assert res.decision is R
    assert res.reason_code == "RISK_UNDETERMINED"


def test_fail_safe_risk_undetermined_without_targets():
    res = run([], risk=None)
    assert res.decision is R


def test_fail_safe_intent_uncertain():
    res = run([face(UNREG)], intent=Intent.UNCERTAIN, risk=L)
    assert res.decision is R
    assert res.reason_code == "INTENT_UNCERTAIN"
    assert res.requester_code == "INTENT_UNCLEAR"
    assert res.suggestion


def test_fail_safe_never_lowers_a_deny():
    res = run([face(UNREG)], intent=Intent.DEFAMATION, unavailable=("face",))
    assert res.decision is D


def test_fail_safe_never_silently_allows():
    for unavailable, risk, intent in [
        (("face",), L, Intent.PERSONAL_CREATION),
        ((), None, Intent.PERSONAL_CREATION),
        ((), L, Intent.UNCERTAIN),
    ]:
        res = run([face(SELF)], intent=intent, risk=risk, unavailable=unavailable)
        assert res.decision is not A


# --- Multi-target: strictest wins -------------------------------------------


def test_multi_target_strictest_wins_review():
    # Scenario 10: A (self) and B (registered, no consent) in one photo for an ad.
    res = run([face(SELF), face(REG)], intent=Intent.COMMERCIAL_USE, risk=M)
    assert res.decision is R
    assert [d.decision for d in res.per_target_detail] == [A, R]


def test_multi_target_strictest_wins_deny():
    res = run([face(SELF), face(UNREG), face(REG, lock_level=LockLevel.ALL)])
    assert res.decision is D
    assert res.reason_code == "IDENTITY_LOCKED"


def test_multi_target_absolute_beats_matrix_deny_for_explanation():
    res = run([face(REG, lock_level=LockLevel.ALL), face(UNREG)], intent=Intent.DEFAMATION)
    assert res.reason_code == "HARMFUL_DEFAMATION"


def test_per_target_detail_keeps_identity_for_owner_and_audit():
    res = run([face(REG, identity_id="ID-B", score=0.71)], intent=Intent.COMMERCIAL_USE)
    detail = res.per_target_detail[0].as_dict()
    assert detail["identity_id"] == "ID-B"
    assert detail["score"] == 0.71
    assert detail["target_type"] == "OTHER_REGISTERED"


# --- Satire ------------------------------------------------------------------


def test_cartoon_satire_follows_matrix_with_label():
    res = run([face(UNREG)], intent=Intent.SATIRE_PARODY, risk=L, realism=0.1)
    assert res.decision is A
    assert res.label_required


def test_photorealistic_satire_is_treated_as_defamation():
    res = run([face(UNREG)], intent=Intent.SATIRE_PARODY, risk=L, realism=0.9)
    assert res.decision is D
    assert res.reason_code == "SATIRE_REALISTIC"
    assert res.effective_intent is Intent.DEFAMATION


def test_realistic_voice_satire_is_treated_as_deceptive():
    inp = PolicyInput(
        targets=[],
        intent=Intent.SATIRE_PARODY,
        risk_level=L,
        media_type=MediaType.AUDIO,
        realism=REALISM_THRESHOLD,
    )
    assert effective_intent(inp) == (Intent.DECEPTIVE, True)


def test_satire_without_realism_signal_is_not_reclassified():
    inp = PolicyInput(
        targets=[], intent=Intent.SATIRE_PARODY, risk_level=L, media_type=MediaType.IMAGE
    )
    assert effective_intent(inp) == (Intent.SATIRE_PARODY, False)


def test_satire_on_registered_person_needs_consent_by_default():
    res = run([face(REG)], intent=Intent.SATIRE_PARODY, risk=L, realism=0.1)
    assert res.decision is R


# --- Uniform requester message ----------------------------------------------

# Pairs that end in the same decision, one about a registered person, one not.
UNIFORM_PAIRS = [
    (
        "deny: lock vs high risk",
        dict(targets=[face(REG, lock_level=LockLevel.ALL)], intent=Intent.PERSONAL_EDITING, risk=H),
        dict(targets=[face(UNREG)], intent=Intent.PERSONAL_EDITING, risk=H),
    ),
    (
        "deny: permission vs high risk",
        dict(
            targets=[face(REG, permission=PermissionDecision.DENY)],
            intent=Intent.POLITICAL_USE,
            risk=H,
        ),
        dict(targets=[face(UNREG)], intent=Intent.POLITICAL_USE, risk=H),
    ),
    (
        "deny: guardian child vs high risk",
        dict(targets=[face(REG, guardian_child=True)], intent=Intent.COMMERCIAL_USE, risk=H),
        dict(targets=[face(UNREG)], intent=Intent.COMMERCIAL_USE, risk=H),
    ),
    (
        "deny: consent denied vs high risk",
        dict(
            targets=[face(REG, consent=ConsentStatus.DENIED)], intent=Intent.COMMERCIAL_USE, risk=H
        ),
        dict(targets=[face(UNREG)], intent=Intent.COMMERCIAL_USE, risk=H),
    ),
    (
        "review: consent required vs medium risk",
        dict(targets=[face(REG)], intent=Intent.COMMERCIAL_USE, risk=M),
        dict(targets=[face(UNREG)], intent=Intent.COMMERCIAL_USE, risk=M),
    ),
    (
        "allow: consented vs unregistered low",
        dict(
            targets=[face(REG, consent=ConsentStatus.GRANTED)], intent=Intent.COMMERCIAL_USE, risk=L
        ),
        dict(targets=[face(UNREG)], intent=Intent.COMMERCIAL_USE, risk=L),
    ),
    (
        "deny: harmful intent",
        dict(targets=[face(REG)], intent=Intent.DEFAMATION, risk=C, prompt="pakai baju tahanan"),
        dict(targets=[face(UNREG)], intent=Intent.DEFAMATION, risk=C, prompt="pakai baju tahanan"),
    ),
    (
        "review: unclear vs registered no consent",
        dict(targets=[face(REG)], intent=Intent.COMMERCIAL_USE, risk=L),
        dict(targets=[face(UNCLEAR)], intent=Intent.COMMERCIAL_USE, risk=L),
    ),
]


@pytest.mark.parametrize(("name", "registered", "unregistered"), UNIFORM_PAIRS)
def test_requester_message_is_uniform(name, registered, unregistered):
    a, b = run(**registered), run(**unregistered)
    assert a.decision is b.decision, name
    assert (a.requester_code, a.requester_message, a.suggestion) == (
        b.requester_code,
        b.requester_message,
        b.suggestion,
    ), name


_LEAKY_WORDS = ("terdaftar", "pemilik", "kunci", "wali", "izin pemilik", "persetujuan pemilik")


@pytest.mark.parametrize(("name", "registered", "unregistered"), UNIFORM_PAIRS)
def test_requester_message_never_mentions_registration(name, registered, unregistered):
    for case in (registered, unregistered):
        msg = run(**case).requester_message.lower()
        assert not any(w in msg for w in _LEAKY_WORDS), (name, msg)


def test_defamation_reason_uses_specific_wording_for_prisoner_prompt():
    res = run([face(UNREG)], intent=Intent.DEFAMATION, prompt="buat dia pakai baju tahanan")
    assert "tahanan" in res.requester_message
    assert res.suggestion == "Buat karikatur superhero dari foto ini."


def test_self_only_request_shows_full_reason():
    res = run([face(SELF)], risk=C)
    assert res.requester_code == "SELF_CRITICAL_RISK"
    assert res.requester_message == explain.REASONS["SELF_CRITICAL_RISK"]


def test_no_target_request_shows_full_reason():
    res = run([], risk=H)
    assert res.requester_code == "NO_TARGET_HIGH_RISK_REVIEW"


# --- Explain and defaults ----------------------------------------------------


def test_every_reason_code_has_text():
    produced = {code for cells in MATRIX.values() for _, code in cells.values()}
    produced |= set(explain.HARMFUL_CODE_BY_INTENT.values())
    produced |= {
        "SATIRE_REALISTIC",
        "VOICE_CLONE_NO_CONSENT",
        "GUARDIAN_CHILD",
        "PERMISSION_DENIED",
        "CONSENT_DENIED",
        "COMPONENT_UNAVAILABLE",
        "RISK_UNDETERMINED",
        "INTENT_UNCERTAIN",
    }
    assert produced <= set(explain.REASONS)


def test_no_em_dash_in_any_user_text():
    texts = [*explain.REASONS.values(), *explain.SUGGESTIONS.values()]
    texts += [explain.requester_view(d, "X", only_self=False).message for d in Decision]
    for text in texts:
        assert "—" not in text and "–" not in text, text


def test_default_permissions_match_claude_md():
    assert FACE_DEFAULTS == {
        Intent.PERSONAL_CREATION: PermissionDecision.ALLOW,
        Intent.PERSONAL_EDITING: PermissionDecision.ALLOW,
        Intent.SATIRE_PARODY: PermissionDecision.REVIEW,
        Intent.COMMERCIAL_USE: PermissionDecision.REVIEW,
        Intent.POLITICAL_USE: PermissionDecision.REVIEW,
        Intent.IMPERSONATION: PermissionDecision.DENY,
        Intent.DEFAMATION: PermissionDecision.DENY,
        Intent.SEXUAL_EXPLICIT: PermissionDecision.DENY,
        Intent.DECEPTIVE: PermissionDecision.DENY,
    }
    assert set(VOICE_DEFAULTS.values()) == {PermissionDecision.DENY}
    assert default_permission(Intent.UNCERTAIN, BiometricMedia.FACE) is PermissionDecision.REVIEW


@pytest.mark.parametrize(
    ("source", "media", "expected"),
    [
        (TargetSource.FACE, MediaType.IMAGE, BiometricMedia.FACE),
        (TargetSource.VOICE, MediaType.AUDIO, BiometricMedia.VOICE),
        (TargetSource.TEXT, MediaType.AUDIO, BiometricMedia.VOICE),
        (TargetSource.TEXT, MediaType.TEXT_ONLY, BiometricMedia.FACE),
    ],
)
def test_permission_media(source, media, expected):
    assert permission_media(source, media) is expected


def test_text_target_uses_face_permission_for_images():
    # Scenario 13: "buat iklan dengan [nama B]" -> REVIEW.
    name = TargetInput(source=TargetSource.TEXT, target_type=REG)
    assert (
        run([name], intent=Intent.COMMERCIAL_USE, risk=M, media=MediaType.TEXT_ONLY).decision is R
    )


def test_defamation_reason_without_specific_pattern_is_generic():
    res = run([face(UNREG)], intent=Intent.DEFAMATION, prompt="buat dia terlihat buruk")
    assert res.requester_message == explain.REASONS["HARMFUL_DEFAMATION"]

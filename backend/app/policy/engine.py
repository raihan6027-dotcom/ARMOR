"""Deterministic ARMOR policy engine (CLAUDE.md bagian 7).

This is the only place a decision is made. Models only supply structured
information (targets, intent, risk, realism); nothing a model outputs is used as
the decision itself.

Evaluation order:

1. Absolute rules, per target (always DENY).
2. Fail-safe rules, per request (at least REVIEW): a component unavailable, the
   risk could not be determined, or the intent is UNCERTAIN.
3. The matrix, per target (app/policy/matrix.py).
4. The final decision is the strictest of all of the above (DENY > REVIEW > ALLOW).

The result carries a full explanation for the owner and audit log, and a
separate requester view that is identical whether or not another person in the
media is registered.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.policy import explain
from app.policy.defaults import default_permission, lock_applies, permission_media
from app.policy.matrix import Row, lookup
from app.schema.common import (
    DECISION_RANK,
    HARMFUL_INTENTS,
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

# Satire at or above this realism (0..1, from Risk AI features) is treated as
# DEFAMATION (visual) or DECEPTIVE (audio).
REALISM_THRESHOLD = 0.6

# Tie-breaking between candidates of the same strictness: an absolute rule
# explains a DENY better than the matrix; a fail-safe explains a REVIEW better
# than the matrix (and never depends on who is registered).
_ABSOLUTE, _FAIL_SAFE, _MATRIX = 3, 2, 1


@dataclass
class TargetInput:
    """One person found in the request: a face, a voice, or a name in the text.

    lock_level, consent, permission and in_trusted_circle must already be
    resolved for this target's governing media (see defaults.permission_media)
    and for the request's intent. permission=None means "use the default".
    """

    source: TargetSource
    target_type: IdentityTarget
    identity_id: str | None = None
    score: float | None = None
    lock_level: LockLevel = LockLevel.NONE
    consent: ConsentStatus = ConsentStatus.NONE
    permission: PermissionDecision | None = None
    in_trusted_circle: bool = False
    guardian_child: bool = False


@dataclass
class PolicyInput:
    targets: list[TargetInput]
    intent: Intent
    risk_level: RiskLevel | None
    media_type: MediaType
    intent_confidence: float | None = None
    realism: float | None = None
    unavailable: tuple[str, ...] = ()
    prompt: str | None = None


@dataclass
class TargetResult:
    source: TargetSource
    target_type: IdentityTarget
    identity_id: str | None
    score: float | None
    decision: Decision
    reason_code: str
    reason: str

    def as_dict(self) -> dict:
        return {
            "source": self.source.value,
            "target_type": self.target_type.value,
            "identity_id": self.identity_id,
            "score": self.score,
            "decision": self.decision.value,
            "reason_code": self.reason_code,
            "reason": self.reason,
        }


@dataclass
class PolicyResult:
    decision: Decision
    reason_code: str
    reason: str
    suggestion: str | None
    requester_code: str
    requester_message: str
    effective_intent: Intent
    label_required: bool
    per_target_detail: list[TargetResult] = field(default_factory=list)


@dataclass(order=True)
class _Candidate:
    rank: int
    priority: int
    decision: Decision = field(compare=False)
    code: str = field(compare=False)


def _candidate(decision: Decision, code: str, priority: int) -> _Candidate:
    return _Candidate(DECISION_RANK[decision], priority, decision, code)


def is_voice_clone(target: TargetInput, media_type: MediaType) -> bool:
    """A request that would reproduce a person's voice."""
    if media_type not in (MediaType.AUDIO, MediaType.VIDEO):
        return False
    if target.source is TargetSource.VOICE:
        return True
    return target.source is TargetSource.TEXT and media_type is MediaType.AUDIO


def effective_intent(inp: PolicyInput) -> tuple[Intent, bool]:
    """Realistic satire is not satire any more. Returns (intent, was_reclassified)."""
    if (
        inp.intent is Intent.SATIRE_PARODY
        and inp.realism is not None
        and inp.realism >= REALISM_THRESHOLD
    ):
        reclassified = Intent.DECEPTIVE if inp.media_type is MediaType.AUDIO else Intent.DEFAMATION
        return reclassified, True
    return inp.intent, False


def _absolute(
    t: TargetInput, inp: PolicyInput, intent: Intent, satire_realistic: bool
) -> str | None:
    """Absolute rules for one target. Returns a DENY reason code or None."""
    other = t.target_type is not IdentityTarget.SELF
    # Rule 3: identities enrolled through guardian mode (children), for anyone.
    if t.guardian_child:
        return "GUARDIAN_CHILD"
    # Rule 1: harmful intents against anyone who is not the requester.
    if other and intent in HARMFUL_INTENTS:
        return "SATIRE_REALISTIC" if satire_realistic else explain.HARMFUL_CODE_BY_INTENT[intent]
    # Rule 2: cloning someone else's voice without consent for VOICE.
    consented = t.consent is ConsentStatus.GRANTED or t.in_trusted_circle
    if other and is_voice_clone(t, inp.media_type) and not consented:
        return "VOICE_CLONE_NO_CONSENT"
    # Rule 4: the owner's explicit refusals.
    if t.target_type is IdentityTarget.OTHER_REGISTERED:
        if _permission(t, inp, intent) is PermissionDecision.DENY:
            return "PERMISSION_DENIED"
        if t.consent is ConsentStatus.DENIED:
            return "CONSENT_DENIED"
    return None


def _permission(t: TargetInput, inp: PolicyInput, intent: Intent) -> PermissionDecision:
    if t.permission is not None:
        return t.permission
    return default_permission(intent, permission_media(t.source, inp.media_type))


def matrix_row(t: TargetInput, inp: PolicyInput, intent: Intent) -> Row:
    if t.target_type is IdentityTarget.SELF:
        return Row.SELF
    if t.target_type is IdentityTarget.OTHER_UNREGISTERED:
        return Row.UNREGISTERED
    if t.target_type is IdentityTarget.UNCLEAR:
        return Row.UNCLEAR
    # OTHER_REGISTERED
    if lock_applies(t.lock_level, intent):
        return Row.REGISTERED_LOCKED
    standing_consent = (
        t.consent is ConsentStatus.GRANTED
        or t.in_trusted_circle
        or _permission(t, inp, intent) is PermissionDecision.ALLOW
    )
    return Row.REGISTERED_CONSENTED if standing_consent else Row.REGISTERED_NO_CONSENT


def _fail_safe(inp: PolicyInput, intent: Intent) -> list[_Candidate]:
    out = []
    if inp.unavailable:
        out.append(_candidate(Decision.REVIEW, "COMPONENT_UNAVAILABLE", _FAIL_SAFE))
    if inp.risk_level is None:
        out.append(_candidate(Decision.REVIEW, "RISK_UNDETERMINED", _FAIL_SAFE))
    if intent is Intent.UNCERTAIN:
        out.append(_candidate(Decision.REVIEW, "INTENT_UNCERTAIN", _FAIL_SAFE))
    return out


def evaluate(inp: PolicyInput) -> PolicyResult:
    intent, satire_realistic = effective_intent(inp)
    candidates: list[_Candidate] = _fail_safe(inp, intent)
    details: list[TargetResult] = []

    for t in inp.targets:
        code = _absolute(t, inp, intent, satire_realistic)
        if code is not None:
            cand = _candidate(Decision.DENY, code, _ABSOLUTE)
        elif inp.risk_level is None:
            cand = _candidate(Decision.REVIEW, "RISK_UNDETERMINED", _FAIL_SAFE)
        else:
            decision, code = lookup(matrix_row(t, inp, intent), inp.risk_level)
            cand = _candidate(decision, code, _MATRIX)
        candidates.append(cand)
        details.append(
            TargetResult(
                source=t.source,
                target_type=t.target_type,
                identity_id=t.identity_id,
                score=t.score,
                decision=cand.decision,
                reason_code=cand.code,
                reason=explain.reason_for(cand.code, inp.prompt),
            )
        )

    if not inp.targets and inp.risk_level is not None:
        decision, code = lookup(Row.NO_TARGET, inp.risk_level)
        candidates.append(_candidate(decision, code, _MATRIX))

    final = max(candidates)
    only_self = all(t.target_type is IdentityTarget.SELF for t in inp.targets)
    view = explain.requester_view(
        final.decision, final.code, only_self=only_self, prompt=inp.prompt
    )
    return PolicyResult(
        decision=final.decision,
        reason_code=final.code,
        reason=explain.reason_for(final.code, inp.prompt),
        suggestion=view.suggestion,
        requester_code=view.public_code,
        requester_message=view.message,
        effective_intent=intent,
        label_required=final.decision is Decision.ALLOW,
        per_target_detail=details,
    )

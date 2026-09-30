"""Default owner permissions per intent x biometric media (CLAUDE.md bagian 6).

An owner can change these, except the four harmful intents, which stay DENY for
everyone (lapis 1): the UI shows them with a padlock.
"""

from __future__ import annotations

from app.schema.common import (
    HARMFUL_INTENTS,
    BiometricMedia,
    Intent,
    LockLevel,
    MediaType,
    PermissionDecision,
    TargetSource,
)

_A, _R, _D = PermissionDecision.ALLOW, PermissionDecision.REVIEW, PermissionDecision.DENY

FACE_DEFAULTS: dict[Intent, PermissionDecision] = {
    Intent.PERSONAL_CREATION: _A,
    Intent.PERSONAL_EDITING: _A,
    Intent.SATIRE_PARODY: _R,
    Intent.COMMERCIAL_USE: _R,
    Intent.POLITICAL_USE: _R,
    Intent.IMPERSONATION: _D,
    Intent.DEFAMATION: _D,
    Intent.SEXUAL_EXPLICIT: _D,
    Intent.DECEPTIVE: _D,
}

# Voice cloning of someone else defaults to DENY for every intent; the owner's own
# PERSONAL_* use is SELF and never consults these permissions.
VOICE_DEFAULTS: dict[Intent, PermissionDecision] = dict.fromkeys(FACE_DEFAULTS, _D)

DEFAULTS: dict[BiometricMedia, dict[Intent, PermissionDecision]] = {
    BiometricMedia.FACE: FACE_DEFAULTS,
    BiometricMedia.VOICE: VOICE_DEFAULTS,
}

LOCKED_INTENTS: frozenset[Intent] = HARMFUL_INTENTS


def default_permission(intent: Intent, media: BiometricMedia) -> PermissionDecision:
    """UNCERTAIN (or anything unmapped) needs review."""
    return DEFAULTS[media].get(intent, _R)


def permission_media(source: TargetSource, media_type: MediaType) -> BiometricMedia:
    """Which of the owner's two biometric settings governs a target.

    A face -> FACE, a voice -> VOICE. A name in the prompt (TEXT) is governed by
    VOICE when the request produces audio and by FACE otherwise.
    """
    if source is TargetSource.VOICE:
        return BiometricMedia.VOICE
    if source is TargetSource.TEXT and media_type is MediaType.AUDIO:
        return BiometricMedia.VOICE
    return BiometricMedia.FACE


def lock_applies(level: LockLevel, intent: Intent) -> bool:
    if level is LockLevel.ALL:
        return True
    if level is LockLevel.COMMERCIAL_POLITICAL:
        return intent in (Intent.COMMERCIAL_USE, Intent.POLITICAL_USE)
    return False

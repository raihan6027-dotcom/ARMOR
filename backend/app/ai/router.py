"""Media Router: which checks a request needs, and running the ones that exist.

    IMAGE     -> Face AI over every face
    VIDEO     -> Face AI over sampled frames (Fase 9) + Voice AI on the audio track (Fase 10b)
    AUDIO     -> Voice AI (Fase 10b)
    TEXT_ONLY -> no media check
    every request -> Intent AI and Risk AI on the prompt

A check the media needs but that is not available yet (or whose model failed to
load) is reported in `unavailable`; the policy engine then applies the fail-safe
rule (REVIEW, never a silent ALLOW).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.schema.common import MediaType

# Checks each media type needs.
REQUIRED: dict[MediaType, tuple[str, ...]] = {
    MediaType.IMAGE: ("face",),
    MediaType.VIDEO: ("face_video", "voice"),
    MediaType.AUDIO: ("voice",),
    MediaType.TEXT_ONLY: (),
}

# Checks implemented so far; later phases add to this set.
IMPLEMENTED: set[str] = {"face"}


@dataclass
class MediaInput:
    media_type: MediaType
    image: Optional[bytes] = None
    video: Optional[bytes] = None
    audio: Optional[bytes] = None


@dataclass
class RoutePlan:
    media_type: MediaType
    run: list[str] = field(default_factory=list)
    unavailable: list[str] = field(default_factory=list)


def media_type_for(
    declared: Optional[MediaType],
    image: Optional[bytes],
    video: Optional[bytes],
    audio: Optional[bytes],
) -> MediaType:
    if declared is not None:
        return declared
    if video:
        return MediaType.VIDEO
    if audio:
        return MediaType.AUDIO
    if image:
        return MediaType.IMAGE
    return MediaType.TEXT_ONLY


def plan(media: MediaInput) -> RoutePlan:
    p = RoutePlan(media_type=media.media_type)
    for check in REQUIRED[media.media_type]:
        (p.run if check in IMPLEMENTED else p.unavailable).append(check)
    return p

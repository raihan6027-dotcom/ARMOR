"""Upload validation: size limits and file type from content (magic bytes), never
from the file name or a client-declared type (CLAUDE.md bagian 9, Unggahan)."""

from __future__ import annotations

import base64
import binascii

from app.core.config import settings
from app.core.exceptions import ArmorError
from app.schema.common import MediaType

KIND_MEDIA = {"image": MediaType.IMAGE, "video": MediaType.VIDEO, "audio": MediaType.AUDIO}


def sniff(data: bytes) -> tuple[str, str] | None:
    """(kind, format) from the first bytes, or None if unrecognized."""
    head = data[:16]
    if head.startswith(b"\xff\xd8\xff"):
        return "image", "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image", "webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio", "wav"
    if head.startswith(b"fLaC"):
        return "audio", "flac"
    if head.startswith(b"OggS"):
        return "audio", "ogg"
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio", "mp3"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"M4A ", b"M4B "):
            return "audio", "m4a"
        return "video", "mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video", "webm"
    return None


def _limit_mb(kind: str) -> float:
    return {
        "image": settings.max_image_mb,
        "video": settings.max_video_mb,
        "audio": settings.max_audio_mb,
    }[kind]


def decode_b64(value: str, field: str) -> bytes:
    if not value:
        raise ArmorError("INVALID_FILE", f"No {field} provided.", 422, {"field": field})
    if "," in value and value.strip().startswith("data:"):
        value = value.split(",", 1)[1]
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ArmorError(
            "INVALID_FILE", f"{field} is not valid base64.", 422, {"field": field}
        ) from exc


def validate(data: bytes, expected: str, field: str) -> str:
    """Check size and content type; returns the detected format."""
    found = sniff(data)
    if found is None or found[0] != expected:
        raise ArmorError(
            "UNSUPPORTED_FILE_TYPE",
            f"{field} must be a {expected} file (checked from its content).",
            415,
            {"field": field, "detected": found[1] if found else None},
        )
    limit = _limit_mb(expected)
    if len(data) > limit * 1024 * 1024:
        raise ArmorError(
            "FILE_TOO_LARGE",
            f"{field} is larger than {limit:g} MB.",
            413,
            {"field": field, "limit_mb": limit},
        )
    return found[1]


def read_upload(value: str, expected: str, field: str) -> bytes:
    data = decode_b64(value, field)
    validate(data, expected, field)
    return data

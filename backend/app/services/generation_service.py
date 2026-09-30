"""After ALLOW: generator -> Output Guard -> ARMOR Shield (POST /requests/{id}/generate).

Media is never stored, so the requester sends the checked media again; it must be
byte-for-byte the media the decision was made on (SHA-256 kept on the request).
The output is returned once and not kept; only its hashes go to the Shield
registry.
"""

from __future__ import annotations

import base64
import hashlib
import io
import time
from typing import Optional

from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ArmorError, NotFoundError
from app.core.logging import get_logger
from app.core.ratelimit import limiter
from app.core.uploads import sniff
from app.generation import GeneratorUnavailable, get_generator
from app.models.identity import Identity
from app.models.request import Request
from app.schema.common import Decision, MediaType
from app.services import audit_service, notify_service, output_guard, shield_service

logger = get_logger("generation")

HELD_MESSAGE = (
    "Hasil ditahan oleh Output Guard karena memuat wajah yang pemakaiannya tidak "
    "diizinkan atau tidak bisa dipastikan. Hasil itu tidak disimpan."
)


def media_sha256(data: Optional[bytes]) -> Optional[str]:
    return hashlib.sha256(data).hexdigest() if data else None


def _own_allowed(db: Session, request_id: str, user_id: str) -> Request:
    row = db.query(Request).filter(Request.request_id == request_id).first()
    if row is None or row.requester_id != user_id:
        raise NotFoundError(f"Request '{request_id}' not found.")
    if row.decision != Decision.ALLOW.value or row.status != "FINAL":
        raise ArmorError(
            "REQUEST_NOT_ALLOWED",
            "Only a request with a final ALLOW decision can be generated.",
            409,
        )
    return row


def _check_media(row: Request, image: Optional[bytes]) -> None:
    media = MediaType(row.media_type or MediaType.TEXT_ONLY.value)
    if media in (MediaType.VIDEO, MediaType.AUDIO):
        raise ArmorError(
            "GENERATION_NOT_SUPPORTED", "Generation for video and audio is not available yet.", 422
        )
    if media is MediaType.TEXT_ONLY:
        if image is not None:
            raise ArmorError("MEDIA_MISMATCH", "This request was checked without media.", 409)
        return
    if image is None or media_sha256(image) != row.input_sha256:
        raise ArmorError(
            "MEDIA_MISMATCH",
            "Send exactly the same image that ARMOR checked for this request.",
            409,
        )


def _decode_output(data: bytes) -> Image.Image:
    kind = sniff(data)
    if kind is None or kind[0] != "image":
        raise GeneratorUnavailable("generator returned something that is not an image")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001
        raise GeneratorUnavailable("generator returned an unreadable image") from exc
    return img


def _hold(db: Session, row: Request, guard: output_guard.GuardResult) -> None:
    row.output_status = "HELD"
    audit_service.record(
        db,
        "OUTPUT_HELD",
        row.requester_id,
        {
            "request_id": row.request_id,
            "reasons": sorted(set(guard.reasons)),
            "identity_ids": guard.blocked_identity_ids,
            "faces": guard.faces,
        },
    )
    notified = set()
    for identity_id in guard.blocked_identity_ids:
        owner = db.query(Identity).filter(Identity.identity_id == identity_id).first()
        if owner is None or owner.user_id in notified:
            continue
        notified.add(owner.user_id)
        notify_service.notify(
            db,
            owner.user_id,
            "OUTPUT_GUARD",
            "Hasil yang memuat wajahmu ditahan",
            "Output Guard menahan sebuah hasil AI yang ternyata memuat wajahmu tanpa izin. "
            "Hasil itu tidak diberikan dan tidak disimpan.",
            {"request_id": row.request_id},
        )


def generate(db: Session, request_id: str, user_id: str, image: Optional[bytes]) -> dict:
    row = _own_allowed(db, request_id, user_id)
    _check_media(row, image)
    limiter.check(f"gateway:{user_id}", settings.gateway_requests_per_minute, 60)
    timing: dict[str, int] = {}

    start = time.perf_counter()
    generator = get_generator()
    try:
        produced = generator.generate(row.prompt, image)
        output = _decode_output(produced.png)
    except GeneratorUnavailable as exc:
        logger.warning("request_id=%s generator unavailable: %s", request_id, exc)
        raise ArmorError(
            "GENERATOR_UNAVAILABLE", "The generator is not available right now.", 503
        ) from exc
    timing["generate"] = int((time.perf_counter() - start) * 1000)

    start = time.perf_counter()
    guard = output_guard.check(db, row, produced.png)
    timing["output_guard"] = int((time.perf_counter() - start) * 1000)
    generator_info = {"name": produced.generator, "simulated": produced.simulated}

    if not guard.passed:
        _hold(db, row, guard)
        db.commit()
        logger.info("request_id=%s output HELD reasons=%s", request_id, guard.reasons)
        return {
            "request_id": request_id,
            "status": "HELD",
            "image": None,
            "message": HELD_MESSAGE,
            "shield": None,
            "generator": generator_info,
            "timing_ms": timing,
        }

    start = time.perf_counter()
    shielded = shield_service.apply(db, row, output, produced.generator, produced.simulated)
    timing["shield"] = int((time.perf_counter() - start) * 1000)
    row.output_status = "DELIVERED"
    audit_service.record(
        db,
        "OUTPUT_DELIVERED",
        row.requester_id,
        {
            "request_id": request_id,
            "shield_id": shielded.record.shield_id,
            "generator": produced.generator,
            "simulated": produced.simulated,
            "faces": guard.faces,
        },
    )
    db.commit()
    logger.info("request_id=%s output DELIVERED shield=%s", request_id, shielded.record.shield_id)
    return {
        "request_id": request_id,
        "status": "DELIVERED",
        "image": base64.b64encode(shielded.png).decode(),
        "message": "Hasil sudah diberi label AI dan tercatat di registri ARMOR Shield.",
        "shield": {
            "shield_id": shielded.record.shield_id,
            "created_at": shielded.manifest["created_at"],
            "permission_status": shielded.record.permission_status,
            "permission_text": shield_service.PERMISSION_TEXT[shielded.record.permission_status],
            "label": shield_service.LABEL,
        },
        "generator": generator_info,
        "timing_ms": timing,
    }

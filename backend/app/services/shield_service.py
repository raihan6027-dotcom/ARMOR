"""ARMOR Shield for images: a visible AI label, a signed manifest in the PNG
metadata, and hashes in a registry, so anyone can later check whether an image
was made through ARMOR (CLAUDE.md bagian 3, Output Guard dan Shield).

Manifest: follows the shape of a C2PA manifest (claim generator, a c2pa.actions
assertion with digitalSourceType trainedAlgorithmicMedia, plus an ARMOR
assertion) as far as is practical without a certificate authority. It is NOT a
C2PA manifest: it lives in a PNG iTXt chunk instead of JUMBF and is signed with
HMAC-SHA256 under a server key instead of an X.509 certificate, so only this
ARMOR server can verify it.

Verification order (public, no login): signed metadata -> exact hash (file or
pixels) -> perceptual hash. The answer never includes the prompt, the requester,
or who is in the image.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import uuid
from dataclasses import dataclass
from typing import Optional

import imagehash
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutil import now
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.models.shield import ShieldRecord
from app.policy.engine import POLICY_VERSION
from app.schema.common import Decision, IdentityTarget

LABEL = "Dibuat dengan AI · ARMOR"
MANIFEST_KEY = "armor:manifest"
DIGITAL_SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"

# Public permission status: says whether an identity owner gave permission, never who.
POLICY_ALLOWED = "POLICY_ALLOWED"
OWNER_PERMITTED = "OWNER_PERMITTED"
PERMISSION_TEXT = {
    POLICY_ALLOWED: "Diizinkan oleh kebijakan ARMOR.",
    OWNER_PERMITTED: "Diizinkan oleh pemilik identitas yang ada di dalamnya.",
}


# --- Keys and hashes ------------------------------------------------------------------


def _signing_key() -> bytes:
    if settings.shield_signing_key:
        return settings.shield_signing_key.encode()
    return hashlib.sha256(b"armor-shield:" + settings.jwt_secret.encode()).digest()


def _canonical(manifest: dict) -> bytes:
    body = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign(manifest: dict) -> str:
    return hmac.new(_signing_key(), _canonical(manifest), hashlib.sha256).hexdigest()


def pixel_sha256(img: Image.Image) -> str:
    rgb = img.convert("RGB")
    h = hashlib.sha256(f"{rgb.width}x{rgb.height}:".encode())
    h.update(rgb.tobytes())
    return h.hexdigest()


def phash(img: Image.Image) -> str:
    return str(imagehash.phash(img.convert("RGB")))


def _decode(data: bytes) -> Optional[Image.Image]:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        return img
    except Exception:  # noqa: BLE001
        return None


# --- Applying the shield ------------------------------------------------------------


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow without FreeType
        return ImageFont.load_default()


def draw_label(img: Image.Image) -> Image.Image:
    """Small visible label in the bottom-right corner."""
    out = img.convert("RGB")
    size = max(11, min(out.width, out.height) // 26)
    font = _font(size)
    draw = ImageDraw.Draw(out, "RGBA")
    left, top, right, bottom = draw.textbbox((0, 0), LABEL, font=font)
    pad = max(4, size // 3)
    w, h = right - left + 2 * pad, bottom - top + 2 * pad
    margin = max(6, size // 2)
    x0, y0 = out.width - w - margin, out.height - h - margin
    draw.rounded_rectangle(
        [x0, y0, x0 + w, y0 + h], radius=h // 2, fill=(6, 20, 42, 200), outline=(155, 227, 251, 230)
    )
    draw.text((x0 + pad - left, y0 + pad - top), LABEL, font=font, fill=(234, 244, 255, 255))
    return out


def permission_status(db: Session, request_id: str) -> str:
    """OWNER_PERMITTED when a registered person other than the requester was allowed
    (their permission, consent, or trusted circle); POLICY_ALLOWED otherwise."""
    owner_ok = (
        db.query(RequestTarget)
        .filter(
            RequestTarget.request_id == request_id,
            RequestTarget.target_type == IdentityTarget.OTHER_REGISTERED.value,
            RequestTarget.decision == Decision.ALLOW.value,
        )
        .first()
    )
    return OWNER_PERMITTED if owner_ok else POLICY_ALLOWED


@dataclass
class Shielded:
    png: bytes
    record: ShieldRecord
    manifest: dict


def apply(db: Session, row: Request, output: Image.Image, generator: str, simulated: bool) -> Shielded:
    labelled = draw_label(output)
    shield_id = str(uuid.uuid4())
    created = now()
    status = permission_status(db, row.request_id)
    manifest = {
        "armor_shield": "1",
        "claim_generator": f"ARMOR {settings.app_version}",
        "shield_id": shield_id,
        "decision_id": row.request_id,
        "created_at": created.isoformat() + "Z",
        "permission_status": status,
        "pixel_sha256": pixel_sha256(labelled),
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": DIGITAL_SOURCE_TYPE,
                            "softwareAgent": generator,
                        }
                    ]
                },
            },
            {
                "label": "armor.decision",
                "data": {
                    "decision": row.decision,
                    "policy_version": POLICY_VERSION,
                    "visible_label": LABEL,
                    "simulated_generator": simulated,
                },
            },
        ],
    }
    manifest["signature"] = {"alg": "HMAC-SHA256", "value": sign(manifest)}

    info = PngInfo()
    info.add_itxt(MANIFEST_KEY, json.dumps(manifest, ensure_ascii=False))
    info.add_text("Software", f"ARMOR Shield; generator: {generator}")
    buf = io.BytesIO()
    labelled.save(buf, format="PNG", pnginfo=info)
    png = buf.getvalue()

    record = ShieldRecord(
        shield_id=shield_id,
        request_id=row.request_id,
        requester_id=row.requester_id,
        media_type="IMAGE",
        permission_status=status,
        generator=generator[:64],
        simulated=simulated,
        file_sha256=hashlib.sha256(png).hexdigest(),
        pixel_sha256=manifest["pixel_sha256"],
        phash=phash(labelled),
        created_at=created,
    )
    db.add(record)
    return Shielded(png=png, record=record, manifest=manifest)


# --- Public verification ------------------------------------------------------------


def _read_manifest(img: Image.Image) -> Optional[dict]:
    raw = getattr(img, "text", {}).get(MANIFEST_KEY) if img.format == "PNG" else None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _valid_signature(manifest: dict) -> bool:
    sig = manifest.get("signature")
    if not isinstance(sig, dict) or sig.get("alg") != "HMAC-SHA256":
        return False
    return hmac.compare_digest(str(sig.get("value", "")), sign(manifest))


def _result(
    record: Optional[ShieldRecord],
    method: str,
    exact: bool,
    *,
    metadata_found: bool,
    metadata_valid: bool,
    distance: Optional[int] = None,
) -> dict:
    if record is None:
        message = (
            "Tidak ditemukan catatan ARMOR untuk gambar ini. Ini tidak membuktikan gambar "
            "itu asli atau palsu, hanya bahwa gambar ini tidak dibuat lewat ARMOR."
        )
        if metadata_found and not metadata_valid:
            message = (
                "Gambar ini memuat metadata ARMOR yang tanda tangannya tidak sah, dan tidak "
                "cocok dengan catatan mana pun. Metadata itu kemungkinan dipalsukan."
            )
        return {
            "verified": False,
            "method": "NONE",
            "exact": False,
            "created_at": None,
            "permission_status": None,
            "permission_text": None,
            "distance": None,
            "metadata_found": metadata_found,
            "metadata_valid": metadata_valid,
            "simulated_generator": None,
            "message": message,
        }
    if exact:
        message = "Gambar ini dibuat lewat ARMOR dan tidak diubah sejak itu."
    else:
        message = (
            "Gambar ini sangat mirip dengan gambar yang dibuat lewat ARMOR, tetapi sudah "
            "diubah (misalnya dipotong, dikompres, atau disunting)."
        )
    return {
        "verified": True,
        "method": method,
        "exact": exact,
        "created_at": record.created_at.isoformat() + "Z",
        "permission_status": record.permission_status,
        "permission_text": PERMISSION_TEXT.get(record.permission_status),
        "distance": distance,
        "metadata_found": metadata_found,
        "metadata_valid": metadata_valid,
        "simulated_generator": record.simulated,
        "message": message,
    }


def verify(db: Session, data: bytes) -> dict:
    img = _decode(data)
    if img is None:
        return _result(None, "NONE", False, metadata_found=False, metadata_valid=False)
    pixels = pixel_sha256(img)

    # 1. Signed metadata, bound to the pixels it was issued for.
    manifest = _read_manifest(img)
    found = manifest is not None
    valid = found and _valid_signature(manifest)
    if valid:
        record = (
            db.query(ShieldRecord)
            .filter(ShieldRecord.shield_id == str(manifest.get("shield_id")))
            .first()
        )
        if record is not None and manifest.get("pixel_sha256") == pixels == record.pixel_sha256:
            return _result(record, "METADATA", True, metadata_found=True, metadata_valid=True)

    # 2. Exact hash: the file as issued, or the same pixels with metadata stripped.
    file_hash = hashlib.sha256(data).hexdigest()
    record = (
        db.query(ShieldRecord)
        .filter((ShieldRecord.file_sha256 == file_hash) | (ShieldRecord.pixel_sha256 == pixels))
        .first()
    )
    if record is not None:
        return _result(record, "HASH", True, metadata_found=found, metadata_valid=valid)

    # 3. Perceptual hash: re-compressed, resized, or lightly edited copies.
    probe = imagehash.hex_to_hash(phash(img))
    best: tuple[Optional[ShieldRecord], int] = (None, 65)
    for rec in db.query(ShieldRecord).all():  # linear scan: fine for a demo-sized registry
        d = probe - imagehash.hex_to_hash(rec.phash)
        if d < best[1]:
            best = (rec, d)
    if best[0] is not None and best[1] <= settings.shield_phash_max_distance:
        return _result(
            best[0], "PERCEPTUAL", False, metadata_found=found, metadata_valid=valid, distance=best[1]
        )
    return _result(None, "NONE", False, metadata_found=found, metadata_valid=valid)

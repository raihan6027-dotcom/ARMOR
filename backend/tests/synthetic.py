"""Synthetic camera for tests: no model, no real faces.

An "image" is a real (tiny) PNG whose tEXt chunk `armor-synth` holds JSON
describing the faces in it, so it passes the upload type check. Each face has an
embedding derived from a person name (a seeded random unit vector), optionally
blended to hit an exact cosine similarity with that person, plus geometry used
by the real quality gate in app/ai/face.py.
"""

from __future__ import annotations

import base64
import io
import json
import zlib

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from app.ai.face import EMBEDDING_DIM, DetectedFace, l2_normalize, quality_issues

KEY = "armor-synth"


def person_vec(name: str) -> np.ndarray:
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    return l2_normalize(rng.standard_normal(EMBEDDING_DIM))


def vec_with_cosine(name: str, cos: float, salt: str = "x") -> np.ndarray:
    """A unit vector whose cosine with person_vec(name) is exactly `cos`."""
    base = person_vec(name)
    other = person_vec(f"{name}:{salt}")
    other = l2_normalize(other - np.dot(other, base) * base)  # orthogonal to base
    return l2_normalize(cos * base + np.sqrt(max(0.0, 1 - cos * cos)) * other)


def face(
    name: str | None = None,
    *,
    cos: float | None = None,
    yaw: float = 0.0,
    pitch: float = 0.0,
    size: float = 160.0,
    blur: float = 250.0,
) -> dict:
    return {"name": name, "cos": cos, "yaw": yaw, "pitch": pitch, "size": size, "blur": blur}


def image_bytes(*faces: dict) -> bytes:
    info = PngInfo()
    info.add_text(KEY, json.dumps(list(faces)))
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (40, 80, 120)).save(buf, format="PNG", pnginfo=info)
    return buf.getvalue()


def image(*faces: dict) -> str:
    return base64.b64encode(image_bytes(*faces)).decode()


def enroll_images(name: str, yaws=(-15.0, 0.0, 15.0), **kw) -> list[str]:
    return [image(face(name, yaw=y, **kw)) for y in yaws]


def _specs(data: bytes) -> list[dict] | None:
    try:
        img = Image.open(io.BytesIO(data))
        raw = img.text.get(KEY)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None
    return json.loads(raw) if raw else None


def analyze(data: bytes) -> list[DetectedFace]:
    """Drop-in replacement for FaceAI.analyze using the synthetic encoding."""
    specs = _specs(data)
    if not specs:
        return []
    out = []
    for spec in specs:
        name = spec["name"] or "anon"
        vec = person_vec(name) if spec["cos"] is None else vec_with_cosine(name, spec["cos"])
        size, blur, yaw, pitch = spec["size"], spec["blur"], spec["yaw"], spec["pitch"]
        out.append(
            DetectedFace(
                bbox=(0.0, 0.0, size, size),
                embedding=vec,
                det_score=0.99,
                size_px=size,
                blur_var=blur,
                yaw=yaw,
                pitch=pitch,
                issues=quality_issues(size, blur, yaw, pitch),
            )
        )
    return out

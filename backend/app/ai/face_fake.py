"""FAKE face engine for development and end-to-end browser tests ONLY.

Enabled with FACE_ENGINE=fake. Every decodable image is treated as containing one
clear face of the same synthetic person, and the head angle cycles through
-15, 0, +15 degrees on successive calls so a three-pose enrollment from a fake
camera passes. It never runs in production (Settings.insecure_settings refuses
it), never sees a real face model, and exists so the Playwright suite can drive
the real backend without volunteer photos.
"""

from __future__ import annotations

import itertools
import zlib

import numpy as np

from app.ai.face import EMBEDDING_DIM, DetectedFace, decode_to_bgr, l2_normalize


class FakeFaceAI:
    loaded = True
    init_error = "FACE_ENGINE=fake (development only)"

    def __init__(self) -> None:
        rng = np.random.default_rng(zlib.crc32(b"armor-e2e-person"))
        self._vec = l2_normalize(rng.standard_normal(EMBEDDING_DIM))
        self._yaws = itertools.cycle((-15.0, 0.0, 15.0))

    @property
    def available(self) -> bool:
        return True

    def analyze(self, image_bytes: bytes) -> list[DetectedFace]:
        if decode_to_bgr(image_bytes) is None:
            return []
        return [
            DetectedFace(
                bbox=(0.0, 0.0, 200.0, 200.0),
                embedding=self._vec.copy(),
                det_score=0.99,
                size_px=200.0,
                blur_var=500.0,
                yaw=next(self._yaws),
                pitch=0.0,
            )
        ]

"""InsightFace/ArcFace wrapper: turns an uploaded image into a 512-D embedding,
and verifies/identifies it against the ARMOR registry.

InsightFace + its model pack are heavy and download on first use, so the pipeline
is lazy-initialized. If unavailable, `available` is False and the identity service
degrades to a safe, explicit "unverified" result (policy then falls back to REVIEW).
"""

from __future__ import annotations

import io
from typing import Optional

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("identity_ai")


class IdentityAIClient:
    def __init__(self) -> None:
        self._app = None
        self._init_error: Optional[str] = None
        self._tried = False

    @property
    def available(self) -> bool:
        self._ensure_ready()
        return self._app is not None

    @property
    def loaded(self) -> bool:
        """Whether the model is already initialized (does not trigger a load)."""
        return self._app is not None

    def _ensure_ready(self) -> None:
        if self._tried:
            return
        self._tried = True
        try:
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(
                name=settings.insightface_model,
                allowed_modules=["detection", "recognition"],
                providers=["CPUExecutionProvider"],
            )
            app.prepare(ctx_id=0, det_size=(640, 640))
            self._app = app
            logger.info("InsightFace ready (%s)", settings.insightface_model)
        except Exception as exc:  # pragma: no cover - heavy/optional dep
            self._init_error = f"InsightFace unavailable: {exc}"
            logger.warning(self._init_error)

    def embed(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Return the normed 512-D embedding of the largest detected face, or None."""
        self._ensure_ready()
        if self._app is None:
            return None
        try:
            import cv2
            from PIL import Image

            pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
            faces = self._app.get(bgr)
            if not faces:
                return None
            faces.sort(
                key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True
            )
            return np.asarray(faces[0].normed_embedding, dtype=np.float32)
        except Exception as exc:  # pragma: no cover
            logger.warning("Embedding failed: %s", exc)
            return None


identity_ai_client = IdentityAIClient()

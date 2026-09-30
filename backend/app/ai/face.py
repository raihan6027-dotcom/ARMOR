"""Face AI: detect EVERY face, check its quality, and embed it (CLAUDE.md bagian 8).

One pipeline for enrollment and inference: InsightFace `FaceAnalysis.get` with the
`buffalo_l` pack (SCRFD detector + ArcFace recognizer). CLAUDE.md bagian 12 is
explicit that the old notebook's separate RetinaFace + eye alignment + CLAHE +
`get_feat` preprocessing made enrolled and query embeddings incomparable, so no
extra preprocessing is added on either side.

This module never says who a face belongs to. It returns geometry, quality, and
an embedding; matching against opt-in enrollments happens in identity_service.

The model is loaded lazily. If it is unavailable, `analyze` returns None and
callers treat the face check as unavailable (fail safe to REVIEW).
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("face_ai")

EMBEDDING_DIM = 512


@dataclass
class DetectedFace:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels
    embedding: np.ndarray  # L2-normalized, shape (512,)
    det_score: float
    size_px: float  # min(width, height) of the box
    blur_var: float  # variance of the Laplacian of the face crop (higher = sharper)
    yaw: float  # degrees, + = face turned to the image's right
    pitch: float  # degrees, + = looking down
    issues: list[str] = field(default_factory=list)

    @property
    def quality_ok(self) -> bool:
        return not self.issues


# --- Quality measures (pure numpy so they are testable without the model) -------


def laplacian_variance(gray: np.ndarray) -> float:
    """Variance of the 4-neighbour Laplacian: a standard blur measure."""
    g = np.asarray(gray, dtype=np.float64)
    if g.ndim != 2 or min(g.shape) < 3:
        return 0.0
    lap = g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:] - 4.0 * g[1:-1, 1:-1]
    return float(lap.var())


def pose_from_landmarks(kps: np.ndarray) -> tuple[float, float]:
    """Approximate (yaw, pitch) in degrees from InsightFace's 5 landmarks.

    kps rows: left eye, right eye, nose tip, left mouth corner, right mouth corner.
    Yaw: horizontal offset of the nose from the eye midpoint, relative to the
    inter-ocular distance. Pitch: vertical position of the nose between the eye
    line and the mouth line (about 0.55 on a frontal face). These are coarse
    geometric estimates, good enough for the "is the face turned too far" gate
    and for checking that three enrollment captures differ in angle.
    """
    k = np.asarray(kps, dtype=np.float64).reshape(5, 2)
    left_eye, right_eye, nose, mouth_l, mouth_r = k
    eye_mid = (left_eye + right_eye) / 2.0
    mouth_mid = (mouth_l + mouth_r) / 2.0
    iod = float(np.linalg.norm(right_eye - left_eye))
    if iod < 1e-6:
        return 0.0, 0.0
    yaw = math.degrees(math.atan2(2.0 * (nose[0] - eye_mid[0]), iod))
    span = float(mouth_mid[1] - eye_mid[1])
    ratio = (nose[1] - eye_mid[1]) / span if abs(span) > 1e-6 else 0.55
    pitch = (ratio - 0.55) * 90.0
    return yaw, pitch


def quality_issues(size_px: float, blur_var: float, yaw: float, pitch: float) -> list[str]:
    issues = []
    if size_px < settings.face_min_size_px:
        issues.append("FACE_TOO_SMALL")
    if blur_var < settings.face_min_blur_var:
        issues.append("FACE_BLURRY")
    if abs(yaw) > settings.face_max_yaw_deg or abs(pitch) > settings.face_max_pitch_deg:
        issues.append("FACE_TURNED_AWAY")
    return issues


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    v = np.asarray(vec, dtype=np.float32).reshape(-1)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(l2_normalize(a), l2_normalize(b)))


# --- Model wrapper ---------------------------------------------------------------


def decode_to_bgr(image_bytes: bytes) -> Optional[np.ndarray]:
    try:
        from PIL import Image

        rgb = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    except Exception as exc:  # noqa: BLE001 - any decode failure means "not an image"
        logger.info("Image could not be decoded: %s", type(exc).__name__)
        return None
    return rgb[:, :, ::-1].copy()


class FaceAI:
    def __init__(self) -> None:
        self._app = None
        self._tried = False
        self.init_error: Optional[str] = None

    @property
    def loaded(self) -> bool:
        return self._app is not None

    @property
    def available(self) -> bool:
        self._ensure_ready()
        return self._app is not None

    def _ensure_ready(self) -> None:
        if self._tried:
            return
        self._tried = True
        try:
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(
                name=settings.insightface_model,
                root=settings.model_root,
                allowed_modules=["detection", "recognition"],
                providers=["CPUExecutionProvider"],
            )
            app.prepare(ctx_id=-1, det_size=(640, 640))
            self._app = app
            logger.info("InsightFace ready (%s)", settings.insightface_model)
        except Exception as exc:  # noqa: BLE001 - heavy optional dependency
            self.init_error = f"InsightFace unavailable: {type(exc).__name__}: {exc}"
            logger.warning(self.init_error)

    def analyze(self, image_bytes: bytes) -> Optional[list[DetectedFace]]:
        """All faces in the image, largest first. None if the model is unavailable.

        An image that cannot be decoded yields an empty list (no faces).
        """
        self._ensure_ready()
        if self._app is None:
            return None
        bgr = decode_to_bgr(image_bytes)
        if bgr is None:
            return []
        gray = bgr[:, :, ::-1].mean(axis=2)
        faces: list[DetectedFace] = []
        for f in self._app.get(bgr):
            x1, y1, x2, y2 = (float(v) for v in f.bbox)
            size = min(x2 - x1, y2 - y1)
            crop = gray[max(int(y1), 0) : max(int(y2), 0), max(int(x1), 0) : max(int(x2), 0)]
            blur = laplacian_variance(crop)
            pose = getattr(f, "pose", None)
            if pose is not None:
                pitch, yaw = float(pose[0]), float(pose[1])
            else:
                yaw, pitch = pose_from_landmarks(f.kps)
            faces.append(
                DetectedFace(
                    bbox=(x1, y1, x2, y2),
                    embedding=l2_normalize(f.normed_embedding),
                    det_score=float(f.det_score),
                    size_px=size,
                    blur_var=blur,
                    yaw=yaw,
                    pitch=pitch,
                    issues=quality_issues(size, blur, yaw, pitch),
                )
            )
        faces.sort(key=lambda d: d.size_px, reverse=True)
        return faces


def _make_engine():
    if settings.face_engine == "fake":
        from app.ai.face_fake import FakeFaceAI

        logger.warning("FACE_ENGINE=fake: development/e2e only, never for real faces")
        return FakeFaceAI()
    return FaceAI()


face_ai = _make_engine()

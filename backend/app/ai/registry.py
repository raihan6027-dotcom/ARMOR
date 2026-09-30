"""Loads the pre-deployment ArcFace registry (official_face_registry.pkl) and
matches query embeddings against it via cosine similarity.

Lazy-loaded on first use so the app boots (and tests run) even when the model
files are absent — in that case `available` is False and callers fall back safely.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("registry")


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class FaceRegistry:
    def __init__(self) -> None:
        self._labels: Optional[np.ndarray] = None
        self._matrix: Optional[np.ndarray] = None  # L2-normalized (N, 512)
        self._load_error: Optional[str] = None
        self._loaded = False

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._matrix is not None

    @property
    def loaded(self) -> bool:
        """Whether the registry is already in memory (does not trigger a load)."""
        return self._matrix is not None

    def file_exists(self) -> bool:
        return os.path.exists(self._path())

    @property
    def size(self) -> int:
        self._ensure_loaded()
        return 0 if self._matrix is None else self._matrix.shape[0]

    def _path(self) -> str:
        return os.path.join(settings.model_dir, settings.face_registry_file)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        path = self._path()
        if not os.path.exists(path):
            self._load_error = f"registry file not found: {path}"
            logger.warning(self._load_error)
            return
        try:
            import pandas as pd

            df = pd.read_pickle(path)
            emb_col = next(c for c in df.columns if "embed" in c.lower())
            id_col = next(
                c for c in df.columns
                if any(k in c.lower() for k in ("id", "ident", "name", "nama", "label"))
            )
            matrix = np.vstack([np.asarray(v, dtype=np.float32).flatten() for v in df[emb_col]])
            self._matrix = _l2_normalize(matrix.astype(np.float32))
            self._labels = df[id_col].astype(str).to_numpy()
            logger.info("Face registry loaded: %d identities", self._matrix.shape[0])
        except Exception as exc:  # pragma: no cover - depends on data files
            self._load_error = f"failed to load registry: {exc}"
            logger.warning(self._load_error)
            self._matrix = None

    def identify(self, embedding: np.ndarray) -> Optional[tuple[str, float]]:
        """Return (identity_id, cosine_score) of the closest registry entry, or None."""
        self._ensure_loaded()
        if self._matrix is None:
            return None
        q = np.asarray(embedding, dtype=np.float32).flatten()
        n = np.linalg.norm(q)
        if n == 0:
            return None
        q = q / n
        scores = self._matrix @ q
        idx = int(np.argmax(scores))
        return str(self._labels[idx]), float(scores[idx])

    def score_against(self, embedding: np.ndarray, identity_id: str) -> Optional[float]:
        """Best cosine score of `embedding` vs all registry rows for `identity_id`."""
        self._ensure_loaded()
        if self._matrix is None or self._labels is None:
            return None
        mask = self._labels == str(identity_id)
        if not mask.any():
            return None
        q = np.asarray(embedding, dtype=np.float32).flatten()
        n = np.linalg.norm(q)
        if n == 0:
            return None
        q = q / n
        return float(np.max(self._matrix[mask] @ q))


face_registry = FaceRegistry()

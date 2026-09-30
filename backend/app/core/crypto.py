"""Encryption of biometric embeddings at rest (CLAUDE.md bagian 9).

Embeddings are stored only as Fernet tokens keyed by ARMOR_EMBEDDING_KEY from the
environment. Without a key nothing biometric can be stored or read: enrollment
and matching fail closed instead of silently writing plaintext.
"""

from __future__ import annotations

import numpy as np
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import ArmorError


def _fernet() -> Fernet:
    key = settings.armor_embedding_key
    if not key:
        raise ArmorError(
            "EMBEDDING_KEY_MISSING",
            "ARMOR_EMBEDDING_KEY is not configured; biometric data cannot be stored.",
            503,
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise ArmorError("EMBEDDING_KEY_INVALID", "ARMOR_EMBEDDING_KEY is not valid.", 503) from exc


def encrypt_embedding(vec: np.ndarray) -> str:
    data = np.asarray(vec, dtype=np.float32).tobytes()
    return _fernet().encrypt(data).decode("ascii")


def decrypt_embedding(token: str) -> np.ndarray:
    try:
        raw = _fernet().decrypt(token.encode("ascii"))
    except InvalidToken as exc:
        raise ArmorError(
            "EMBEDDING_DECRYPT_FAILED",
            "A stored embedding could not be decrypted (wrong ARMOR_EMBEDDING_KEY?).",
            500,
        ) from exc
    return np.frombuffer(raw, dtype=np.float32).copy()

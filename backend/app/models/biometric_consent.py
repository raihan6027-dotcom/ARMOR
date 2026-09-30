from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BiometricConsent(Base):
    """Lapis 1 consent record: the owner agreed to biometric processing of one
    media, under a specific version of the consent text (docs/consent-text/).
    Revoking sets revoked_at and deletes that media's embedding."""

    __tablename__ = "biometric_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    identity_id: Mapped[str] = mapped_column(String(64), index=True)
    media: Mapped[str] = mapped_column(String(8))  # FACE | VOICE
    text_version: Mapped[str] = mapped_column(String(32))  # e.g. face-v1
    agreed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

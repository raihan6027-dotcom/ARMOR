from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consent_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    request_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    identity_id: Mapped[str] = mapped_column(String(64), index=True)
    requester_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Scope of the consent: None means "any" for that dimension.
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media: Mapped[str | None] = mapped_column(String(8), nullable=True)  # FACE | VOICE
    status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING|GRANTED|DENIED
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

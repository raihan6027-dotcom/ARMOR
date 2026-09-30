from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Case(Base):
    """An appeal against a DENY or a false-enrollment dispute (Fase 6 adds review)."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(32))  # APPEAL | DISPUTE
    status: Mapped[str] = mapped_column(String(16), default="SUBMITTED")
    reporter_id: Mapped[str] = mapped_column(String(64), index=True)
    # DISPUTE: the identity the reporter says is theirs. APPEAL: None.
    identity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # APPEAL
    media: Mapped[str | None] = mapped_column(String(8), nullable=True)  # FACE | VOICE
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

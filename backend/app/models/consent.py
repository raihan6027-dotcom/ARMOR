from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now
from app.db.database import Base


class Consent(Base):
    """Lapis 2 consent: a requester asked, the owner answered with a scope and a
    validity. GRANTED stops counting once revoked, expired, or (single use) used."""

    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consent_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    identity_id: Mapped[str] = mapped_column(String(64), index=True)
    requester_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # Scope: None means "any" for that dimension.
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media: Mapped[str | None] = mapped_column(String(8), nullable=True)  # FACE | VOICE

    status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING|GRANTED|DENIED
    # ONCE | DAYS_1 | DAYS_7 | DAYS_30 | UNTIL
    validity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now
from app.db.database import Base


class Case(Base):
    """An appeal against a DENY, or a false-enrollment dispute."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(16))  # APPEAL | DISPUTE
    # SUBMITTED | REVIEWING | RESOLVED
    status: Mapped[str] = mapped_column(String(16), default="SUBMITTED")
    reporter_id: Mapped[str] = mapped_column(String(64), index=True)
    assigned_reviewer_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    # DISPUTE: the identity the reporter claims is theirs (never shown to the reporter).
    identity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # APPEAL
    media: Mapped[str | None] = mapped_column(String(8), nullable=True)  # FACE | VOICE
    verification_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)  # context from the reporter
    outcome: Mapped[str | None] = mapped_column(String(24), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Reviewer label corrections (Fase 6b learning loop).
    corrected_intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    corrected_risk: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class CaseEvent(Base):
    """Timeline entries shown to the reporter (Diajukan, Ditinjau, Selesai)."""

    __tablename__ = "case_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

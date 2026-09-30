from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Request(Base):
    """One gateway evaluation and its final decision. Targets live in request_targets;
    no media is ever stored."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    requester_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    prompt: Mapped[str] = mapped_column(Text)

    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intent_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)

    decision: Mapped[str] = mapped_column(String(16))  # ALLOW | REVIEW | DENY
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # What the requester was shown (uniform, never reveals registration status).
    requester_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requester_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # JSON list of per-target results: for the identity owner and audit only.
    per_target_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)

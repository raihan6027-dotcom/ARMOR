from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now
from app.db.database import Base


class Request(Base):
    """One gateway evaluation and its current decision. Targets live in
    request_targets; no media is ever stored."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    requester_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    prompt: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # The requester agreed that this prompt may be used to improve the models (6b).
    allow_training: Mapped[bool] = mapped_column(Boolean, default=False)
    # FINAL, or HELD while waiting for consent; re-evaluated when owners answer.
    status: Mapped[str] = mapped_column(String(16), default="FINAL")

    intent_original: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)  # effective intent
    intent_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    unavailable: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list

    decision: Mapped[str] = mapped_column(String(16))  # ALLOW | REVIEW | DENY
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # What the requester was shown (uniform, never reveals registration status).
    requester_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requester_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON list of per-target results: for the identity owner and audit only.
    per_target_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON: Risk AI input features and the top contributing features.
    risk_features: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON {component: version} of every model that informed this decision.
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON {stage: milliseconds}.
    stage_ms: Mapped[str | None] = mapped_column(Text, nullable=True)

    processing_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

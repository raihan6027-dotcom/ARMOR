from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now
from app.db.database import Base


class Feedback(Base):
    """A label produced by a human outcome, for retraining Intent AI and Risk AI.

    Stored only when the requester agreed that their prompt may be used to improve
    the models (Request.allow_training). No media, no identities: the prompt text,
    the content features, and the final labels.
    """

    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("request_id", "source", name="uq_feedback_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feedback_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)  # Risk AI features (JSON)
    intent_final: Mapped[str] = mapped_column(String(32))
    risk_final: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # REVIEW_RESOLVED | CONSENT_GRANTED | CONSENT_DENIED | APPEAL_UPHOLD | APPEAL_RELABEL
    source: Mapped[str] = mapped_column(String(24))
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Permission(Base):
    """An owner override of the default permission for one intent x media."""

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("identity_id", "intent", "media", name="uq_identity_intent_media"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identity_id: Mapped[str] = mapped_column(String(64), index=True)
    intent: Mapped[str] = mapped_column(String(32))  # Intent value
    media: Mapped[str] = mapped_column(String(8))  # BiometricMedia: FACE | VOICE
    decision: Mapped[str] = mapped_column(String(16))  # ALLOW | REVIEW | DENY

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

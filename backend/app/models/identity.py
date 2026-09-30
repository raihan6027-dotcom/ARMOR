from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Identity(Base):
    __tablename__ = "identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identity_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # JSON-encoded 512-D ArcFace embedding produced at enrollment. Biometric data
    # lives in the DB only — never committed to git (see .gitignore).
    embedding_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "locked" when any media has a Lock level other than NONE, else "active".
    status: Mapped[str] = mapped_column(String(32), default="active")
    # Identity Lock per biometric media (LockLevel values), CLAUDE.md bagian 6.
    face_lock: Mapped[str] = mapped_column(String(32), default="NONE")
    voice_lock: Mapped[str] = mapped_column(String(32), default="NONE")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

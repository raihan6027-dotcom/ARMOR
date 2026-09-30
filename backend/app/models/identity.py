from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Identity(Base):
    """A person protected by ARMOR, enrolled by themselves (or by a guardian).

    Biometric data is stored only as encrypted embeddings (Fernet tokens); photos
    and recordings are never stored (CLAUDE.md bagian 2, minimisasi data).
    """

    __tablename__ = "identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identity_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Guardian mode (Fase 10c): an identity a guardian enrolled for a child.
    is_child: Mapped[bool] = mapped_column(Boolean, default=False)
    # Frozen by a reviewer during a false-enrollment dispute (Fase 6).
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)

    # "locked" when any media has a Lock level other than NONE, else "active".
    status: Mapped[str] = mapped_column(String(32), default="active")
    # Identity Lock per biometric media (LockLevel values), CLAUDE.md bagian 6.
    face_lock: Mapped[str] = mapped_column(String(32), default="NONE")
    voice_lock: Mapped[str] = mapped_column(String(32), default="NONE")

    # Encrypted mean embeddings (Fernet tokens). NULL = not enrolled / revoked.
    face_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    face_enrolled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    voice_embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_enrolled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

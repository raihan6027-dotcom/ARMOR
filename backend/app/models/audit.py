from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AuditLog(Base):
    """Append-only, hash-chained: hash = sha256(prev_hash + canonical JSON of the row).
    Never holds media, embeddings, passwords, or tokens."""

    __tablename__ = "audit_log"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(48), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data: Mapped[str] = mapped_column(Text)  # canonical JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)

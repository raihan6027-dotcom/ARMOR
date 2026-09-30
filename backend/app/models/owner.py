"""Owner-side records: blocked requesters and trusted-circle members."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now
from app.db.database import Base


class Block(Base):
    """An owner blocked a requester: no more consent requests reach them."""

    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("owner_id", "requester_id", name="uq_block"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    requester_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CircleMember(Base):
    """A trusted person: a standing consent for a scope (intents x media), optional expiry."""

    __tablename__ = "circle_members"
    __table_args__ = (UniqueConstraint("identity_id", "member_id", name="uq_circle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_ref: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    identity_id: Mapped[str] = mapped_column(String(64), index=True)
    member_id: Mapped[str] = mapped_column(String(64), index=True)
    intents: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list; NULL = any
    media: Mapped[str | None] = mapped_column(String(8), nullable=True)  # FACE | VOICE | NULL
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

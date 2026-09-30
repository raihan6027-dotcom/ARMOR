from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RequestTarget(Base):
    """One person found in a gateway request, with the per-target decision.

    Visible to the identity owner (dashboard, consent inbox) and to audit; never
    to the requester. Unregistered faces have no identity_id and no embedding is
    kept for them.
    """

    __tablename__ = "request_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(8))  # FACE | VOICE | TEXT
    target_type: Mapped[str] = mapped_column(String(32))
    identity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str] = mapped_column(String(64))

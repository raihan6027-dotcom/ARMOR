from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import now
from app.db.database import Base


class ShieldRecord(Base):
    """ARMOR Shield registry: one row per output delivered after an ALLOW decision.
    Holds hashes only, never the image, the prompt, or who is in it."""

    __tablename__ = "shield_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shield_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    requester_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    media_type: Mapped[str] = mapped_column(String(16), default="IMAGE")
    # POLICY_ALLOWED | OWNER_PERMITTED (see app/services/shield_service.py)
    permission_status: Mapped[str] = mapped_column(String(32))
    generator: Mapped[str] = mapped_column(String(64))
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    # SHA-256 of the decoded RGB pixels: survives metadata stripping / lossless re-save.
    pixel_sha256: Mapped[str] = mapped_column(String(64), index=True)
    phash: Mapped[str] = mapped_column(String(16), index=True)  # 64-bit perceptual hash, hex
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)

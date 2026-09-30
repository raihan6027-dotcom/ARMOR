"""Owner features: trusted circle, notifications, activity dashboard."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schema.common import BiometricMedia, Intent
from app.services import circle_service, dashboard_service, notify_service

router = APIRouter(tags=["Pemilik"])


class CircleAdd(BaseModel):
    identity_id: str
    email: EmailStr
    intents: Optional[list[Intent]] = None  # None = every purpose the owner can permit
    media: Optional[BiometricMedia] = None  # None = face and voice
    expires_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "identity_id": "<identity_id milikmu>",
                    "email": "sinta@example.com",
                    "intents": ["PERSONAL_CREATION"],
                    "media": "FACE",
                    "expires_at": "2026-12-31T23:59:59",
                }
            ]
        }
    }


class MarkRead(BaseModel):
    ids: Optional[list[str]] = Field(default=None, description="None = tandai semua dibaca")


@router.get("/circle")
def list_circle(
    identity_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Lingkaran tepercaya sebuah identitas milikmu."""
    return {"items": circle_service.list_for(db, current.user_id, identity_id)}


@router.post("/circle", status_code=201)
def add_to_circle(
    body: CircleAdd,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Tambah orang ke lingkaran tepercaya lewat email, dengan cakupan dan masa berlaku."""
    return circle_service.add(
        db, current.user_id, body.identity_id, body.email, body.intents, body.media, body.expires_at
    )


@router.delete("/circle/{member_ref}", status_code=204)
def remove_from_circle(
    member_ref: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    circle_service.remove(db, current.user_id, member_ref)


@router.get("/notifications")
def list_notifications(
    unread: bool = Query(False),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return notify_service.list_for(db, current.user_id, unread_only=unread)


@router.post("/notifications/read")
def mark_notifications_read(
    body: MarkRead,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return {"marked": notify_service.mark_read(db, current.user_id, body.ids)}


@router.get("/dashboard/activity")
def activity(
    weeks: int = Query(8, ge=1, le=52),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Upaya penggunaan identitasmu per minggu: diblokir, disetujui, menunggu. Pengirim
    hanya ditampilkan jika ia mengajukan permintaan persetujuan."""
    return dashboard_service.activity(db, current.user_id, weeks)

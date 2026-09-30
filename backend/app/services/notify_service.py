"""In-app notifications, plus optional e-mail over SMTP.

E-mail is sent only when EMAIL_ENABLED=true in the config AND the user turned on
e-mail notifications. It is off by default and in the offline demo. A failed
e-mail never breaks the action that triggered it.
"""

from __future__ import annotations

import json
import smtplib
import uuid
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.timeutil import now
from app.models.notification import Notification
from app.models.user import User

logger = get_logger("notify")


def send_email(to: str, subject: str, body: str) -> bool:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001 - e-mail is best effort
        logger.warning("E-mail not sent: %s", type(exc).__name__)
        return False


def notify(
    db: Session,
    user_id: str,
    kind: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> Notification:
    row = Notification(
        notification_id=str(uuid.uuid4()),
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        data=json.dumps(data or {}, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    if settings.email_enabled:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user is not None and user.email_notifications:
            send_email(user.email, f"ARMOR: {title}", body)
    return row


def as_dict(n: Notification) -> dict:
    return {
        "notification_id": n.notification_id,
        "kind": n.kind,
        "title": n.title,
        "body": n.body,
        "data": json.loads(n.data or "{}"),
        "read": n.read_at is not None,
        "created_at": n.created_at.isoformat(),
    }


def list_for(db: Session, user_id: str, unread_only: bool = False, limit: int = 100) -> dict:
    q = db.query(Notification).filter(Notification.user_id == user_id)
    unread = q.filter(Notification.read_at.is_(None)).count()
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).all()
    return {"items": [as_dict(n) for n in rows], "unread": unread}


def mark_read(db: Session, user_id: str, ids: list[str] | None) -> int:
    q = db.query(Notification).filter(
        Notification.user_id == user_id, Notification.read_at.is_(None)
    )
    if ids is not None:
        q = q.filter(Notification.notification_id.in_(ids))
    rows = q.all()
    stamp = now()
    for n in rows:
        n.read_at = stamp
    db.commit()
    return len(rows)

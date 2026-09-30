"""Owner activity dashboard: attempts to use your identity, per week.

A requester is identified to the owner only if they filed a consent request for
that request (CLAUDE.md Fase 6 task 8); otherwise "Pengirim tidak diketahui".
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.timeutil import now
from app.models.consent import Consent
from app.models.identity import Identity
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.models.user import User
from app.policy.explain import REASONS
from app.schema.common import IdentityTarget

UNKNOWN_SENDER = "Pengirim tidak diketahui"
_BUCKET = {"DENY": "blocked", "ALLOW": "approved", "REVIEW": "pending"}


def _week_start(day):
    d = day.date() if hasattr(day, "date") else day
    return d - timedelta(days=d.weekday())


def activity(db: Session, user_id: str, weeks: int = 8) -> dict:
    ids = [i.identity_id for i in db.query(Identity).filter(Identity.user_id == user_id).all()]
    first_week = _week_start(now()) - timedelta(weeks=weeks - 1)
    buckets = {
        first_week + timedelta(weeks=k): {"attempts": 0, "blocked": 0, "approved": 0, "pending": 0}
        for k in range(weeks)
    }
    events = []
    if ids:
        rows = (
            db.query(RequestTarget, Request)
            .join(Request, Request.request_id == RequestTarget.request_id)
            .filter(
                RequestTarget.identity_id.in_(ids),
                RequestTarget.target_type == IdentityTarget.OTHER_REGISTERED.value,
            )
            .order_by(Request.created_at.desc())
            .all()
        )
        for target, req in rows:
            week = _week_start(req.created_at)
            if week in buckets:
                b = buckets[week]
                b["attempts"] += 1
                b[_BUCKET[target.decision]] += 1
            if len(events) < 30:
                consent = (
                    db.query(Consent)
                    .filter(
                        Consent.identity_id == target.identity_id,
                        Consent.request_id == req.request_id,
                        Consent.requester_id == req.requester_id,
                    )
                    .first()
                )
                sender = UNKNOWN_SENDER
                if consent is not None:
                    user = db.query(User).filter(User.user_id == req.requester_id).first()
                    sender = user.email if user else UNKNOWN_SENDER
                events.append(
                    {
                        "request_id": req.request_id,
                        "identity_id": target.identity_id,
                        "created_at": req.created_at.isoformat(),
                        "media_type": req.media_type,
                        "intent": req.intent,
                        "decision": target.decision,
                        "reason_code": target.reason_code,
                        "reason": REASONS.get(target.reason_code, ""),
                        "sender": sender,
                    }
                )
    series = [{"week_start": w.isoformat(), **counts} for w, counts in sorted(buckets.items())]
    this_week = series[-1]
    return {
        "weeks": series,
        "this_week": this_week,
        "totals": {
            k: sum(s[k] for s in series) for k in ("attempts", "blocked", "approved", "pending")
        },
        "recent": events,
    }

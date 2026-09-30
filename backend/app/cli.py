"""ARMOR admin CLI. REVIEWER and ADMIN roles can only be granted here.

python -m app.cli role grant --email peninjau@example.com --role REVIEWER
python -m app.cli role revoke --email peninjau@example.com
python -m app.cli platform create --email dev@platform.example --password <kata-sandi>
python -m app.cli logs purge [--days 90]
python -m app.cli audit verify
python -m app.cli feedback export [--out ../ml/feedback/feedback.csv]
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import REPO_ROOT, settings
from app.core.security import hash_password
from app.core.timeutil import now
from app.db.database import SessionLocal, init_db
from app.models.audit import AuditLog
from app.models.consent import Consent
from app.models.notification import Notification
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.models.user import User
from app.services import audit_service, feedback_service

GRANTABLE = ("REVIEWER", "ADMIN")
FEEDBACK_CSV = REPO_ROOT / "ml" / "feedback" / "feedback.csv"


def _user(db: Session, email: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    if user is None:
        raise SystemExit(f"Tidak ada akun dengan email {email}.")
    return user


def role_grant(db: Session, email: str, role: str) -> str:
    if role not in GRANTABLE:
        raise SystemExit(f"Peran harus salah satu dari {GRANTABLE}.")
    user = _user(db, email)
    user.role = role
    audit_service.record(
        db, "ROLE_GRANTED", None, {"user_id": user.user_id, "role": role, "via": "cli"}
    )
    db.commit()
    return f"{email} sekarang {role}."


def role_revoke(db: Session, email: str) -> str:
    user = _user(db, email)
    previous, user.role = user.role, "USER"
    audit_service.record(
        db, "ROLE_REVOKED", None, {"user_id": user.user_id, "previous": previous, "via": "cli"}
    )
    db.commit()
    return f"{email} kembali menjadi USER."


def platform_create(db: Session, email: str, password: str) -> str:
    if len(password) < 12:
        raise SystemExit("Kata sandi akun platform minimal 12 karakter.")
    if db.query(User).filter(User.email == email.lower()).first():
        raise SystemExit("Email sudah dipakai.")
    user = User(
        user_id=str(uuid.uuid4()),
        email=email.lower(),
        password_hash=hash_password(password),
        role="PLATFORM",
    )
    db.add(user)
    audit_service.record(db, "PLATFORM_CREATED", None, {"user_id": user.user_id, "via": "cli"})
    db.commit()
    return f"Akun platform {email} dibuat."


def purge_logs(db: Session, days: int) -> dict:
    """Delete decision logs (and their targets, answered consents that point at them,
    read notifications, and audit rows) older than `days`. The audit chain keeps
    verifying because the first remaining row's prev_hash is the new anchor, which
    is recorded in a LOG_PURGED event."""
    cutoff = now() - timedelta(days=days)
    old = [r.request_id for r in db.query(Request).filter(Request.created_at < cutoff).all()]
    counts = {"requests": len(old)}
    if old:
        counts["targets"] = (
            db.query(RequestTarget)
            .filter(RequestTarget.request_id.in_(old))
            .delete(synchronize_session=False)
        )
        db.query(Consent).filter(Consent.request_id.in_(old), Consent.status == "PENDING").delete(
            synchronize_session=False
        )
        db.query(Request).filter(Request.request_id.in_(old)).delete(synchronize_session=False)
    counts["notifications"] = (
        db.query(Notification)
        .filter(Notification.created_at < cutoff, Notification.read_at.is_not(None))
        .delete(synchronize_session=False)
    )
    old_audit = db.query(AuditLog).filter(AuditLog.created_at < cutoff).order_by(AuditLog.seq).all()
    counts["audit"] = len(old_audit)
    anchor = old_audit[-1].hash if old_audit else None
    for row in old_audit:
        db.delete(row)
    db.flush()
    audit_service.record(
        db, "LOG_PURGED", None, {"older_than_days": days, "counts": counts, "anchor": anchor}
    )
    db.commit()
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m app.cli", description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = ap.add_subparsers(dest="group", required=True)
    role = sub.add_parser("role").add_subparsers(dest="cmd", required=True)
    g = role.add_parser("grant")
    g.add_argument("--email", required=True)
    g.add_argument("--role", required=True, choices=GRANTABLE)
    r = role.add_parser("revoke")
    r.add_argument("--email", required=True)
    plat = sub.add_parser("platform").add_subparsers(dest="cmd", required=True)
    pc = plat.add_parser("create")
    pc.add_argument("--email", required=True)
    pc.add_argument("--password", required=True)
    logs = sub.add_parser("logs").add_subparsers(dest="cmd", required=True)
    lp = logs.add_parser("purge")
    lp.add_argument("--days", type=int, default=settings.log_retention_days)
    audit = sub.add_parser("audit").add_subparsers(dest="cmd", required=True)
    audit.add_parser("verify")
    fb = sub.add_parser("feedback").add_subparsers(dest="cmd", required=True)
    fe = fb.add_parser("export")
    fe.add_argument("--out", default=str(FEEDBACK_CSV))
    args = ap.parse_args(argv)

    init_db()
    with SessionLocal() as db:
        if args.group == "role" and args.cmd == "grant":
            print(role_grant(db, args.email, args.role))
        elif args.group == "role":
            print(role_revoke(db, args.email))
        elif args.group == "platform":
            print(platform_create(db, args.email, args.password))
        elif args.group == "feedback":
            n = feedback_service.export_csv(db, Path(args.out))
            print(f"{n} baris feedback -> {args.out}. Periksa dan isi diperiksa_oleh.")
        elif args.group == "logs":
            print(json.dumps(purge_logs(db, args.days)))
        else:
            result = audit_service.verify(db)
            print(json.dumps(result))
            return 0 if result["ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

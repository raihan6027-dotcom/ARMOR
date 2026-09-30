"""Hash-chained audit log (CLAUDE.md bagian 9).

Each row stores hash = sha256(prev_hash + canonical JSON of the row), so changing,
deleting or reordering any row breaks every hash after it. `verify` recomputes
the chain. Purging old rows (log retention) leaves the first remaining row's
prev_hash as the anchor and records a LOG_PURGED event with that anchor.

Never put media, embeddings, passwords, tokens, or prompts in `data`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.timeutil import now
from app.models.audit import AuditLog

GENESIS = "0" * 64


def _canonical(event: str, actor_id: str | None, data: str, created_at: datetime) -> str:
    return json.dumps(
        {
            "event": event,
            "actor_id": actor_id,
            "data": data,
            "created_at": created_at.isoformat(timespec="microseconds"),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _hash(prev_hash: str, canonical: str) -> str:
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def record(db: Session, event: str, actor_id: str | None, data: dict) -> AuditLog:
    """Append one event. The caller commits (together with the change it describes)."""
    last = db.query(AuditLog).order_by(AuditLog.seq.desc()).first()
    prev = last.hash if last else GENESIS
    payload = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    created = now()
    row = AuditLog(
        event=event,
        actor_id=actor_id,
        data=payload,
        created_at=created,
        prev_hash=prev,
        hash=_hash(prev, _canonical(event, actor_id, payload, created)),
    )
    db.add(row)
    db.flush()  # so the next record() in this transaction chains onto this row
    return row


def verify(db: Session) -> dict:
    rows = db.query(AuditLog).order_by(AuditLog.seq).all()
    if not rows:
        return {"ok": True, "count": 0, "broken_at": None, "anchor": GENESIS}
    anchor = rows[0].prev_hash
    prev = anchor
    for row in rows:
        expected = _hash(prev, _canonical(row.event, row.actor_id, row.data, row.created_at))
        if row.prev_hash != prev or row.hash != expected:
            return {"ok": False, "count": len(rows), "broken_at": row.seq, "anchor": anchor}
        prev = row.hash
    return {"ok": True, "count": len(rows), "broken_at": None, "anchor": anchor}


def for_subject(db: Session, key: str, value: str, limit: int = 50) -> list[dict]:
    """Audit events whose data mentions key=value (e.g. request_id), oldest first."""
    needle = json.dumps({key: value}, separators=(",", ":"))[1:-1]
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.data.contains(needle))
        .order_by(AuditLog.seq)
        .limit(limit)
        .all()
    )
    return [
        {
            "seq": r.seq,
            "event": r.event,
            "actor_id": r.actor_id,
            "data": json.loads(r.data),
            "created_at": r.created_at.isoformat(),
            "hash": r.hash,
        }
        for r in rows
    ]

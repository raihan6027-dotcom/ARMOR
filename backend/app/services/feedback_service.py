"""Learning-loop labels (Fase 6b).

Human outcomes become training labels for Intent AI and Risk AI:

* REVIEW_RESOLVED: a held request reached a final decision after human input;
* CONSENT_GRANTED / CONSENT_DENIED: an owner answered with the prompt in view;
* APPEAL_UPHOLD / APPEAL_RELABEL: a reviewer confirmed or corrected the labels.

Only for requests whose requester opted in (allow_training). Nothing is used for
training until a team member reviewed the exported rows (column diperiksa_oleh),
and the frozen test set never receives feedback (ml/retrain.py).
"""

from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.request import Request

EXPORT_FIELDS = [
    "feedback_id",
    "request_id",
    "prompt",
    "media_type",
    "intent_final",
    "risk_final",
    "source",
    "features",
    "model_version",
    "created_at",
    "diperiksa_oleh",
]


def record(
    db: Session,
    req: Request,
    source: str,
    intent_final: Optional[str] = None,
    risk_final: Optional[str] = None,
) -> Optional[Feedback]:
    if not req.allow_training:
        return None
    existing = (
        db.query(Feedback)
        .filter(Feedback.request_id == req.request_id, Feedback.source == source)
        .first()
    )
    row = existing or Feedback(
        feedback_id=str(uuid.uuid4()), request_id=req.request_id, source=source
    )
    row.prompt = req.prompt
    row.media_type = req.media_type
    row.features = json.dumps(json.loads(req.risk_features or "{}").get("features", {}))
    row.intent_final = intent_final or req.intent_original or req.intent
    row.risk_final = risk_final or req.risk_level
    row.model_version = req.model_version
    if existing is None:
        db.add(row)
    return row


def export_csv(db: Session, path: Path) -> int:
    """Write every feedback row for team review. diperiksa_oleh stays empty; rows
    already reviewed in an existing file keep their reviewer."""
    reviewed = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            reviewed = {r["feedback_id"]: r for r in csv.DictReader(f) if r.get("diperiksa_oleh")}
    rows = db.query(Feedback).order_by(Feedback.created_at).all()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EXPORT_FIELDS)
        w.writeheader()
        for r in rows:
            prior = reviewed.get(r.feedback_id)
            w.writerow(
                {
                    "feedback_id": r.feedback_id,
                    "request_id": r.request_id,
                    "prompt": r.prompt,
                    "media_type": r.media_type,
                    # A reviewer may have corrected labels in the CSV: keep their version.
                    "intent_final": prior["intent_final"] if prior else r.intent_final,
                    "risk_final": prior["risk_final"] if prior else r.risk_final,
                    "source": r.source,
                    "features": r.features,
                    "model_version": r.model_version,
                    "created_at": r.created_at.isoformat(),
                    "diperiksa_oleh": prior["diperiksa_oleh"] if prior else "",
                }
            )
    return len(rows)

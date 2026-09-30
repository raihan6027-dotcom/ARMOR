"""Output Guard: the generator's result is checked again by Face AI before anyone
sees it (CLAUDE.md bagian 3 and Lampiran B: "prompt aman tetapi hasil memuat
wajah terdaftar").

A face in the output passes when it is:
  - the requester's own enrolled face (SELF),
  - a face that is not enrolled (OTHER_UNREGISTERED), or
  - an enrolled person whom the decision for this very request allowed.
Anything else holds the output: another enrolled person, a face in the gray zone
or of low quality (UNCLEAR), or Face AI being unavailable (fail safe). A held
output is discarded, never stored; the event goes to the audit log and every
affected owner is notified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.face import DetectedFace, face_ai
from app.models.request import Request
from app.models.request_target import RequestTarget
from app.schema.common import Decision, IdentityTarget
from app.services import identity_service

# Why an output was held (internal; the requester sees one uniform message).
HELD_REGISTERED = "OUTPUT_REGISTERED_NOT_ALLOWED"
HELD_UNCLEAR = "OUTPUT_FACE_UNCLEAR"
HELD_UNAVAILABLE = "OUTPUT_CHECK_UNAVAILABLE"


@dataclass
class GuardResult:
    passed: bool
    faces: int = 0
    reasons: list[str] = field(default_factory=list)
    # Enrolled identities found in the output without permission for this request.
    blocked_identity_ids: list[str] = field(default_factory=list)


def allowed_identities(db: Session, row: Request) -> set[str]:
    rows = (
        db.query(RequestTarget)
        .filter(
            RequestTarget.request_id == row.request_id,
            RequestTarget.decision == Decision.ALLOW.value,
            RequestTarget.identity_id.is_not(None),
        )
        .all()
    )
    return {r.identity_id for r in rows}


def judge(
    faces: Optional[list[DetectedFace]],
    requester_user_id: str,
    index: list,
    allowed: set[str],
) -> GuardResult:
    """The Output Guard rule on already-detected faces (None = Face AI unavailable).
    Pure: also used by ml/output_guard_eval so the evaluation measures this code."""
    if faces is None:
        return GuardResult(passed=False, reasons=[HELD_UNAVAILABLE])
    result = GuardResult(passed=True, faces=len(faces))
    for face in faces:
        match = identity_service.classify_face(face, requester_user_id, index)
        face.embedding = None  # nothing about faces in the output is kept
        if match.target in (IdentityTarget.SELF, IdentityTarget.OTHER_UNREGISTERED):
            continue
        if match.target is IdentityTarget.UNCLEAR:
            result.passed = False
            result.reasons.append(HELD_UNCLEAR)
            continue
        identity_id = match.identity.identity_id if match.identity else None
        if identity_id in allowed:
            continue
        result.passed = False
        result.reasons.append(HELD_REGISTERED)
        if identity_id and identity_id not in result.blocked_identity_ids:
            result.blocked_identity_ids.append(identity_id)
    return result


def check(db: Session, row: Request, output: bytes) -> GuardResult:
    faces = face_ai.analyze(output)
    index = identity_service.registered_face_embeddings(db) if faces else []
    allowed = allowed_identities(db, row) if faces else set()
    return judge(faces, row.requester_id, index, allowed)

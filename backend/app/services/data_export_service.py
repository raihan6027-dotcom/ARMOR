"""Export of everything ARMOR stores about one user (GET /me/data).

Biometric embeddings are reported only as "stored / not stored" with dates; the
vectors themselves, password hashes and tokens are never exported.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.biometric_consent import BiometricConsent
from app.models.case import Case
from app.models.consent import Consent
from app.models.identity import Identity
from app.models.permission import Permission
from app.models.request import Request
from app.models.shield import ShieldRecord
from app.models.user import User

RETENTION = {
    "account": "Sampai akun dihapus.",
    "face_embedding": "Sampai persetujuan wajah dicabut atau identitas dihapus.",
    "voice_embedding": "Sampai persetujuan suara dicabut atau identitas dihapus.",
    "photos_and_recordings": "Tidak disimpan. Hanya diproses di memori lalu dibuang.",
    "decision_log": "Log keputusan (tanpa media) disimpan 90 hari lalu dihapus otomatis.",
    "consent_records": "Selama identitas terdaftar, sebagai bukti persetujuan.",
    "generated_outputs": "Hasil generator tidak disimpan. Hanya hash-nya di registri ARMOR Shield "
    "agar keasliannya bisa diverifikasi.",
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def export(db: Session, user: User) -> dict:
    identities = db.query(Identity).filter(Identity.user_id == user.user_id).all()
    ids = [i.identity_id for i in identities]
    in_ids = (lambda col: col.in_(ids)) if ids else (lambda col: col.in_([""]))

    return {
        "exported_by": "ARMOR",
        "retention": RETENTION,
        "account": {
            "user_id": user.user_id,
            "email": user.email,
            "created_at": _iso(user.created_at),
        },
        "identities": [
            {
                "identity_id": i.identity_id,
                "display_name": i.display_name,
                "is_child": i.is_child,
                "status": i.status,
                "face_lock": i.face_lock,
                "voice_lock": i.voice_lock,
                "face_embedding_stored": i.face_embedding is not None,
                "face_enrolled_at": _iso(i.face_enrolled_at),
                "voice_embedding_stored": i.voice_embedding is not None,
                "voice_enrolled_at": _iso(i.voice_enrolled_at),
                "created_at": _iso(i.created_at),
            }
            for i in identities
        ],
        "biometric_consents": [
            {
                "record_id": c.record_id,
                "identity_id": c.identity_id,
                "media": c.media,
                "text_version": c.text_version,
                "current_text_version": (
                    settings.consent_text_face if c.media == "FACE" else settings.consent_text_voice
                ),
                "agreed_at": _iso(c.agreed_at),
                "revoked_at": _iso(c.revoked_at),
            }
            for c in db.query(BiometricConsent)
            .filter(BiometricConsent.user_id == user.user_id)
            .order_by(BiometricConsent.agreed_at)
            .all()
        ],
        "permissions": [
            {
                "identity_id": p.identity_id,
                "intent": p.intent,
                "media": p.media,
                "decision": p.decision,
            }
            for p in db.query(Permission).filter(in_ids(Permission.identity_id)).all()
        ],
        "consent_requests_received": [
            {
                "consent_id": c.consent_id,
                "identity_id": c.identity_id,
                "requester_id": c.requester_id,
                "intent": c.intent,
                "media": c.media,
                "status": c.status,
                "created_at": _iso(c.created_at),
            }
            for c in db.query(Consent).filter(in_ids(Consent.identity_id)).all()
        ],
        "consent_requests_sent": [
            {
                "consent_id": c.consent_id,
                "request_id": c.request_id,
                "intent": c.intent,
                "media": c.media,
                "status": c.status,
                "created_at": _iso(c.created_at),
            }
            for c in db.query(Consent).filter(Consent.requester_id == user.user_id).all()
        ],
        "requests_made": [
            {
                "request_id": r.request_id,
                "prompt": r.prompt,
                "media_type": r.media_type,
                "decision": r.decision,
                "reason_code": r.requester_code,
                "output_status": r.output_status,
                "created_at": _iso(r.created_at),
            }
            for r in db.query(Request).filter(Request.requester_id == user.user_id).all()
        ],
        "shield_records": [
            {
                "shield_id": s.shield_id,
                "request_id": s.request_id,
                "permission_status": s.permission_status,
                "generator": s.generator,
                "simulated": s.simulated,
                "created_at": _iso(s.created_at),
            }
            for s in db.query(ShieldRecord).filter(ShieldRecord.requester_id == user.user_id).all()
        ],
        "cases_reported": [
            {
                "case_id": c.case_id,
                "kind": c.kind,
                "status": c.status,
                "created_at": _iso(c.created_at),
            }
            for c in db.query(Case).filter(Case.reporter_id == user.user_id).all()
        ],
    }

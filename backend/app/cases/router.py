"""Cases: appeals (requesters), disputes (owners), and the reviewer console API."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.user import User
from app.schema.common import Intent, RiskLevel
from app.schema.identity import ConsentAgreement
from app.services import audit_service, case_service
from app.services.identity_service import decode_image

router = APIRouter(tags=["Kasus"])


class AppealCreate(BaseModel):
    kind: Literal["APPEAL"] = "APPEAL"
    request_id: str
    note: str = Field(min_length=3, max_length=2000, description="Konteks tambahan dari requester")


class DisputeCreate(BaseModel):
    """Re-verify your own face live (three captures, like enrollment)."""

    images: list[str] = Field(min_length=3, max_length=3)
    consent: ConsentAgreement
    note: Optional[str] = Field(default=None, max_length=2000)


class CaseResolve(BaseModel):
    # APPEAL: UPHOLD | RELABEL. DISPUTE: TRANSFER | DELETE_ENROLLMENT | REJECT.
    outcome: Literal["UPHOLD", "RELABEL", "TRANSFER", "DELETE_ENROLLMENT", "REJECT"]
    note: Optional[str] = Field(default=None, max_length=2000)
    corrected_intent: Optional[Intent] = None
    corrected_risk: Optional[RiskLevel] = None


class CaseAssign(BaseModel):
    reviewer_email: str


@router.post("/cases", status_code=201)
def create_appeal(
    body: AppealCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Ajukan banding atas keputusan DENY milikmu, dengan konteks tambahan."""
    case = case_service.create_appeal(db, current.user_id, body.request_id, body.note)
    return case_service.reporter_view(db, case)


@router.post("/cases/dispute", status_code=201)
def create_dispute(
    body: DisputeCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Laporkan bahwa wajahmu didaftarkan orang lain, dengan verifikasi ulang lewat kamera."""
    images = [decode_image(img, f"images[{i}]") for i, img in enumerate(body.images)]
    case = case_service.create_dispute(
        db, current.user_id, images, body.consent.agreed, body.consent.text_version, body.note
    )
    return case_service.reporter_view(db, case)


@router.get("/cases")
def list_cases(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Kasus milikmu; untuk peninjau, kasus yang ditugaskan; untuk admin, semua kasus."""
    return {"items": case_service.list_for(db, current)}


@router.get("/cases/{case_id}")
def get_case(
    case_id: str, db: Session = Depends(get_db), current: User = Depends(get_current_user)
):
    return case_service.detail(db, current, case_id)


@router.post("/cases/{case_id}/review")
def start_review(
    case_id: str,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_role("REVIEWER", "ADMIN")),
):
    return case_service.reviewer_view(db, case_service.start_review(db, reviewer, case_id))


@router.post("/cases/{case_id}/freeze")
def freeze_identity(
    case_id: str,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_role("REVIEWER", "ADMIN")),
):
    """Bekukan identitas yang disengketakan selama peninjauan."""
    return case_service.reviewer_view(db, case_service.freeze(db, reviewer, case_id))


@router.post("/cases/{case_id}/resolve")
def resolve_case(
    case_id: str,
    body: CaseResolve,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_role("REVIEWER", "ADMIN")),
):
    """Selesaikan kasus. Banding: pertahankan, atau koreksi label intent/risiko lalu
    policy engine memutuskan ulang. Sengketa: pindahkan kepemilikan, hapus pendaftaran
    palsu, atau tolak."""
    case = case_service.resolve(
        db, reviewer, case_id, body.outcome, body.note, body.corrected_intent, body.corrected_risk
    )
    return case_service.reviewer_view(db, case)


@router.post("/cases/{case_id}/assign")
def assign_case(
    case_id: str,
    body: CaseAssign,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("ADMIN")),
):
    return case_service.reviewer_view(
        db, case_service.assign(db, admin, case_id, body.reviewer_email)
    )


@router.get("/audit/verify")
def verify_audit_chain(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("ADMIN", "REVIEWER")),
):
    """Periksa integritas rantai hash audit log."""
    return audit_service.verify(db)

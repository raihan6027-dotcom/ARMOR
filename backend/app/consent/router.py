from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schema.common import ConsentStatus
from app.schema.consent import (
    ConsentAnswer,
    ConsentInboxResponse,
    ConsentItem,
    ConsentRequest,
    ConsentRequestResponse,
    ConsentRequestStatusResponse,
)
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["Consent"])


@router.post("/request", response_model=ConsentRequestResponse)
def request_consent(
    request: ConsentRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Minta persetujuan untuk permintaan REVIEW milikmu. Jawabannya sama, entah ada
    orang terdaftar di media itu atau tidak."""
    consent_service.request_for(
        db, request.request_id, current.user_id, request.intent, request.media
    )
    return ConsentRequestResponse(request_id=request.request_id, status=ConsentStatus.PENDING)


@router.get("/request/{request_id}", response_model=ConsentRequestStatusResponse)
def consent_status_for_request(
    request_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    status = consent_service.status_for_request(db, request_id, current.user_id)
    return ConsentRequestStatusResponse(request_id=request_id, status=status)


@router.get("/inbox", response_model=ConsentInboxResponse)
def consent_inbox(
    status: Optional[Literal["pending", "answered"]] = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Kotak consent: permintaan atas identitas milikmu."""
    return ConsentInboxResponse(
        items=consent_service.inbox(db, current.user_id, status),
        pending=consent_service.pending_count(db, current.user_id),
    )


@router.get("/{consent_id}", response_model=ConsentItem)
def get_consent(
    consent_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    consent = consent_service.get_for_owner(db, consent_id, current.user_id)
    return consent_service.as_owner_dict(db, consent)


@router.post("/{consent_id}/respond", response_model=ConsentItem)
def respond_consent(
    consent_id: str,
    answer: ConsentAnswer,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Setujui dengan cakupan dan masa berlaku, tolak, atau blokir pengirim. Permintaan
    yang tertahan langsung dinilai ulang."""
    consent = consent_service.respond(
        db,
        consent_id,
        current.user_id,
        answer.action,
        answer.intent,
        answer.media,
        answer.validity,
        answer.until,
    )
    return consent_service.as_owner_dict(db, consent)


@router.post("/{consent_id}/revoke", response_model=ConsentItem)
def revoke_consent(
    consent_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Cabut persetujuan yang sudah diberikan. Sejak saat itu dianggap tidak ada."""
    consent = consent_service.revoke(db, consent_id, current.user_id)
    return consent_service.as_owner_dict(db, consent)

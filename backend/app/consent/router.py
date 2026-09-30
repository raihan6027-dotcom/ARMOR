from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schema.common import ConsentStatus
from app.schema.consent import (
    ConsentInboxResponse,
    ConsentRequest,
    ConsentRequestResponse,
    ConsentRequestStatusResponse,
    ConsentRespondRequest,
    ConsentRespondResponse,
    ConsentStatusResponse,
)
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["Consent"])


@router.post("/request", response_model=ConsentRequestResponse)
def request_consent(
    request: ConsentRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Ask for consent on your own REVIEW request. The answer is the same whether or
    not anyone in the media is registered."""
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
    """Consent requests about identities you own."""
    return ConsentInboxResponse(items=consent_service.inbox(db, current.user_id, status))


@router.get("/status/{consent_id}", response_model=ConsentStatusResponse)
def get_consent_status(
    consent_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    consent = consent_service.get_for_owner(db, consent_id, current.user_id)
    return ConsentStatusResponse(
        consent_id=consent.consent_id,
        identity_id=consent.identity_id,
        status=ConsentStatus(consent.status),
        request_id=consent.request_id,
        intent=consent.intent,
        media=consent.media,
    )


@router.post("/respond", response_model=ConsentRespondResponse)
def respond_consent(
    request: ConsentRespondRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    consent = consent_service.respond(db, request.consent_id, request.decision, current.user_id)
    return ConsentRespondResponse(
        consent_id=consent.consent_id,
        status=ConsentStatus(consent.status),
    )

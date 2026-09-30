from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schema.common import ConsentStatus
from app.schema.consent import (
    ConsentRequest,
    ConsentRequestResponse,
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
    # requester_id always comes from the token; a body value is ignored.
    consent = consent_service.create_request(
        db,
        identity_id=request.identity_id,
        requester_id=current.user_id,
        intent=request.intent.value if request.intent else None,
        request_id=request.request_id,
        media=request.media.value if request.media else None,
    )
    return ConsentRequestResponse(
        consent_id=consent.consent_id,
        identity_id=consent.identity_id,
        status=ConsentStatus(consent.status),
    )


@router.get("/status/{consent_id}", response_model=ConsentStatusResponse)
def get_consent_status(
    consent_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    consent = consent_service.get_status(db, consent_id, current.user_id)
    return ConsentStatusResponse(
        consent_id=consent.consent_id,
        identity_id=consent.identity_id,
        status=ConsentStatus(consent.status),
        request_id=consent.request_id,
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

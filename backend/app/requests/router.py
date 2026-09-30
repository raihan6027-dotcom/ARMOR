from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schema.request import (
    RequestCreate,
    RequestDecisionResponse,
    RequestHistoryResponse,
)
from app.services import decision_service
from app.services.identity_service import decode_image

router = APIRouter(prefix="/requests", tags=["Requests"])


@router.post("", response_model=RequestDecisionResponse)
def create_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """The ARMOR AI-safety gateway: full IDENTIFY -> ANALYZE -> DECIDE pipeline."""
    image_bytes = decode_image(payload.image) if payload.image else None
    result = decision_service.orchestrate(
        db,
        requester_user_id=current.user_id,
        identity_id=payload.identity_id,
        prompt=payload.prompt,
        image_bytes=image_bytes,
    )
    return RequestDecisionResponse(**result)


@router.get("", response_model=RequestHistoryResponse)
def list_requests(
    limit: int = Query(50, ge=1, le=200),
    mine: bool = Query(False, description="Only return the current user's requests"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    result = decision_service.history(
        db, requester_user_id=current.user_id if mine else None, limit=limit
    )
    return RequestHistoryResponse(**result)

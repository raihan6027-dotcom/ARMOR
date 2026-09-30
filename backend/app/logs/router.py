from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schema.request import RequestHistoryResponse
from app.services import decision_service

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("", response_model=RequestHistoryResponse)
def get_logs(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """The caller's own decision log (most recent first)."""
    return RequestHistoryResponse(
        **decision_service.history(db, requester_user_id=current.user_id, limit=limit)
    )

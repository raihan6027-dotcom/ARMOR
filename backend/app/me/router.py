"""GET /me/data: everything ARMOR stores about the caller (UU PDP right of access).

Never includes raw embeddings, password hashes, or tokens.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services import data_export_service

router = APIRouter(prefix="/me", tags=["Data saya"])


@router.get("/data")
def export_my_data(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> dict:
    return data_export_service.export(db, current)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schema.permission import (
    PermissionSetRequest,
    PermissionSetResponse,
    PermissionsResponse,
)
from app.services import permission_service

router = APIRouter(prefix="/permissions", tags=["Permission"])


@router.get("", response_model=PermissionsResponse)
def get_permissions(
    identity_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    perms = permission_service.get_permissions(db, identity_id)
    return PermissionsResponse(identity_id=identity_id, permissions=perms)


@router.post("", response_model=PermissionSetResponse)
def set_permission(
    request: PermissionSetRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    permission_service.set_permission(
        db, request.identity_id, request.action, request.decision
    )
    return PermissionSetResponse(
        identity_id=request.identity_id,
        action=request.action,
        decision=request.decision,
    )

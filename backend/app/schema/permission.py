from pydantic import BaseModel

from app.schema.common import PermissionDecision


class PermissionSetRequest(BaseModel):
    identity_id: str
    action: str                      # e.g. "commercial_use"
    decision: PermissionDecision     # ALLOW | REVIEW | DENY


class PermissionSetResponse(BaseModel):
    identity_id: str
    action: str
    decision: PermissionDecision
    message: str = "Permission updated successfully"


class PermissionsResponse(BaseModel):
    identity_id: str
    permissions: dict[str, PermissionDecision]

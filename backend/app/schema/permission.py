from pydantic import BaseModel

from app.schema.common import BiometricMedia, Intent, PermissionDecision


class PermissionSetRequest(BaseModel):
    identity_id: str
    intent: Intent
    media: BiometricMedia = BiometricMedia.FACE
    decision: PermissionDecision  # ALLOW | REVIEW | DENY


class PermissionSetResponse(BaseModel):
    identity_id: str
    intent: Intent
    media: BiometricMedia
    decision: PermissionDecision
    message: str = "Permission updated successfully"


class PermissionsResponse(BaseModel):
    identity_id: str
    # {"FACE": {"PERSONAL_CREATION": "ALLOW", ...}, "VOICE": {...}}
    permissions: dict[BiometricMedia, dict[Intent, PermissionDecision]]
    # Purposes fixed at DENY that the owner cannot change (shown with a padlock).
    locked_intents: list[Intent]

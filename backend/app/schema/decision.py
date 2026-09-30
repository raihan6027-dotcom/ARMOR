from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schema.common import (
    ConsentStatus,
    Decision,
    IdentityTarget,
    Intent,
    LockLevel,
    MediaType,
    PermissionDecision,
    RiskLevel,
    TargetSource,
)


class DecisionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: TargetSource = TargetSource.FACE
    target_type: IdentityTarget
    identity_id: Optional[str] = None
    score: Optional[float] = None
    lock_level: LockLevel = LockLevel.NONE
    consent: ConsentStatus = ConsentStatus.NONE
    permission: Optional[PermissionDecision] = None  # None = owner default
    in_trusted_circle: bool = False
    guardian_child: bool = False


class DecisionRequest(BaseModel):
    """Stateless policy evaluation over pre-computed signals (for testing and demos)."""

    model_config = ConfigDict(extra="forbid")

    targets: list[DecisionTarget] = Field(default_factory=list)
    intent: Intent
    risk_level: Optional[RiskLevel] = None
    media_type: MediaType = MediaType.IMAGE
    intent_confidence: Optional[float] = None
    realism: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    unavailable: list[str] = Field(default_factory=list)
    prompt: Optional[str] = None


class TargetDetail(BaseModel):
    source: TargetSource
    target_type: IdentityTarget
    identity_id: Optional[str] = None
    score: Optional[float] = None
    decision: Decision
    reason_code: str
    reason: str


class DecisionResponse(BaseModel):
    decision: Decision
    reason_code: str
    reason: str
    suggestion: Optional[str] = None
    requester_code: str
    requester_message: str
    effective_intent: Intent
    label_required: bool
    per_target_detail: list[TargetDetail]

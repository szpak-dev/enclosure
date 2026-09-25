from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ApprovalDecisionKind(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_id: str
    actor_kind: str
    operation_id: str
    target: str
    payload_digest: str


class ApprovalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    expires_at: datetime


class ApprovalView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    actor_id: str
    actor_kind: str
    operation_id: str
    target: str
    payload_digest: str
    correlation_id: str
    requested_at: datetime
    expires_at: datetime
    state: str

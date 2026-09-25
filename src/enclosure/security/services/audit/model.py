from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class AuditPhase(StrEnum):
    AUTHORIZATION = "authorization"
    EXECUTION = "execution"
    APPROVAL = "approval"


class ExecutionOutcome(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class AuditEventView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    execution_id: str
    actor_id: str
    actor_kind: str
    operation_id: str
    target: str
    payload_digest: str
    phase: AuditPhase
    decision: str
    outcome: ExecutionOutcome
    reason_code: str
    correlation_id: str
    safe_metadata: dict[str, str]
    occurred_at: datetime


class AuditEventPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[AuditEventView, ...]
    next_offset: int
    limit: int
    has_more: bool

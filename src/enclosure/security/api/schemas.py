from datetime import datetime

from ninja import Field, Schema


class ApprovalRequest(Schema):
    id: str = Field(..., description="Approval request identifier.")
    actor_id: str = Field(..., description="Identifier of the actor requesting execution.")
    actor_kind: str = Field(..., description="Kind of actor requesting execution.")
    operation_id: str = Field(..., description="Stable method and route operation identity.")
    target: str = Field(..., description="Exact resource target covered by the request.")
    payload_digest: str = Field(..., description="SHA-256 digest of the exact request payload.")
    correlation_id: str = Field(..., description="Correlation identifier assigned to the request.")
    requested_at: datetime = Field(..., description="Time at which approval was requested.")
    expires_at: datetime = Field(..., description="Time after which approval cannot be consumed.")
    state: str = Field(..., description="Current pending, approved, or rejected state.")


class AuditEvent(Schema):
    id: str = Field(..., description="Immutable audit-event identifier.")
    execution_id: str = Field(..., description="Identifier shared by authorization and execution events.")
    actor_id: str = Field(..., description="Identifier of the actor invoking the operation.")
    actor_kind: str = Field(..., description="Kind of actor invoking the operation.")
    operation_id: str = Field(..., description="Stable method and route operation identity.")
    target: str = Field(..., description="Exact resource target of the operation.")
    payload_digest: str = Field(..., description="SHA-256 digest of the request payload.")
    phase: str = Field(..., description="Authorization, execution, or approval audit phase.")
    decision: str = Field(..., description="Authorization decision recorded for the operation.")
    outcome: str = Field(..., description="Execution outcome recorded for the operation.")
    reason_code: str = Field(..., description="Stable machine-readable reason for the event.")
    correlation_id: str = Field(..., description="Correlation identifier assigned to the operation.")
    safe_metadata: dict[str, str] = Field(..., description="Redacted non-secret diagnostic metadata.")
    occurred_at: datetime = Field(..., description="Time at which the event occurred.")


class AuditEventPage(Schema):
    items: tuple[AuditEvent, ...] = Field(..., description="Audit events in this page.")
    next_offset: int = Field(..., description="Offset of the next page.")
    limit: int = Field(..., description="Maximum audit events requested for this page.")
    has_more: bool = Field(..., description="Whether another page of audit events exists.")


class FindAuditEvents(Schema):
    offset: int = Field(0, ge=0, description="Zero-based audit-event offset.")
    limit: int = Field(25, ge=1, le=100, description="Maximum audit events returned by the page.")

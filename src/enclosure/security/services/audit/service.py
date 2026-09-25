from dataclasses import dataclass

from django.utils import timezone
from wireup import injectable

from ...models import AuditEvent
from ..actors import Actor
from ..enforcement.model import AuthorizationDecision
from ..policies import OperationIntent
from .model import AuditEventPage, AuditEventView, AuditPhase, ExecutionOutcome
from .repository import AuditRepository


@injectable
@dataclass(frozen=True)
class AuditService:
    repository: AuditRepository

    def authorization(self, actor: Actor, intent: OperationIntent, decision: AuthorizationDecision) -> None:
        self.append(
            actor=actor,
            intent=intent,
            phase=AuditPhase.AUTHORIZATION,
            decision=decision.kind.value,
            outcome=ExecutionOutcome.NOT_APPLICABLE,
            reason_code=decision.reason_code,
        )

    def execution(self, actor: Actor, intent: OperationIntent, outcome: ExecutionOutcome) -> None:
        self.append(
            actor=actor,
            intent=intent,
            phase=AuditPhase.EXECUTION,
            decision="authorized",
            outcome=outcome,
            reason_code=f"execution_{outcome.value}",
        )

    def append(
        self,
        actor: Actor,
        intent: OperationIntent,
        phase: AuditPhase,
        decision: str,
        outcome: ExecutionOutcome,
        reason_code: str,
    ) -> None:
        self.repository.append(
            {
                "execution_id": intent.execution_id,
                "actor_id": actor.id,
                "actor_kind": actor.kind.value,
                "operation_id": intent.operation_id,
                "target": intent.target,
                "payload_digest": intent.payload_digest,
                "phase": phase.value,
                "decision": decision,
                "outcome": outcome.value,
                "reason_code": reason_code,
                "correlation_id": intent.correlation_id,
                "safe_metadata": {"classification": intent.classification.value, "method": intent.method},
                "occurred_at": timezone.now(),
            }
        )

    def find(self, offset: int, limit: int) -> AuditEventPage:
        events = self.repository.find(offset, limit)
        items = events[:limit]
        return AuditEventPage(
            items=tuple(self.view(event) for event in items),
            next_offset=offset + len(items),
            limit=limit,
            has_more=len(events) > limit,
        )

    def view(self, event: AuditEvent) -> AuditEventView:
        return AuditEventView(
            id=event.id,
            execution_id=event.execution_id,
            actor_id=event.actor_id,
            actor_kind=event.actor_kind,
            operation_id=event.operation_id,
            target=event.target,
            payload_digest=event.payload_digest,
            phase=AuditPhase(event.phase),
            decision=event.decision,
            outcome=ExecutionOutcome(event.outcome),
            reason_code=event.reason_code,
            correlation_id=event.correlation_id,
            safe_metadata=event.safe_metadata,
            occurred_at=event.occurred_at,
        )

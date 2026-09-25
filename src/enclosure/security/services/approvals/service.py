from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from wireup import injectable

from ..actors import Actor
from ..enforcement.model import ApprovalRequiredAuthorization, AuthorizationDecision, AuthorizedExecution
from ..policies import OperationIntent
from .model import ApprovalDecisionKind, ApprovalRequirement, ApprovalScope, ApprovalView
from .repository import ApprovalRepository


@injectable
@dataclass(frozen=True)
class ApprovalService:
    repository: ApprovalRepository

    def authorize(self, actor: Actor, intent: OperationIntent) -> AuthorizationDecision:
        now = timezone.now()
        scope = self.scope(actor, intent)
        if self.repository.consume_approved(scope, intent.execution_id, now):
            return AuthorizedExecution(
                execution_id=intent.execution_id,
                reason_code="approval_consumed",
            )
        requirement = self.requirement(intent, scope)
        return ApprovalRequiredAuthorization(
            execution_id=intent.execution_id,
            reason_code="destructive_approval_required",
            approval_request_id=requirement.request_id,
            expires_at=requirement.expires_at,
        )

    def requirement(self, intent: OperationIntent, scope: ApprovalScope) -> ApprovalRequirement:
        now = timezone.now()
        pending = self.repository.pending(scope, now)
        if pending:
            return ApprovalRequirement(request_id=pending[0].id, expires_at=pending[0].expires_at)
        expires_at = now + timedelta(seconds=settings.SECURITY_APPROVAL_TTL_SECONDS)
        request = self.repository.create_request(
            scope=scope,
            correlation_id=intent.correlation_id,
            requested_at=now,
            expires_at=expires_at,
        )
        return ApprovalRequirement(request_id=request.id, expires_at=request.expires_at)

    def approve(self, request_id: str, actor: Actor) -> ApprovalView:
        return self.resolve(request_id, actor, ApprovalDecisionKind.APPROVED)

    def reject(self, request_id: str, actor: Actor) -> ApprovalView:
        return self.resolve(request_id, actor, ApprovalDecisionKind.REJECTED)

    def resolve(self, request_id: str, actor: Actor, decision: ApprovalDecisionKind) -> ApprovalView:
        now = timezone.now()
        self.repository.resolve(request_id, decision, actor.id, now)
        return self.view(request_id)

    def get(self, request_id: str) -> ApprovalView:
        return self.view(request_id)

    def view(self, request_id: str) -> ApprovalView:
        request = self.repository.get(request_id)
        return ApprovalView(
            id=request.id,
            actor_id=request.actor_id,
            actor_kind=request.actor_kind,
            operation_id=request.operation_id,
            target=request.target,
            payload_digest=request.payload_digest,
            correlation_id=request.correlation_id,
            requested_at=request.requested_at,
            expires_at=request.expires_at,
            state=self.repository.state(request_id),
        )

    def scope(self, actor: Actor, intent: OperationIntent) -> ApprovalScope:
        return ApprovalScope(
            actor_id=actor.id,
            actor_kind=actor.kind.value,
            operation_id=intent.operation_id,
            target=intent.target,
            payload_digest=intent.payload_digest,
        )

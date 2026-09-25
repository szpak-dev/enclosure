from dataclasses import dataclass
from uuid import uuid7

from wireup import injectable

from ..actors import Actor
from ..approvals.service import ApprovalService
from ..policies.model import OperationClassification, OperationIntent, OperationPolicy
from ..policies.service import PolicyService
from .model import AuthorizationDecision, AuthorizationDecisionKind
from .sanitization import SafeMetadataRedactor


@injectable
@dataclass(frozen=True)
class OperationIntentFactory:
    redactor: SafeMetadataRedactor

    def create(
        self,
        policy: OperationPolicy,
        target: str,
        payload: bytes,
        correlation_id: str,
    ) -> OperationIntent:
        return OperationIntent(
            execution_id=str(uuid7()),
            operation_id=policy.operation_id,
            classification=policy.classification,
            method=policy.method,
            route=policy.route,
            target=target,
            payload_digest=self.redactor.digest(payload),
            correlation_id=correlation_id,
            required_permission=policy.required_permission,
        )


@injectable
@dataclass(frozen=True)
class EnforcementService:
    policies: PolicyService
    approvals: ApprovalService

    def authorize(self, actor: Actor, intent: OperationIntent) -> AuthorizationDecision:
        decision = self.policies.evaluate(actor, intent)
        if decision.kind == AuthorizationDecisionKind.DENIED:
            return decision
        if intent.classification == OperationClassification.DESTRUCTIVE:
            return self.approvals.authorize(actor, intent)
        return decision

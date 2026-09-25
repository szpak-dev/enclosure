from dataclasses import dataclass

from wireup import injectable

from ..actors import Actor
from ..approvals.service import ApprovalService
from ..policies.model import OperationClassification, OperationIntent
from ..policies.service import PolicyService
from .model import AuthorizationDecision, AuthorizationDecisionKind


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

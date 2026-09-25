from dataclasses import dataclass

from wireup import injectable

from .actors import Actor
from .approvals import ApprovalView
from .approvals.service import ApprovalService
from .audit.model import AuditEventPage, ExecutionOutcome
from .audit.service import AuditService
from .enforcement import AuthorizationDecision
from .enforcement.service import EnforcementService
from .policies import OperationIntent


@injectable
@dataclass(frozen=True)
class SecurityService:
    enforcement: EnforcementService
    approvals: ApprovalService
    audit: AuditService

    def authorize(self, actor: Actor, intent: OperationIntent) -> AuthorizationDecision:
        decision = self.enforcement.authorize(actor, intent)
        self.audit.authorization(actor, intent, decision)
        return decision

    def record_outcome(self, actor: Actor, intent: OperationIntent, outcome: ExecutionOutcome) -> None:
        self.audit.execution(actor, intent, outcome)

    def get_approval(self, request_id: str) -> ApprovalView:
        return self.approvals.get(request_id)

    def approve(self, request_id: str, actor: Actor) -> ApprovalView:
        return self.approvals.approve(request_id, actor)

    def reject(self, request_id: str, actor: Actor) -> ApprovalView:
        return self.approvals.reject(request_id, actor)

    def find_audit_events(self, offset: int, limit: int) -> AuditEventPage:
        return self.audit.find(offset, limit)

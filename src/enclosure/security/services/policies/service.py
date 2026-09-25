from dataclasses import dataclass

from wireup import injectable

from ..actors import Actor
from ..enforcement.model import AuthorizationDecision, AuthorizedExecution, DeniedAuthorization
from .model import OperationIntent


@injectable
@dataclass(frozen=True)
class PolicyService:
    def evaluate(self, actor: Actor, intent: OperationIntent) -> AuthorizationDecision:
        if "*" in actor.permissions or intent.required_permission in actor.permissions:
            return AuthorizedExecution(execution_id=intent.execution_id, reason_code="permission_granted")
        return DeniedAuthorization(execution_id=intent.execution_id, reason_code="permission_missing")

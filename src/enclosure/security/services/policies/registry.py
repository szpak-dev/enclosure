from dataclasses import dataclass

from wireup import injectable

from ...errors import UnmappedOperationError
from .model import OperationClassification, OperationPolicy


@injectable
@dataclass(frozen=True)
class OperationPolicyRegistry:
    def policy(
        self,
        method: str,
        route: str,
        classification: OperationClassification,
    ) -> OperationPolicy:
        return OperationPolicy(
            method=method,
            route=route,
            operation_id=f"{method} {route}",
            classification=classification,
            required_permission=self.required_permission(classification),
        )

    def classification(self, method: str) -> OperationClassification:
        if method == "GET":
            return OperationClassification.READ
        if method == "DELETE":
            return OperationClassification.DESTRUCTIVE
        if method in {"POST", "PUT", "PATCH"}:
            return OperationClassification.MUTATION
        raise UnmappedOperationError(method, "unsupported-method")

    def required_permission(self, classification: OperationClassification) -> str:
        if classification == OperationClassification.APPROVAL:
            return "security.approve_operation"
        if classification == OperationClassification.AUDIT:
            return "security.view_audit_event"
        return f"security.invoke_{classification.value}"

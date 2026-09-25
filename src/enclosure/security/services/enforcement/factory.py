from dataclasses import dataclass
from uuid import uuid7

from wireup import injectable

from ..policies.model import OperationIntent, OperationPolicy
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

from abc import ABC, abstractmethod
from datetime import datetime

from ...models import ApprovalRequest, ApprovalResolution
from .model import ApprovalDecisionKind, ApprovalScope


class ApprovalRepository(ABC):
    @abstractmethod
    def get(self, request_id: str) -> ApprovalRequest:
        raise NotImplementedError

    @abstractmethod
    def pending(self, scope: ApprovalScope, now: datetime) -> tuple[ApprovalRequest, ...]:
        raise NotImplementedError

    @abstractmethod
    def create_request(
        self,
        scope: ApprovalScope,
        correlation_id: str,
        requested_at: datetime,
        expires_at: datetime,
    ) -> ApprovalRequest:
        raise NotImplementedError

    @abstractmethod
    def state(self, request_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def resolve(
        self,
        request_id: str,
        decision: ApprovalDecisionKind,
        decider_actor_id: str,
        decided_at: datetime,
    ) -> ApprovalResolution:
        raise NotImplementedError

    @abstractmethod
    def consume_approved(self, scope: ApprovalScope, execution_id: str, now: datetime) -> bool:
        raise NotImplementedError

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.db.models import QuerySet
from wireup import injectable

from ...errors import ApprovalResolutionError
from ...models import ApprovalConsumption, ApprovalRequest, ApprovalResolution
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


@injectable(as_type=ApprovalRepository)
@dataclass(frozen=True)
class DjangoApprovalRepository(ApprovalRepository):
    def get(self, request_id: str) -> ApprovalRequest:
        return ApprovalRequest.objects.get(pk=request_id)

    def pending(self, scope: ApprovalScope, now: datetime) -> tuple[ApprovalRequest, ...]:
        return tuple(
            ApprovalRequest.objects.filter(
                actor_id=scope.actor_id,
                actor_kind=scope.actor_kind,
                operation_id=scope.operation_id,
                target=scope.target,
                payload_digest=scope.payload_digest,
                expires_at__gt=now,
                resolution__isnull=True,
            ).order_by("requested_at")[:1]
        )

    def create_request(
        self,
        scope: ApprovalScope,
        correlation_id: str,
        requested_at: datetime,
        expires_at: datetime,
    ) -> ApprovalRequest:
        return ApprovalRequest.objects.create(
            actor_id=scope.actor_id,
            actor_kind=scope.actor_kind,
            operation_id=scope.operation_id,
            target=scope.target,
            payload_digest=scope.payload_digest,
            correlation_id=correlation_id,
            requested_at=requested_at,
            expires_at=expires_at,
        )

    def state(self, request_id: str) -> str:
        resolutions = tuple(ApprovalResolution.objects.filter(request_id=request_id).values_list("decision", flat=True))
        return "pending" if not resolutions else resolutions[0]

    @transaction.atomic
    def resolve(
        self,
        request_id: str,
        decision: ApprovalDecisionKind,
        decider_actor_id: str,
        decided_at: datetime,
    ) -> ApprovalResolution:
        requests = tuple(
            ApprovalRequest.objects.select_for_update(of=("self",)).filter(
                pk=request_id,
                expires_at__gt=decided_at,
                resolution__isnull=True,
            )[:1]
        )
        if not requests:
            raise ApprovalResolutionError("The approval request is expired or already resolved.")
        return ApprovalResolution.objects.create(
            request=requests[0],
            decision=decision.value,
            decider_actor_id=decider_actor_id,
            decided_at=decided_at,
        )

    @transaction.atomic
    def consume_approved(self, scope: ApprovalScope, execution_id: str, now: datetime) -> bool:
        resolutions: QuerySet[ApprovalResolution] = (
            ApprovalResolution.objects.select_for_update(of=("self",))
            .filter(
                request__actor_id=scope.actor_id,
                request__actor_kind=scope.actor_kind,
                request__operation_id=scope.operation_id,
                request__target=scope.target,
                request__payload_digest=scope.payload_digest,
                request__expires_at__gt=now,
                decision=ApprovalDecisionKind.APPROVED.value,
                consumption__isnull=True,
            )
            .order_by("decided_at")
        )
        approved = tuple(resolutions[:1])
        if not approved:
            return False
        ApprovalConsumption.objects.create(
            resolution=approved[0],
            execution_id=execution_id,
            consumed_at=now,
        )
        return True

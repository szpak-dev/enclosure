from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from wireup import injectable

from ...models import AuditEvent


class AuditRepository(ABC):
    @abstractmethod
    def append(self, values: dict[str, str | datetime | dict[str, str]]) -> AuditEvent:
        raise NotImplementedError

    @abstractmethod
    def find(self, offset: int, limit: int) -> tuple[AuditEvent, ...]:
        raise NotImplementedError


@injectable(as_type=AuditRepository)
@dataclass(frozen=True)
class DjangoAuditRepository(AuditRepository):
    def append(self, values: dict[str, str | datetime | dict[str, str]]) -> AuditEvent:
        return AuditEvent.objects.create(**values)

    def find(self, offset: int, limit: int) -> tuple[AuditEvent, ...]:
        return tuple(AuditEvent.objects.order_by("-occurred_at", "-id")[offset : offset + limit + 1])

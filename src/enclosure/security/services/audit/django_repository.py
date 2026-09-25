from dataclasses import dataclass
from datetime import datetime

from wireup import injectable

from ...models import AuditEvent
from .repository import AuditRepository


@injectable(as_type=AuditRepository)
@dataclass(frozen=True)
class DjangoAuditRepository(AuditRepository):
    def append(self, values: dict[str, str | datetime | dict[str, str]]) -> AuditEvent:
        return AuditEvent.objects.create(**values)

    def find(self, offset: int, limit: int) -> tuple[AuditEvent, ...]:
        return tuple(AuditEvent.objects.order_by("-occurred_at", "-id")[offset : offset + limit + 1])

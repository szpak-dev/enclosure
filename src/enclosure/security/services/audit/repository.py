from abc import ABC, abstractmethod
from datetime import datetime

from ...models import AuditEvent


class AuditRepository(ABC):
    @abstractmethod
    def append(self, values: dict[str, str | datetime | dict[str, str]]) -> AuditEvent:
        raise NotImplementedError

    @abstractmethod
    def find(self, offset: int, limit: int) -> tuple[AuditEvent, ...]:
        raise NotImplementedError

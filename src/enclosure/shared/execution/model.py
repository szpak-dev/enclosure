from contextvars import Token
from dataclasses import dataclass, field
from threading import Event


@dataclass(frozen=True)
class CancellationSignal:
    event: Event = field(default_factory=Event)

    @property
    def cancelled(self) -> bool:
        return self.event.is_set()

    def cancel(self) -> None:
        self.event.set()


@dataclass(frozen=True)
class CancellationToken:
    value: Token[CancellationSignal]

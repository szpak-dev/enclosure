from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from .model import CancellationSignal, CancellationToken


@injectable
@dataclass(frozen=True)
class RequestCancellationContext:
    signal: ClassVar[ContextVar[CancellationSignal]] = ContextVar("request_cancellation_signal")
    baseline: CancellationSignal = field(default_factory=CancellationSignal, init=False)

    def bind(self, signal: CancellationSignal) -> CancellationToken:
        return CancellationToken(value=self.signal.set(signal))

    def current(self) -> CancellationSignal:
        return self.signal.get(self.baseline)

    def reset(self, token: CancellationToken) -> None:
        self.signal.reset(token.value)

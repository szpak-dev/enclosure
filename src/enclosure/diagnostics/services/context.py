from contextvars import ContextVar
from dataclasses import dataclass
from typing import ClassVar

from modwire.application import CacheOutcome
from wireup import injectable


@injectable
@dataclass(frozen=True)
class CacheDiagnosticsContext:
    active: ClassVar[ContextVar[bool]] = ContextVar(
        "cache_diagnostics_active",
        default=False,
    )
    outcomes: ClassVar[ContextVar[tuple[CacheOutcome, ...]]] = ContextVar(
        "cache_diagnostics_outcomes",
        default=(),
    )

    def begin(self) -> None:
        self.active.set(True)
        self.outcomes.set(())

    def record(self, outcomes: tuple[CacheOutcome, ...]) -> None:
        if self.active.get():
            self.outcomes.set(self.outcomes.get() + outcomes)

    def read(self) -> tuple[CacheOutcome, ...]:
        return self.outcomes.get()

    def reset(self) -> None:
        self.active.set(False)
        self.outcomes.set(())

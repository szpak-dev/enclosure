from contextvars import ContextVar, Token
from dataclasses import dataclass, field

from modwire.application import CacheOutcome
from wireup import injectable

from .reporter import CacheDiagnosticsReporter


@injectable
@dataclass(frozen=True)
class CacheDiagnosticsContext:
    active: ContextVar[bool] = field(
        default_factory=lambda: ContextVar("cache_diagnostics_active", default=False),
        init=False,
    )
    outcomes: ContextVar[tuple[CacheOutcome, ...]] = field(
        default_factory=lambda: ContextVar("cache_diagnostics_outcomes", default=()),
        init=False,
    )
    reporters: ContextVar[tuple[CacheDiagnosticsReporter, ...]] = field(
        default_factory=lambda: ContextVar("cache_diagnostics_reporters", default=()),
        init=False,
    )

    def begin(self) -> None:
        self.active.set(True)
        self.outcomes.set(())

    def record(self, outcomes: tuple[CacheOutcome, ...]) -> None:
        if self.active.get():
            self.outcomes.set(self.outcomes.get() + outcomes)
            for reporter in self.reporters.get():
                reporter.report_cache_outcomes(outcomes)

    def set_reporter(
        self,
        reporter: CacheDiagnosticsReporter,
    ) -> Token[tuple[CacheDiagnosticsReporter, ...]]:
        return self.reporters.set((reporter,))

    def reset_reporter(
        self,
        token: Token[tuple[CacheDiagnosticsReporter, ...]],
    ) -> None:
        self.reporters.reset(token)

    def read(self) -> tuple[CacheOutcome, ...]:
        return self.outcomes.get()

    def reset(self) -> None:
        self.active.set(False)
        self.outcomes.set(())

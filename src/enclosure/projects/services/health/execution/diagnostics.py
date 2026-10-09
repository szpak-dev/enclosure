from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from time import perf_counter_ns

from wireup import injectable

from .model import CacheOutcomeState, HealthCacheStage, HealthExecutionPhase, HealthPhaseDiagnostic, HealthPhaseToken
from .reporter import HealthPhaseReporter


@injectable
@dataclass(frozen=True)
class HealthPhaseDiagnostics:
    diagnostics: ContextVar[tuple[HealthPhaseDiagnostic, ...]] = field(
        default_factory=lambda: ContextVar("health_phase_diagnostics", default=()),
        init=False,
    )
    reporter: ContextVar[HealthPhaseReporter] = field(
        default_factory=lambda: ContextVar("health_phase_reporter"),
        init=False,
    )

    def begin(self) -> Token[tuple[HealthPhaseDiagnostic, ...]]:
        return self.diagnostics.set(())

    def set_reporter(
        self,
        reporter: HealthPhaseReporter,
    ) -> Token[HealthPhaseReporter]:
        return self.reporter.set(reporter)

    def start(self, phase: HealthExecutionPhase) -> HealthPhaseToken:
        token = HealthPhaseToken(phase=phase, started_ns=perf_counter_ns())
        self.reporter.get().report_phase(token)
        return token

    def finish(
        self,
        token: HealthPhaseToken,
        *,
        outcome: str = "completed",
        item_count: int = 0,
        cache_outcome: CacheOutcomeState = CacheOutcomeState.NOT_APPLICABLE,
        cache_stages: tuple[HealthCacheStage, ...] = (),
    ) -> HealthPhaseDiagnostic:
        diagnostic = HealthPhaseDiagnostic(
            phase=token.phase,
            duration_ns=perf_counter_ns() - token.started_ns,
            outcome=outcome,
            item_count=item_count,
            cache_outcome=cache_outcome,
            cache_stages=cache_stages,
        )
        self.diagnostics.set((*self.diagnostics.get(), diagnostic))
        self.reporter.get().report_phase(diagnostic)
        return diagnostic

    def read(self) -> tuple[HealthPhaseDiagnostic, ...]:
        return self.diagnostics.get()

    def reset(self, token: Token[tuple[HealthPhaseDiagnostic, ...]]) -> None:
        self.diagnostics.reset(token)

    def reset_reporter(
        self,
        token: Token[HealthPhaseReporter],
    ) -> None:
        self.reporter.reset(token)

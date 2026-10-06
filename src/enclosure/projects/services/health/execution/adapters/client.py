import multiprocessing
import os
import signal
from dataclasses import dataclass, field
from multiprocessing.connection import Connection
from time import monotonic, perf_counter_ns
from typing import cast

from modwire.application import CacheOutcome

from enclosure.shared.execution import CancellationSignal

from ..model import (
    CompletedHealthExecutionResult,
    HealthCacheOutcomeDiagnostic,
    HealthExecutionRequest,
    HealthExecutionResponse,
    HealthPhaseDiagnostic,
    HealthPhaseToken,
    HealthRunOutcome,
    HealthWorkerMessage,
    HealthWorkerReadiness,
    HealthWorkerReady,
    IncompleteHealthExecutionResult,
)


@dataclass(frozen=True)
class HealthWorkerClient:
    process: multiprocessing.Process
    connection: Connection
    poll_seconds: float = field(default=0.05, init=False)
    termination_grace_seconds: float = field(default=1.0, init=False)

    def wait_until_ready(self, timeout_seconds: float) -> HealthWorkerReadiness:
        deadline = monotonic() + timeout_seconds
        while self.process.is_alive():
            remaining = deadline - monotonic()
            if remaining <= 0:
                return HealthWorkerReadiness.TIMED_OUT
            try:
                if not self.connection.poll(min(self.poll_seconds, remaining)):
                    continue
                payload: object = self.connection.recv()
            except (EOFError, OSError):
                return HealthWorkerReadiness.FAILED
            try:
                HealthWorkerReady.model_validate(payload)
            except ValueError:
                return HealthWorkerReadiness.FAILED
            return HealthWorkerReadiness.READY
        return HealthWorkerReadiness.FAILED

    def execute(
        self,
        request: HealthExecutionRequest,
        signal: CancellationSignal,
        timeout_seconds: float,
    ) -> CompletedHealthExecutionResult | IncompleteHealthExecutionResult:
        try:
            self.connection.send(request)
        except (EOFError, OSError):
            return self.failed_result()
        deadline = monotonic() + timeout_seconds
        diagnostics: list[HealthPhaseDiagnostic] = []
        cache_outcomes: list[CacheOutcome] = []
        active_phases: tuple[HealthPhaseToken, ...] = ()
        while True:
            if signal.cancelled:
                return self.terminal_result(
                    HealthRunOutcome.CANCELED,
                    "Project health request was canceled.",
                    tuple(diagnostics),
                    active_phases,
                    tuple(cache_outcomes),
                )
            remaining = deadline - monotonic()
            if remaining <= 0:
                return self.terminal_result(
                    HealthRunOutcome.TIMED_OUT,
                    "Project health execution timed out.",
                    tuple(diagnostics),
                    active_phases,
                    tuple(cache_outcomes),
                )
            try:
                result_available = self.connection.poll(min(self.poll_seconds, remaining))
            except OSError:
                return self.failed_result(tuple(diagnostics), active_phases, tuple(cache_outcomes))
            if result_available:
                try:
                    payload: object = self.connection.recv()
                except (EOFError, OSError):
                    return self.failed_result(tuple(diagnostics), active_phases, tuple(cache_outcomes))
                try:
                    message = HealthWorkerMessage.model_validate({"message": payload}).message
                except ValueError:
                    return self.failed_result(tuple(diagnostics), active_phases, tuple(cache_outcomes))
                if message.kind == "phase-started":
                    active_phases = (cast(HealthPhaseToken, message),)
                    continue
                if message.kind == "phase-diagnostic":
                    diagnostic = cast(HealthPhaseDiagnostic, message)
                    diagnostics.append(diagnostic)
                    active_phases = ()
                    continue
                if message.kind == "cache-outcomes":
                    cache_outcomes.extend(cast(HealthCacheOutcomeDiagnostic, message).outcomes)
                    continue
                response = cast(HealthExecutionResponse, message)
                if not self.process.is_alive():
                    return self.failed_result(tuple(diagnostics), active_phases, tuple(cache_outcomes))
                return response.result.model_copy(update={"phase_diagnostics": tuple(diagnostics)})
            if not self.process.is_alive():
                return self.failed_result(tuple(diagnostics), active_phases, tuple(cache_outcomes))

    def terminate(self) -> None:
        process_id = self.process.pid
        try:
            group_signaled = False
            if self.process.is_alive():
                if process_id is not None:
                    try:
                        os.killpg(process_id, signal.SIGTERM)
                        group_signaled = True
                    except PermissionError:
                        self.process.terminate()
                    except ProcessLookupError:
                        self.process.join(self.termination_grace_seconds)
                if not group_signaled:
                    self.process.terminate()
                self.process.join(self.termination_grace_seconds)
            else:
                self.process.join()
            group_killed = False
            if self.process.is_alive() and process_id is not None and group_signaled:
                try:
                    os.killpg(process_id, signal.SIGKILL)
                    group_killed = True
                except PermissionError:
                    self.process.kill()
                except ProcessLookupError:
                    self.process.join(self.termination_grace_seconds)
            if self.process.is_alive() and not group_killed:
                self.process.kill()
            if self.process.is_alive():
                self.process.join(self.termination_grace_seconds)
        finally:
            self.connection.close()
            if not self.process.is_alive():
                self.process.close()

    def failed_result(
        self,
        diagnostics: tuple[HealthPhaseDiagnostic, ...] = (),
        active_phases: tuple[HealthPhaseToken, ...] = (),
        cache_outcomes: tuple[CacheOutcome, ...] = (),
    ) -> IncompleteHealthExecutionResult:
        return self.terminal_result(
            HealthRunOutcome.FAILED,
            f"Project health worker exited with code {self.process.exitcode}.",
            diagnostics,
            active_phases,
            cache_outcomes,
        )

    def terminal_result(
        self,
        outcome: HealthRunOutcome,
        detail: str,
        diagnostics: tuple[HealthPhaseDiagnostic, ...] = (),
        active_phases: tuple[HealthPhaseToken, ...] = (),
        cache_outcomes: tuple[CacheOutcome, ...] = (),
    ) -> IncompleteHealthExecutionResult:
        retained = list(diagnostics)
        for active_phase in active_phases:
            retained.append(
                HealthPhaseDiagnostic(
                    phase=active_phase.phase,
                    duration_ns=max(0, perf_counter_ns() - active_phase.started_ns),
                    outcome=outcome.value,
                )
            )
        return IncompleteHealthExecutionResult(
            outcome=outcome,
            cache_outcomes=cache_outcomes,
            phase_diagnostics=tuple(retained),
            detail=detail,
        )

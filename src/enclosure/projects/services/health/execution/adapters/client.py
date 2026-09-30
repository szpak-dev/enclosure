import multiprocessing
import os
import signal
from dataclasses import dataclass, field
from multiprocessing.connection import Connection
from time import monotonic

from enclosure.shared.execution import CancellationSignal

from ..model import (
    CompletedHealthExecutionResult,
    HealthExecutionRequest,
    HealthExecutionResponse,
    HealthRunOutcome,
    IncompleteHealthExecutionResult,
)


@dataclass(frozen=True)
class HealthWorkerClient:
    process: multiprocessing.Process
    connection: Connection
    poll_seconds: float = field(default=0.05, init=False)
    termination_grace_seconds: float = field(default=1.0, init=False)

    def execute(
        self,
        request: HealthExecutionRequest,
        signal: CancellationSignal,
        timeout_seconds: int,
    ) -> CompletedHealthExecutionResult | IncompleteHealthExecutionResult:
        try:
            self.connection.send(request)
        except (EOFError, OSError):
            return self.failed_result()
        deadline = monotonic() + timeout_seconds
        while True:
            if signal.cancelled:
                return self.terminal_result(HealthRunOutcome.CANCELED, "Project health request was canceled.")
            remaining = deadline - monotonic()
            if remaining <= 0:
                return self.terminal_result(HealthRunOutcome.TIMED_OUT, "Project health execution timed out.")
            try:
                result_available = self.connection.poll(min(self.poll_seconds, remaining))
            except OSError:
                return self.failed_result()
            if result_available:
                try:
                    payload: object = self.connection.recv()
                except (EOFError, OSError):
                    return self.failed_result()
                if not self.process.is_alive():
                    return self.failed_result()
                return HealthExecutionResponse.model_validate({"result": payload}).result
            if not self.process.is_alive():
                return self.failed_result()

    def terminate(self) -> None:
        process_id = self.process.pid
        try:
            group_signaled = False
            if self.process.is_alive():
                if process_id is not None:
                    try:
                        os.killpg(process_id, signal.SIGTERM)
                        group_signaled = True
                    except (PermissionError, ProcessLookupError):
                        pass
                if not group_signaled:
                    self.process.terminate()
                self.process.join(self.termination_grace_seconds)
            else:
                self.process.join()
            group_killed = False
            if process_id is not None and group_signaled:
                try:
                    os.killpg(process_id, signal.SIGKILL)
                    group_killed = True
                except (PermissionError, ProcessLookupError):
                    pass
            if self.process.is_alive() and not group_killed:
                self.process.kill()
            if self.process.is_alive():
                self.process.join()
        finally:
            self.connection.close()
            if not self.process.is_alive():
                self.process.close()

    def failed_result(self) -> IncompleteHealthExecutionResult:
        return self.terminal_result(
            HealthRunOutcome.FAILED,
            f"Project health worker exited with code {self.process.exitcode}.",
        )

    def terminal_result(self, outcome: HealthRunOutcome, detail: str) -> IncompleteHealthExecutionResult:
        return IncompleteHealthExecutionResult(
            outcome=outcome,
            cache_outcomes=(),
            detail=detail,
        )

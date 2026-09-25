import multiprocessing
from dataclasses import dataclass
from multiprocessing.connection import Connection
from time import monotonic
from typing import ClassVar

from enclosure.shared.execution import CancellationSignal

from ..model import HealthExecutionRequest, HealthExecutionResult, HealthRunOutcome


@dataclass(frozen=True)
class HealthWorkerClient:
    POLL_SECONDS: ClassVar[float] = 0.05
    TERMINATION_GRACE_SECONDS: ClassVar[float] = 1.0

    process: multiprocessing.Process
    connection: Connection

    def execute(
        self,
        request: HealthExecutionRequest,
        signal: CancellationSignal,
        timeout_seconds: int,
    ) -> HealthExecutionResult:
        try:
            self.connection.send(request)
        except (EOFError, OSError):
            return self._failed()
        deadline = monotonic() + timeout_seconds
        while True:
            if signal.cancelled:
                return self._terminal(HealthRunOutcome.CANCELED, "Project health request was canceled.")
            remaining = deadline - monotonic()
            if remaining <= 0:
                return self._terminal(HealthRunOutcome.TIMED_OUT, "Project health execution timed out.")
            try:
                result_available = self.connection.poll(min(self.POLL_SECONDS, remaining))
            except OSError:
                return self._failed()
            if result_available:
                try:
                    result = self.connection.recv()
                except (EOFError, OSError):
                    return self._failed()
                if not self.process.is_alive():
                    return self._failed()
                return result
            if not self.process.is_alive():
                return self._failed()

    def terminate(self) -> None:
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(self.TERMINATION_GRACE_SECONDS)
        else:
            self.process.join()
        if self.process.is_alive():
            self.process.kill()
            self.process.join()
        self.connection.close()
        self.process.close()

    def _failed(self) -> HealthExecutionResult:
        return self._terminal(
            HealthRunOutcome.FAILED,
            f"Project health worker exited with code {self.process.exitcode}.",
        )

    def _terminal(self, outcome: HealthRunOutcome, detail: str) -> HealthExecutionResult:
        return HealthExecutionResult(
            outcome=outcome,
            reports=(),
            cache_outcomes=(),
            detail=detail,
        )

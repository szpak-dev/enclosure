import fcntl
import multiprocessing
from dataclasses import dataclass
from multiprocessing.connection import Connection
from pathlib import Path
from time import monotonic
from typing import BinaryIO, ClassVar

from django.conf import settings
from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext
from enclosure.shared.execution import CancellationSignal

from .....errors import ProjectHealthCapacityUnavailable
from ....reports.adapters import ArchitectureAdapter
from ....reports.model import ArchitectureSource
from ....reports.paging import InsightPagingService
from ....reports.service import ReportsService
from ..gateway import HealthWorkerGateway
from ..model import HealthExecutionResult, HealthRunOutcome


@dataclass(frozen=True)
class HealthSlotLease:
    handle: BinaryIO

    def release(self) -> None:
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


@dataclass(frozen=True)
class HealthWorkerProcess:
    source: ArchitectureSource
    connection: Connection

    def run(self) -> None:
        cache = CacheDiagnosticsContext()
        reports = ReportsService(
            architecture=ArchitectureAdapter(cache_diagnostics=cache),
            paging=InsightPagingService(),
        )
        cache.begin()
        try:
            report = reports.generate_health_report(self.source)
            self.connection.send(
                HealthExecutionResult(
                    outcome=HealthRunOutcome.COMPLETED,
                    reports=report.reports,
                    cache_outcomes=cache.read(),
                    detail="",
                )
            )
        finally:
            cache.reset()
            self.connection.close()


@injectable(as_type=HealthWorkerGateway)
@dataclass(frozen=True)
class ProcessHealthWorker(HealthWorkerGateway):
    POLL_SECONDS: ClassVar[float] = 0.05
    TERMINATION_GRACE_SECONDS: ClassVar[float] = 1.0

    @property
    def max_concurrency(self) -> int:
        return settings.PROJECT_HEALTH_MAX_CONCURRENCY

    @property
    def timeout_seconds(self) -> int:
        return settings.PROJECT_HEALTH_TIMEOUT_SECONDS

    def execute(
        self,
        source: ArchitectureSource,
        signal: CancellationSignal,
        timeout_seconds: int,
    ) -> HealthExecutionResult:
        lease = self._acquire()
        try:
            process_context = multiprocessing.get_context("spawn")
            receiver, sender = process_context.Pipe(duplex=False)
            process = process_context.Process(
                target=HealthWorkerProcess(source=source, connection=sender).run,
                daemon=True,
            )
            process.start()
            return self._supervise(process, receiver, sender, signal, timeout_seconds)
        finally:
            lease.release()

    def _supervise(
        self,
        process: multiprocessing.Process,
        receiver: Connection,
        sender: Connection,
        signal: CancellationSignal,
        timeout_seconds: int,
    ) -> HealthExecutionResult:
        sender.close()
        deadline = monotonic() + timeout_seconds
        try:
            while True:
                if signal.cancelled:
                    self._terminate(process)
                    return self._terminal(HealthRunOutcome.CANCELED, "Project health request was canceled.")
                remaining = deadline - monotonic()
                if remaining <= 0:
                    self._terminate(process)
                    return self._terminal(HealthRunOutcome.TIMED_OUT, "Project health execution timed out.")
                if receiver.poll(min(self.POLL_SECONDS, remaining)):
                    try:
                        result = receiver.recv()
                    except EOFError:
                        process.join()
                        return self._failed(process)
                    process.join(max(0.0, deadline - monotonic()))
                    if process.is_alive():
                        self._terminate(process)
                        return self._terminal(HealthRunOutcome.TIMED_OUT, "Project health execution timed out.")
                    if process.exitcode != 0:
                        return self._failed(process)
                    return result
                if not process.is_alive():
                    process.join()
                    return self._failed(process)
        finally:
            if process.is_alive():
                self._terminate(process)
            receiver.close()
            process.close()

    def _acquire(self) -> HealthSlotLease:
        directory = self._capacity_path()
        for index in range(self.max_concurrency):
            handle = (directory / f"slot-{index}.lock").open("a+b")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
            else:
                return HealthSlotLease(handle=handle)
        raise ProjectHealthCapacityUnavailable("Project health execution capacity is exhausted.")

    def _capacity_path(self) -> Path:
        directory = Path(settings.MODWIRE_CACHE_DIRECTORY) / "health-capacity"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _terminate(self, process: multiprocessing.Process) -> None:
        process.terminate()
        process.join(self.TERMINATION_GRACE_SECONDS)
        if process.is_alive():
            process.kill()
            process.join()

    def _failed(self, process: multiprocessing.Process) -> HealthExecutionResult:
        return self._terminal(
            HealthRunOutcome.FAILED,
            f"Project health worker exited with code {process.exitcode}.",
        )

    def _terminal(self, outcome: HealthRunOutcome, detail: str) -> HealthExecutionResult:
        return HealthExecutionResult(
            outcome=outcome,
            reports=(),
            cache_outcomes=(),
            detail=detail,
        )

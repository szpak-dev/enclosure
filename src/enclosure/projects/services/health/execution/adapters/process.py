import fcntl
import multiprocessing
from dataclasses import dataclass, field
from multiprocessing.connection import Connection
from pathlib import Path
from threading import Lock
from time import monotonic, perf_counter_ns
from typing import BinaryIO, ClassVar

import structlog
from django.conf import settings
from django.db import connections
from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext
from enclosure.shared.execution import CancellationSignal

from .....errors import ProjectHealthCapacityUnavailable
from ....reports.adapters import ArchitectureAdapter
from ....reports.paging import InsightPagingService
from ....reports.service import ReportsService
from ..gateway import HealthWorkerGateway
from ..model import HealthExecutionRequest, HealthExecutionResult, HealthRunOutcome


@dataclass(frozen=True)
class HealthSlotLease:
    slot_index: int
    handle: BinaryIO

    def release(self) -> None:
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


@dataclass(frozen=True)
class HealthWorkerProcess:
    logger: ClassVar = structlog.get_logger(__name__)

    connection: Connection

    def run(self) -> None:
        connections.close_all()
        try:
            while True:
                try:
                    request = self.connection.recv()
                except (EOFError, OSError):
                    return
                self._execute(request)
                del request
        finally:
            self.connection.close()
            connections.close_all()

    def _execute(self, request: HealthExecutionRequest) -> None:
        started_ns = perf_counter_ns()
        outcome = HealthRunOutcome.FAILED
        self.logger.info(
            "project_health_architecture_started",
            run_id=request.run_id,
            started_ns=started_ns,
            project_id=request.source.project_id,
            workspace_id=request.source.workspace_id,
        )
        cache = CacheDiagnosticsContext()
        reports = ReportsService(
            architecture=ArchitectureAdapter(cache_diagnostics=cache),
            paging=InsightPagingService(),
        )
        cache.begin()
        try:
            report = reports.generate_health_report(request.source)
            self.connection.send(
                HealthExecutionResult(
                    outcome=HealthRunOutcome.COMPLETED,
                    reports=report.reports,
                    cache_outcomes=cache.read(),
                    detail="",
                )
            )
            outcome = HealthRunOutcome.COMPLETED
        finally:
            cache.reset()
            connections.close_all()
            finished_ns = perf_counter_ns()
            self.logger.info(
                "project_health_architecture_terminal",
                run_id=request.run_id,
                outcome=outcome.value,
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
                project_id=request.source.project_id,
                workspace_id=request.source.workspace_id,
            )


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


@injectable
@dataclass
class HealthWorkerRegistry:
    logger: ClassVar = structlog.get_logger(__name__)

    guard: Lock = field(default_factory=Lock, init=False)
    workers: dict[int, HealthWorkerClient] = field(default_factory=dict, init=False)
    replacement_slots: set[int] = field(default_factory=set, init=False)

    def get_or_start(self, slot_index: int, run_id: str) -> HealthWorkerClient:
        with self.guard:
            replacement = slot_index in self.workers or slot_index in self.replacement_slots
            if slot_index in self.workers:
                worker = self.workers[slot_index]
                if worker.process.is_alive():
                    self.logger.info(
                        "project_health_worker_reused",
                        run_id=run_id,
                        slot_index=slot_index,
                        worker_process_id=worker.process.pid,
                    )
                    return worker
                del self.workers[slot_index]
                worker.terminate()
            started_ns = perf_counter_ns()
            process_context = multiprocessing.get_context("spawn")
            parent, child = process_context.Pipe(duplex=True)
            process = process_context.Process(
                target=HealthWorkerProcess(connection=child).run,
                daemon=True,
            )
            process.start()
            child.close()
            worker = HealthWorkerClient(process=process, connection=parent)
            self.workers[slot_index] = worker
            self.replacement_slots.discard(slot_index)
            finished_ns = perf_counter_ns()
            self.logger.info(
                "project_health_worker_started",
                run_id=run_id,
                replacement=replacement,
                slot_index=slot_index,
                worker_process_id=process.pid,
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
            )
            return worker

    def discard(self, slot_index: int, worker: HealthWorkerClient) -> None:
        with self.guard:
            if slot_index not in self.workers or self.workers[slot_index] is not worker:
                return
            del self.workers[slot_index]
            self.replacement_slots.add(slot_index)
        worker.terminate()


@injectable(as_type=HealthWorkerGateway)
@dataclass(frozen=True)
class ProcessHealthWorker(HealthWorkerGateway):
    logger: ClassVar = structlog.get_logger(__name__)

    registry: HealthWorkerRegistry

    @property
    def max_concurrency(self) -> int:
        return settings.PROJECT_HEALTH_MAX_CONCURRENCY

    @property
    def timeout_seconds(self) -> int:
        return settings.PROJECT_HEALTH_TIMEOUT_SECONDS

    def execute(
        self,
        request: HealthExecutionRequest,
        signal: CancellationSignal,
        timeout_seconds: int,
    ) -> HealthExecutionResult:
        acquisition_started_ns = perf_counter_ns()
        try:
            lease = self._acquire()
        except ProjectHealthCapacityUnavailable:
            acquisition_finished_ns = perf_counter_ns()
            self.logger.info(
                "project_health_capacity_unavailable",
                run_id=request.run_id,
                max_concurrency=self.max_concurrency,
                started_ns=acquisition_started_ns,
                finished_ns=acquisition_finished_ns,
                duration_ns=acquisition_finished_ns - acquisition_started_ns,
            )
            raise
        acquisition_finished_ns = perf_counter_ns()
        self.logger.info(
            "project_health_capacity_acquired",
            run_id=request.run_id,
            slot_index=lease.slot_index,
            max_concurrency=self.max_concurrency,
            started_ns=acquisition_started_ns,
            finished_ns=acquisition_finished_ns,
            duration_ns=acquisition_finished_ns - acquisition_started_ns,
        )
        try:
            worker = self.registry.get_or_start(lease.slot_index, request.run_id)
            result = worker.execute(request, signal, timeout_seconds)
            if result.outcome != HealthRunOutcome.COMPLETED:
                self.registry.discard(lease.slot_index, worker)
                self.logger.info(
                    "project_health_worker_discarded",
                    run_id=request.run_id,
                    slot_index=lease.slot_index,
                    outcome=result.outcome.value,
                )
            return result
        finally:
            lease.release()

    def _acquire(self) -> HealthSlotLease:
        directory = self._capacity_path()
        for index in range(self.max_concurrency):
            handle = (directory / f"slot-{index}.lock").open("a+b")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
            else:
                return HealthSlotLease(slot_index=index, handle=handle)
        raise ProjectHealthCapacityUnavailable("Project health execution capacity is exhausted.")

    def _capacity_path(self) -> Path:
        directory = Path(settings.MODWIRE_CACHE_DIRECTORY) / "health-capacity"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

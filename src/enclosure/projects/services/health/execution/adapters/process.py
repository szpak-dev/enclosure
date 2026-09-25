import fcntl
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import ClassVar

import structlog
from django.conf import settings
from wireup import injectable

from enclosure.shared.execution import CancellationSignal

from .....errors import ProjectHealthCapacityUnavailable
from ..gateway import HealthWorkerGateway
from ..model import HealthExecutionRequest, HealthExecutionResult, HealthRunOutcome
from .lease import HealthSlotLease
from .registry import HealthWorkerRegistry


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

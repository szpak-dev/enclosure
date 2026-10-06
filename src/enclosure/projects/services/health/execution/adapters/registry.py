import multiprocessing
from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter_ns
from typing import ClassVar

import structlog
from django.conf import settings
from wireup import injectable

from .....errors import ProjectHealthExecutionFailed, ProjectHealthTimedOut
from ..model import HealthWorkerReadiness
from .client import HealthWorkerClient
from .worker import HealthWorkerProcess


@injectable
@dataclass
class HealthWorkerRegistry:
    logger: ClassVar = structlog.get_logger(__name__)

    guard: Lock = field(default_factory=Lock, init=False)
    workers: dict[int, HealthWorkerClient] = field(default_factory=dict, init=False)
    replacement_slots: set[int] = field(default_factory=set, init=False)

    def get_or_start(self, slot_index: int, run_id: str, timeout_seconds: float) -> HealthWorkerClient:
        stale_workers: tuple[HealthWorkerClient, ...] = ()
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
                stale_workers = (worker,)
            self.replacement_slots.add(slot_index)
        for stale_worker in stale_workers:
            stale_worker.terminate()
        started_ns = perf_counter_ns()
        process_context = multiprocessing.get_context("spawn")
        parent, child = process_context.Pipe(duplex=True)
        process = process_context.Process(
            target=HealthWorkerProcess(connection=child).run,
            daemon=True,
        )
        try:
            process.start()
        except (OSError, RuntimeError) as error:
            parent.close()
            child.close()
            finished_ns = perf_counter_ns()
            self.logger.info(
                "project_health_worker_bootstrap_terminal",
                run_id=run_id,
                phase="worker-bootstrap",
                outcome="failed",
                slot_index=slot_index,
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
            )
            raise ProjectHealthExecutionFailed("Project health worker could not start.") from error
        child.close()
        worker_process_id = process.pid
        worker = HealthWorkerClient(process=process, connection=parent)
        bootstrap_outcome = "failed"
        try:
            readiness = worker.wait_until_ready(
                min(float(settings.PROJECT_HEALTH_WORKER_READY_TIMEOUT_SECONDS), timeout_seconds)
            )
            if readiness != HealthWorkerReadiness.READY:
                worker.terminate()
                if readiness == HealthWorkerReadiness.TIMED_OUT:
                    bootstrap_outcome = HealthWorkerReadiness.TIMED_OUT.value
                    raise ProjectHealthTimedOut("Project health execution timed out.")
                raise ProjectHealthExecutionFailed("Project health worker did not become ready in time.")
            bootstrap_outcome = "completed"
        finally:
            finished_ns = perf_counter_ns()
            self.logger.info(
                "project_health_worker_bootstrap_terminal",
                run_id=run_id,
                phase="worker-bootstrap",
                outcome=bootstrap_outcome,
                replacement=replacement,
                slot_index=slot_index,
                worker_process_id=worker_process_id,
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
            )
        with self.guard:
            self.workers[slot_index] = worker
            self.replacement_slots.discard(slot_index)
        return worker

    def discard(self, slot_index: int, worker: HealthWorkerClient) -> None:
        with self.guard:
            if slot_index not in self.workers or self.workers[slot_index] is not worker:
                return
            del self.workers[slot_index]
            self.replacement_slots.add(slot_index)
        worker.terminate()

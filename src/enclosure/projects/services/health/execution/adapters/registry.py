import multiprocessing
from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter_ns
from typing import ClassVar

import structlog
from wireup import injectable

from .client import HealthWorkerClient
from .worker import HealthWorkerProcess


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

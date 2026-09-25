from dataclasses import dataclass
from multiprocessing.connection import Connection
from time import perf_counter_ns
from typing import ClassVar

import structlog
from django.db import connections

from enclosure.diagnostics.services import CacheDiagnosticsContext

from ....reports.adapters import ArchitectureAdapter
from ....reports.paging import InsightPagingService
from ....reports.service import ReportsService
from ..model import HealthExecutionRequest, HealthExecutionResult, HealthRunOutcome


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

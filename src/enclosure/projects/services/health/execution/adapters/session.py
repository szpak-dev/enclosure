from dataclasses import dataclass
from multiprocessing.connection import Connection
from time import perf_counter_ns
from typing import cast

import structlog
from django.db import connections
from modwire.application import CacheOutcome

from enclosure.diagnostics.services.reporter import CacheDiagnosticsReporter

from .....errors import ProjectsError
from ..evaluation import HealthWorkerEvaluationService
from ..model import (
    HealthCacheOutcomeDiagnostic,
    HealthExecutionRequest,
    HealthExecutionResponse,
    HealthPhaseDiagnostic,
    HealthPhaseToken,
    HealthRunOutcome,
    IncompleteHealthExecutionResult,
)
from ..reporter import HealthPhaseReporter


@dataclass(frozen=True)
class HealthWorkerSession(CacheDiagnosticsReporter, HealthPhaseReporter):
    connection: Connection
    evaluation: HealthWorkerEvaluationService

    def run(self) -> None:
        while True:
            try:
                payload: object = self.connection.recv()
            except (EOFError, OSError):
                return
            request = HealthExecutionRequest.model_validate(payload)
            self.execute_request(request)
            del request

    def execute_request(self, request: HealthExecutionRequest) -> None:
        logger = cast(structlog.stdlib.BoundLogger, structlog.get_logger(__name__))
        started_ns = perf_counter_ns()
        outcome = HealthRunOutcome.FAILED
        logger.info(
            "project_health_architecture_started",
            run_id=request.run_id,
            started_ns=started_ns,
            project_id=request.source.project_id,
            workspace_id=request.source.workspace_id,
        )
        phase_reporter_token = self.evaluation.phases.set_reporter(self)
        cache_reporter_token = self.evaluation.cache.set_reporter(self)
        try:
            try:
                result = self.evaluation.evaluate(request)
            except ProjectsError as error:
                result = IncompleteHealthExecutionResult(
                    outcome=HealthRunOutcome.REJECTED,
                    cache_outcomes=(),
                    phase_diagnostics=(),
                    detail=str(error),
                )
            self.connection.send(HealthExecutionResponse(result=result).model_dump(mode="json"))
            outcome = result.outcome
        finally:
            self.evaluation.cache.reset_reporter(cache_reporter_token)
            self.evaluation.phases.reset_reporter(phase_reporter_token)
            connections.close_all()
            finished_ns = perf_counter_ns()
            logger.info(
                "project_health_architecture_terminal",
                run_id=request.run_id,
                outcome=outcome.value,
                started_ns=started_ns,
                finished_ns=finished_ns,
                duration_ns=finished_ns - started_ns,
                project_id=request.source.project_id,
                workspace_id=request.source.workspace_id,
            )

    def report_phase(self, receipt: HealthPhaseToken | HealthPhaseDiagnostic) -> None:
        self.connection.send(receipt.model_dump(mode="json"))

    def report_cache_outcomes(self, outcomes: tuple[CacheOutcome, ...]) -> None:
        self.connection.send(HealthCacheOutcomeDiagnostic(outcomes=outcomes).model_dump(mode="json"))

from __future__ import annotations

from dataclasses import dataclass
from multiprocessing.connection import Connection
from time import perf_counter_ns
from typing import TYPE_CHECKING, cast

import structlog
from django import setup
from django.db import connections
from wireup import SyncContainer

from ..model import HealthExecutionRequest, HealthRunOutcome

if TYPE_CHECKING:
    from ..evaluation import HealthWorkerEvaluationService


@dataclass(frozen=True)
class HealthWorkerProcess:
    connection: Connection

    def run(self) -> None:
        setup()
        from enclosure.autowiring import application

        from ..evaluation import HealthWorkerEvaluationService

        connections.close_all()
        container = cast(SyncContainer, application.create_container())
        try:
            evaluation = container.get(HealthWorkerEvaluationService)
            while True:
                try:
                    payload: object = self.connection.recv()
                except (EOFError, OSError):
                    return
                request = HealthExecutionRequest.model_validate(payload)
                self.execute_request(request, evaluation)
                del request
        finally:
            container.close()
            self.connection.close()
            connections.close_all()

    def execute_request(
        self,
        request: HealthExecutionRequest,
        evaluation: HealthWorkerEvaluationService,
    ) -> None:
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
        try:
            self.connection.send(evaluation.evaluate(request))
            outcome = HealthRunOutcome.COMPLETED
        finally:
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

import os
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import cast

from django import setup
from django.db import connections
from wireup import SyncContainer

from ..model import HealthWorkerReady


@dataclass(frozen=True)
class HealthWorkerProcess:
    connection: Connection

    def run(self) -> None:
        os.setsid()
        setup()
        from enclosure.autowiring import application

        from ..evaluation import HealthWorkerEvaluationService
        from .session import HealthWorkerSession

        connections.close_all()
        container = cast(SyncContainer, application.create_container())
        try:
            evaluation = container.get(HealthWorkerEvaluationService)
            self.connection.send(HealthWorkerReady().model_dump(mode="json"))
            HealthWorkerSession(connection=self.connection, evaluation=evaluation).run()
        finally:
            container.close()
            self.connection.close()
            connections.close_all()

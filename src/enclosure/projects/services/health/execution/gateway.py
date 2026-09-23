from abc import ABC, abstractmethod

from enclosure.shared.execution import CancellationSignal

from ...reports.model import ArchitectureSource
from .model import HealthExecutionResult


class HealthWorkerGateway(ABC):
    timeout_seconds: int

    @abstractmethod
    def execute(
        self,
        source: ArchitectureSource,
        signal: CancellationSignal,
        timeout_seconds: int,
    ) -> HealthExecutionResult:
        raise NotImplementedError

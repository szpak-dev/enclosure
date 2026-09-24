from abc import ABC, abstractmethod

from enclosure.shared.execution import CancellationSignal

from .model import HealthExecutionRequest, HealthExecutionResult


class HealthWorkerGateway(ABC):
    timeout_seconds: int

    @abstractmethod
    def execute(
        self,
        request: HealthExecutionRequest,
        signal: CancellationSignal,
        timeout_seconds: int,
    ) -> HealthExecutionResult:
        raise NotImplementedError

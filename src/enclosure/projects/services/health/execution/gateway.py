from abc import ABC, abstractmethod

from enclosure.shared.execution import CancellationSignal

from .model import CompletedHealthExecutionResult, HealthExecutionRequest, IncompleteHealthExecutionResult


class HealthWorkerGateway(ABC):
    timeout_seconds: int

    @abstractmethod
    def execute(
        self,
        request: HealthExecutionRequest,
        signal: CancellationSignal,
        timeout_seconds: int,
    ) -> CompletedHealthExecutionResult | IncompleteHealthExecutionResult:
        raise NotImplementedError

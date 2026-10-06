from abc import ABC, abstractmethod

from enclosure.shared.execution import CancellationSignal

from .model import (
    CacheOutcomeState,
    CompletedHealthExecutionResult,
    HealthCacheIdentity,
    HealthCacheLookup,
    HealthExecutionRequest,
    IncompleteHealthExecutionResult,
)


class ArchitectureHealthCache(ABC):
    @abstractmethod
    def load(self, identity: HealthCacheIdentity) -> HealthCacheLookup:
        raise NotImplementedError

    @abstractmethod
    def store(self, identity: HealthCacheIdentity, payload: bytes) -> CacheOutcomeState:
        raise NotImplementedError


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

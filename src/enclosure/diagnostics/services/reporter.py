from abc import ABC, abstractmethod

from modwire.application import CacheOutcome


class CacheDiagnosticsReporter(ABC):
    @abstractmethod
    def report_cache_outcomes(self, outcomes: tuple[CacheOutcome, ...]) -> None:
        raise NotImplementedError

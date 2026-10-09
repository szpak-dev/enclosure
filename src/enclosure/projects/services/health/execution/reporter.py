from abc import ABC, abstractmethod

from .model import HealthPhaseDiagnostic, HealthPhaseToken


class HealthPhaseReporter(ABC):
    @abstractmethod
    def report_phase(self, receipt: HealthPhaseToken | HealthPhaseDiagnostic) -> None:
        raise NotImplementedError

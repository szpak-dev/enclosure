from abc import ABC, abstractmethod

from .model import PresentationTemplate


class PresentationTemplateRepository(ABC):
    @abstractmethod
    def find(self, operation_id: str) -> PresentationTemplate:
        raise NotImplementedError

    @abstractmethod
    def find_all(self, operation_ids: tuple[str, ...]) -> tuple[PresentationTemplate, ...]:
        raise NotImplementedError

    @abstractmethod
    def error(self) -> PresentationTemplate:
        raise NotImplementedError

    @abstractmethod
    def incomplete(self) -> PresentationTemplate:
        raise NotImplementedError

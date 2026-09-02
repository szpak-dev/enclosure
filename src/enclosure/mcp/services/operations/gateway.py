from abc import ABC, abstractmethod

from .model import SirenDocument, ToolCatalogue, ToolInvocation


class SirenGateway(ABC):
    @abstractmethod
    def catalogue(self) -> ToolCatalogue:
        raise NotImplementedError

    @abstractmethod
    def invoke(self, invocation: ToolInvocation) -> SirenDocument:
        raise NotImplementedError

from dataclasses import dataclass

from wireup import injectable

from .gateway import SirenGateway
from .model import SirenDocument, ToolCatalogue, ToolInvocation


@injectable
@dataclass(frozen=True)
class OperationsService:
    gateway: SirenGateway

    def catalogue(self) -> ToolCatalogue:
        return self.gateway.catalogue()

    def invoke(self, invocation: ToolInvocation) -> SirenDocument:
        return self.gateway.invoke(invocation)

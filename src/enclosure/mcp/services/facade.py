from dataclasses import dataclass

from wireup import injectable

from .bootstrap import AgentBootstrapService
from .operations import OperationsService, ToolCatalogue, ToolInvocation
from .presentation import McpPresentation, PresentationService


@injectable
@dataclass(frozen=True)
class McpService:
    operations: OperationsService
    bootstrap: AgentBootstrapService
    presentation: PresentationService

    def instructions(self) -> str:
        return self.bootstrap.instructions()

    def catalogue(self) -> ToolCatalogue:
        return self.operations.catalogue()

    def invoke(self, invocation: ToolInvocation) -> McpPresentation:
        document = self.operations.invoke(invocation)
        return self.presentation.present(document)

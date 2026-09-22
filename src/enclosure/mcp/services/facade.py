from dataclasses import dataclass

from wireup import injectable

from .bootstrap import AgentBootstrapService
from .diagnostics import (
    DiagnosticOwner,
    DiagnosticStageName,
    McpDiagnosticRequest,
    McpDiagnosticsService,
    McpInvocationResult,
)
from .operations import OperationsService, ToolCatalogue, ToolInvocation
from .presentation import PresentationService


@injectable
@dataclass(frozen=True)
class McpService:
    operations: OperationsService
    bootstrap: AgentBootstrapService
    presentation: PresentationService
    diagnostics: McpDiagnosticsService

    def instructions(self) -> str:
        return self.bootstrap.instructions()

    def catalogue(self) -> ToolCatalogue:
        catalogue = self.operations.catalogue()
        self.presentation.strategies(catalogue)
        return catalogue

    def invoke(self, invocation: ToolInvocation, request: McpDiagnosticRequest) -> McpInvocationResult:
        trace = self.diagnostics.begin(request)
        try:
            operation_started_ns = self.diagnostics.started()
            document = self.operations.invoke(invocation)
            self.diagnostics.record(
                trace,
                DiagnosticStageName.SIREN_OPERATION,
                DiagnosticOwner.MCP_OPERATIONS,
                operation_started_ns,
            )
            presentation_started_ns = self.diagnostics.started()
            presentation = self.presentation.present(document)
            self.diagnostics.record(
                trace,
                DiagnosticStageName.PRESENTATION,
                DiagnosticOwner.MCP_SERVICE,
                presentation_started_ns,
            )
            return McpInvocationResult(
                presentation=presentation,
                diagnostics=self.diagnostics.complete(trace),
            )
        finally:
            self.diagnostics.reset()

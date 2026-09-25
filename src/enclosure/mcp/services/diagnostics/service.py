from dataclasses import dataclass
from time import perf_counter_ns
from typing import ClassVar

import structlog
from wireup import injectable

from enclosure.diagnostics.services import CacheDiagnosticsContext

from .model import DiagnosticOwner, DiagnosticStage, DiagnosticStageName, DiagnosticTrace, McpDiagnosticRequest, McpDiagnostics

@injectable
@dataclass(frozen=True)
class McpDiagnosticsService:
    logger: ClassVar = structlog.get_logger(__name__)

    cache: CacheDiagnosticsContext

    def begin(self, request: McpDiagnosticRequest) -> DiagnosticTrace:
        started_ns = perf_counter_ns()
        self.logger.info(
            "mcp_tool_started",
            correlation_id=request.correlation_id,
            started_ns=started_ns,
            release=request.release,
            process_id=request.process_id,
            session_mode=request.session_mode,
            session_reused=request.session_reused,
        )
        self.cache.begin()
        return DiagnosticTrace(request=request, started_ns=started_ns)

    def started(self) -> int:
        return perf_counter_ns()

    def record(
        self,
        trace: DiagnosticTrace,
        name: DiagnosticStageName,
        owner: DiagnosticOwner,
        started_ns: int,
    ) -> None:
        finished_ns = perf_counter_ns()
        stage = DiagnosticStage(
            name=name,
            owner=owner,
            started_ns=started_ns,
            finished_ns=finished_ns,
            duration_ns=finished_ns - started_ns,
        )
        trace.stages.append(stage)
        self.logger.info(
            "mcp_stage_finished",
            correlation_id=trace.request.correlation_id,
            **stage.model_dump(mode="json"),
        )

    def complete(self, trace: DiagnosticTrace) -> McpDiagnostics:
        self.record(
            trace,
            DiagnosticStageName.MCP_TOOL,
            DiagnosticOwner.MCP_SERVICE,
            trace.started_ns,
        )
        request = trace.request
        return McpDiagnostics(
            correlation_id=request.correlation_id,
            release=request.release,
            process_id=request.process_id,
            cache_directory=request.cache_directory,
            session_mode=request.session_mode,
            session_reused=request.session_reused,
            stages=tuple(trace.stages),
            cache_outcomes=self.cache.read(),
        )

    def reset(self) -> None:
        self.cache.reset()

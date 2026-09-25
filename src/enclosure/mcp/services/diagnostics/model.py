from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from modwire.application import CacheOutcome
from pydantic import BaseModel, ConfigDict

from ..presentation import McpPresentation


class DiagnosticValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DiagnosticStageName(StrEnum):
    MCP_TOOL = "mcp.tool"
    SIREN_OPERATION = "siren.operation"
    PRESENTATION = "mcp.presentation"


class DiagnosticOwner(StrEnum):
    MCP_SERVICE = "mcp.service"
    MCP_OPERATIONS = "mcp.operations"


class McpDiagnosticRequest(DiagnosticValue):
    correlation_id: str
    release: str
    process_id: int
    cache_directory: str
    session_mode: str
    session_reused: bool


class DiagnosticStage(DiagnosticValue):
    name: DiagnosticStageName
    owner: DiagnosticOwner
    started_ns: int
    finished_ns: int
    duration_ns: int


class McpDiagnostics(DiagnosticValue):
    META_KEY: ClassVar[str] = "enclosure.dev/diagnostics"

    correlation_id: str
    release: str
    process_id: int
    cache_directory: str
    session_mode: str
    session_reused: bool
    stages: tuple[DiagnosticStage, ...]
    cache_outcomes: tuple[CacheOutcome, ...]


class McpInvocationResult(DiagnosticValue):
    presentation: McpPresentation
    diagnostics: McpDiagnostics


@dataclass
class DiagnosticTrace:
    request: McpDiagnosticRequest
    started_ns: int
    stages: list[DiagnosticStage] = field(default_factory=list)

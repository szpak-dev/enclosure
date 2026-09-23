from enum import StrEnum
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ArchitectureReportMetadata(TypedDict):
    id: str
    title: str
    description: str
    model: str
    path: str
    order: int
    children: list["ArchitectureReportMetadata"]


class ShapeFindingInput(TypedDict):
    source_id: str
    rule_name: str
    actual: int | str | bool
    limit: int | str | bool
    realm: str
    symbol_kind: str
    symbol_name: str


class FlowFindingInput(TypedDict):
    violation_type: str
    path: list[str]
    violation_index: int
    rule_name: str
    message: str
    source_module: str
    target_module: str


class GuidanceFindingInput(TypedDict):
    rule: str
    source_id: str
    guidance_ids: list[str]
    message: str
    remediation: str


class HotspotInput(TypedDict):
    source_id: str
    incoming_count: int
    outgoing_count: int
    pressure_score: int


class ClusterInput(TypedDict):
    name: str
    files: list[str]
    incoming_count: int
    outgoing_count: int
    pressure_score: int
    top_files: list[str]


class HotspotReportInput(TypedDict):
    hotspots: list[HotspotInput]


class ClusterReportInput(TypedDict):
    clusters: list[ClusterInput]


class CoherenceReportInput(TypedDict):
    roots: list[str]
    leaves: list[str]
    isolated: list[str]
    external_dependencies: list[str]


class CallableInput(TypedDict):
    source_callable: str
    calls: list[str]
    callers: list[str]


class CallableReportInput(TypedDict):
    entries: list[CallableInput]


class ExportInput(TypedDict):
    source_id: str
    name: str
    kind: str
    crossing_type: str
    reason: str


class ExportReportInput(TypedDict):
    unused_exports: list[ExportInput]


class ArchitectureGroupInput(TypedDict):
    name: str
    source_ids: list[str]


class ArchitectureMapReportInput(TypedDict):
    metadata: ArchitectureReportMetadata
    modules: list[ArchitectureGroupInput]
    layers: list[ArchitectureGroupInput]
    unknown_files: list[str]


class InsightReportInput(TypedDict):
    metadata: ArchitectureReportMetadata
    hotspots: HotspotReportInput
    clusters: ClusterReportInput
    coherence: CoherenceReportInput
    callables: CallableReportInput
    exports: ExportReportInput


class ReportValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HealthOutcome(StrEnum):
    HEALTHY = "healthy"
    ADVISORY = "advisory"
    GATING_FAILURE = "gating-failure"


class HealthFinding(ReportValue):
    rule: str
    target: str
    message: str
    next_action: str


class ShapeHealthFinding(HealthFinding):
    kind: Literal["shape"]
    source_file: str
    realm: str
    symbol_kind: str
    symbol_name: str
    actual: int | str | bool
    limit: int | str | bool


class FlowHealthFinding(HealthFinding):
    kind: Literal["flow"]
    violation_type: str
    path: tuple[str, ...]
    violation_index: int
    source_module: str
    target_module: str


class GuidanceHealthFinding(HealthFinding):
    kind: Literal["guidance"]
    related_ids: tuple[str, ...]
    remediation: str


class HealthReportSummary(ReportValue):
    id: str
    title: str
    failure_count: int
    advisory_count: int


class HealthReportSet(ReportValue):
    healthy: bool
    reports: tuple[dict[str, JsonValue], ...]


class ArchitectureSource(ReportValue):
    project_id: str
    workspace_id: str
    architecture_root: str
    language: str
    boundaries_yaml: str
    shape_yaml: str


class HealthReport(ReportValue):
    outcome: HealthOutcome
    healthy: bool
    reports: tuple[HealthReportSummary, ...]
    failure_count: int
    advisory_count: int
    targets: tuple[str, ...]
    next_actions: tuple[str, ...]
    failures: tuple[
        Annotated[ShapeHealthFinding | FlowHealthFinding | GuidanceHealthFinding, Field(discriminator="kind")],
        ...,
    ]
    advisories: tuple[
        Annotated[ShapeHealthFinding | FlowHealthFinding | GuidanceHealthFinding, Field(discriminator="kind")],
        ...,
    ]


class InsightFindingKind(StrEnum):
    HOTSPOT = "hotspot"
    CLUSTER = "cluster"


class InsightSection(ReportValue):
    path: str
    total: int


class InsightFinding(ReportValue):
    kind: InsightFindingKind
    area: str
    pressure_score: float
    incoming_count: int
    outgoing_count: int


class InsightReportSet(ReportValue):
    project_id: str
    workspace_id: str
    revision: str
    reports: tuple[dict[str, JsonValue], ...]


class InsightsReport(ReportValue):
    project_id: str
    workspace_id: str
    revision: str
    reports: tuple[dict[str, JsonValue], ...]
    sections: tuple[InsightSection, ...]
    affected_areas: tuple[str, ...]
    top_findings: tuple[InsightFinding, ...]


class InsightPage(ReportValue):
    project_id: str
    workspace_id: str
    revision: str
    path: str
    offset: int
    limit: int
    total: int
    items: tuple[JsonValue, ...]
    has_more: bool
    next_offset: int

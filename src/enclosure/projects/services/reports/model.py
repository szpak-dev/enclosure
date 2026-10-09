from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, TypedDict

from modwire.application import QueryableCodeMap
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ..architecture_manifests.model import (
    ArchitectureComparisonState,
    ArchitectureFindingKind,
    ArchitectureFindingOwner,
    ArchitectureSemanticValue,
)
from ..health.attestations.model import ArchitectureConformanceAttestation
from ..health.conformance.model import (
    ArchitectureAssertionEvidence,
    ArchitectureConformanceCoverage,
    ArchitectureConformanceReport,
    ArchitectureCoverageEvidence,
    ArchitectureUnexpectedEvidence,
)


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


class HealthFindingKind(StrEnum):
    FAILURE = "failure"
    ADVISORY = "advisory"


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


class ConformanceHealthFinding(HealthFinding):
    kind: Literal["conformance"]
    fingerprint: str
    contract_unit: str
    evidence: Annotated[
        ArchitectureAssertionEvidence | ArchitectureUnexpectedEvidence | ArchitectureCoverageEvidence,
        Field(discriminator="kind"),
    ]
    expected: ArchitectureSemanticValue
    observed: tuple[ArchitectureSemanticValue, ...]
    state: ArchitectureComparisonState
    finding_kind: ArchitectureFindingKind
    owner: ArchitectureFindingOwner


class HealthReportSummary(ReportValue):
    id: str
    title: str
    failure_count: int
    advisory_count: int
    coverage: tuple[ArchitectureConformanceCoverage, ...]


class HealthReportSet(ReportValue):
    healthy: bool
    reports: tuple[dict[str, JsonValue], ...]
    conformance: ArchitectureConformanceReport
    attestation: ArchitectureConformanceAttestation


class ArchitectureSource(ReportValue):
    project_id: str
    workspace_id: str
    architecture_root: str
    language: str
    boundaries_yaml: str
    shape_yaml: str


@dataclass(frozen=True)
class ArchitectureCodeMapObservation:
    code_map: QueryableCodeMap
    source_digest: str


class ArchitectureObservation(ReportValue):
    implementation_document: dict[str, JsonValue]
    source_digest: str
    document_digest: str


class ArchitectureReportObservation(ReportValue):
    reports: tuple[dict[str, JsonValue], ...]
    source_digest: str


class HealthReport(ReportValue):
    revision: str
    outcome: HealthOutcome
    healthy: bool
    attestation: ArchitectureConformanceAttestation
    reports: tuple[HealthReportSummary, ...]
    failure_count: int
    advisory_count: int
    failure_kind: HealthFindingKind
    advisory_kind: HealthFindingKind
    targets: tuple[str, ...]
    next_actions: tuple[str, ...]
    failures: tuple[
        Annotated[
            ShapeHealthFinding | FlowHealthFinding | GuidanceHealthFinding | ConformanceHealthFinding,
            Field(discriminator="kind"),
        ],
        ...,
    ]
    advisories: tuple[
        Annotated[
            ShapeHealthFinding | FlowHealthFinding | GuidanceHealthFinding | ConformanceHealthFinding,
            Field(discriminator="kind"),
        ],
        ...,
    ]


class HealthFindingPage(ReportValue):
    revision: str
    kind: HealthFindingKind
    offset: int
    limit: int
    total: int
    items: tuple[
        Annotated[
            ShapeHealthFinding | FlowHealthFinding | GuidanceHealthFinding | ConformanceHealthFinding,
            Field(discriminator="kind"),
        ],
        ...,
    ]
    has_more: bool
    next_offset: int


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
    report_count: int
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


class InsightContentPage(ReportValue):
    revision: str
    section_offset: int
    path: str
    item_offset: int
    limit: int
    section_total: int
    items: tuple[JsonValue, ...]
    has_more: bool
    next_section_offset: int
    next_item_offset: int

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, JsonValue


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
    related_ids: tuple[str, ...]
    remediation: str
    next_action: str


class HealthReportSummary(ReportValue):
    id: str
    title: str
    failure_count: int
    advisory_count: int


class HealthReportSet(ReportValue):
    healthy: bool
    reports: tuple[dict[str, JsonValue], ...]


class InsightSource(ReportValue):
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
    failures: tuple[HealthFinding, ...]
    advisories: tuple[HealthFinding, ...]


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

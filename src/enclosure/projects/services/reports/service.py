from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, cast

from pydantic import JsonValue
from wireup import injectable

from .adapters import ArchitectureAdapter
from .model import (
    ArchitectureReportMetadata,
    ArchitectureSource,
    ClusterInput,
    FlowFindingInput,
    FlowHealthFinding,
    GuidanceFindingInput,
    GuidanceHealthFinding,
    HealthOutcome,
    HealthReport,
    HealthReportSet,
    HealthReportSummary,
    HotspotInput,
    InsightFinding,
    InsightFindingKind,
    InsightPage,
    InsightReportInput,
    InsightReportSet,
    InsightsReport,
    ShapeFindingInput,
    ShapeHealthFinding,
)
from .paging import InsightPagingService


@injectable
@dataclass(frozen=True)
class ReportsService:
    architecture: ArchitectureAdapter
    paging: InsightPagingService

    MAX_TOP_FINDINGS: ClassVar[int] = 5

    def generate_health_report(
        self,
        source: ArchitectureSource,
    ) -> HealthReportSet:
        reports = self.architecture.generate_reports(source)
        health_reports = tuple(report for report in reports if "violations" in report)
        return HealthReportSet(
            healthy=all(not report["violations"] for report in health_reports),
            reports=health_reports,
        )

    def summarize_health_report(self, report: HealthReportSet) -> HealthReport:
        summaries = []
        failures = []
        advisories = []
        for item in report.reports:
            report_id, title = self._metadata(item)
            report_failures = tuple(
                self._health_finding(finding, report_id) for finding in self._mappings(item.get("violations", []))
            )
            report_advisories = tuple(
                self._health_finding(finding, report_id) for finding in self._mappings(item.get("advisories", []))
            )
            summaries.append(
                HealthReportSummary(
                    id=report_id,
                    title=title,
                    failure_count=len(report_failures),
                    advisory_count=len(report_advisories),
                )
            )
            failures.extend(report_failures)
            advisories.extend(report_advisories)
        targets = tuple(dict.fromkeys(finding.target for finding in (*failures, *advisories)))
        next_actions = tuple(dict.fromkeys(finding.next_action for finding in (*failures, *advisories)))
        outcome = (
            HealthOutcome.GATING_FAILURE
            if failures
            else HealthOutcome.ADVISORY
            if advisories
            else HealthOutcome.HEALTHY
        )
        return HealthReport(
            outcome=outcome,
            healthy=report.healthy,
            reports=tuple(summaries),
            failure_count=len(failures),
            advisory_count=len(advisories),
            targets=targets,
            next_actions=next_actions,
            failures=tuple(failures),
            advisories=tuple(advisories),
        )

    def generate_insights_report(
        self,
        source: ArchitectureSource,
    ) -> InsightReportSet:
        reports = self.architecture.generate_reports(source)
        insights = tuple(report for report in reports if "violations" not in report)
        return InsightReportSet(
            project_id=source.project_id,
            workspace_id=source.workspace_id,
            revision=self.paging.revision(insights),
            reports=insights,
        )

    def summarize_insights_report(self, report: InsightReportSet) -> InsightsReport:
        sections = self.paging.sections(report)
        findings = sorted(
            self._insight_findings(report.reports),
            key=lambda finding: finding.pressure_score,
            reverse=True,
        )[: self.MAX_TOP_FINDINGS]
        return InsightsReport(
            project_id=report.project_id,
            workspace_id=report.workspace_id,
            revision=report.revision,
            reports=report.reports,
            sections=sections,
            affected_areas=tuple(dict.fromkeys(finding.area for finding in findings)),
            top_findings=tuple(findings),
        )

    def read_insight_page(
        self,
        report: InsightReportSet,
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> InsightPage:
        return self.paging.page(report, path, expected_revision, offset, limit)

    def _metadata(self, report: Mapping[str, JsonValue]) -> tuple[str, str]:
        metadata = cast(ArchitectureReportMetadata, report["metadata"])
        return metadata["id"], metadata["title"]

    def _health_finding(
        self,
        finding: Mapping[str, JsonValue],
        report_id: str,
    ) -> ShapeHealthFinding | FlowHealthFinding | GuidanceHealthFinding:
        if report_id == "architecture.violations.shape":
            return self._shape_health_finding(cast(ShapeFindingInput, finding))
        if report_id == "architecture.violations.flow":
            return self._flow_health_finding(cast(FlowFindingInput, finding))
        if report_id == "guidance-graph":
            return self._guidance_health_finding(cast(GuidanceFindingInput, finding))
        raise ValueError(f"Unsupported health report {report_id!r}.")

    def _shape_health_finding(self, finding: ShapeFindingInput) -> ShapeHealthFinding:
        source_file = finding["source_id"]
        rule = finding["rule_name"]
        realm = finding["realm"]
        symbol_kind = finding["symbol_kind"]
        symbol_name = finding["symbol_name"]
        actual = finding["actual"]
        limit = finding["limit"]
        location = f"{symbol_kind} {symbol_name}" if symbol_name else symbol_kind
        target = f"{source_file}::{symbol_kind}:{symbol_name}" if symbol_name else source_file
        return ShapeHealthFinding(
            kind="shape",
            rule=rule,
            target=target,
            message=f"{location} reports {actual!r}; configured limit is {limit!r} in realm {realm!r}.",
            next_action=(f"Review {location} in {source_file}: {rule} is {actual!r}; configured limit is {limit!r}."),
            source_file=source_file,
            realm=realm,
            symbol_kind=symbol_kind,
            symbol_name=symbol_name,
            actual=actual,
            limit=limit,
        )

    def _flow_health_finding(self, finding: FlowFindingInput) -> FlowHealthFinding:
        path = tuple(finding["path"])
        violation_index = finding["violation_index"]
        rule = finding["rule_name"]
        target = " → ".join(path)
        edge = (
            f"{path[violation_index - 1]} → {path[violation_index]}" if violation_index > 0 else path[violation_index]
        )
        return FlowHealthFinding(
            kind="flow",
            rule=rule,
            target=target,
            message=finding["message"],
            next_action=f"Review dependency location {edge} at path index {violation_index} against {rule}.",
            violation_type=finding["violation_type"],
            path=path,
            violation_index=violation_index,
            source_module=finding["source_module"],
            target_module=finding["target_module"],
        )

    def _guidance_health_finding(self, finding: GuidanceFindingInput) -> GuidanceHealthFinding:
        target = finding["source_id"]
        rule = finding["rule"]
        return GuidanceHealthFinding(
            kind="guidance",
            rule=rule,
            target=target,
            message=finding["message"],
            next_action=f"Review {target} against {rule}.",
            related_ids=tuple(finding["guidance_ids"]),
            remediation=finding["remediation"],
        )

    def _insight_findings(self, reports: tuple[dict[str, JsonValue], ...]) -> list[InsightFinding]:
        findings = []
        for report in reports:
            metadata = cast(ArchitectureReportMetadata, report["metadata"])
            if metadata["id"] != "architecture.insights":
                continue
            insight = cast(InsightReportInput, report)
            findings.extend(self._hotspot_finding(hotspot) for hotspot in insight["hotspots"]["hotspots"])
            findings.extend(self._cluster_finding(cluster) for cluster in insight["clusters"]["clusters"])
        return findings

    def _hotspot_finding(self, hotspot: HotspotInput) -> InsightFinding:
        return InsightFinding(
            kind=InsightFindingKind.HOTSPOT,
            area=hotspot["source_id"],
            pressure_score=hotspot["pressure_score"],
            incoming_count=hotspot["incoming_count"],
            outgoing_count=hotspot["outgoing_count"],
        )

    def _cluster_finding(self, cluster: ClusterInput) -> InsightFinding:
        return InsightFinding(
            kind=InsightFindingKind.CLUSTER,
            area=cluster["name"],
            pressure_score=cluster["pressure_score"],
            incoming_count=cluster["incoming_count"],
            outgoing_count=cluster["outgoing_count"],
        )

    def _mappings(self, value: JsonValue) -> tuple[Mapping[str, JsonValue], ...]:
        return tuple(cast(list[dict[str, JsonValue]], value))

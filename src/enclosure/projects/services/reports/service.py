from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from pydantic import JsonValue
from wireup import injectable

from .adapters import ArchitectureAdapter
from .model import (
    HealthFinding,
    HealthOutcome,
    HealthReport,
    HealthReportSet,
    HealthReportSummary,
    InsightFinding,
    InsightFindingKind,
    InsightPage,
    InsightReportSet,
    InsightSource,
    InsightsReport,
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
        architecture_root: str,
        language: str,
        boundaries_yaml: str,
        shape_yaml: str,
    ) -> HealthReportSet:
        reports = self.architecture.generate_reports(
            architecture_root,
            language,
            boundaries_yaml,
            shape_yaml,
        )
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
        source: InsightSource,
    ) -> InsightReportSet:
        reports = self.architecture.generate_reports(
            source.architecture_root,
            source.language,
            source.boundaries_yaml,
            source.shape_yaml,
        )
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
        metadata = report.get("metadata")
        if not isinstance(metadata, Mapping):
            return ("unknown", "Architecture report")
        report_id = metadata.get("id")
        title = metadata.get("title")
        return (
            report_id if isinstance(report_id, str) and report_id else "unknown",
            title if isinstance(title, str) and title else "Architecture report",
        )

    def _health_finding(self, finding: Mapping[str, JsonValue], report_id: str) -> HealthFinding:
        rule_value = finding.get("rule", finding.get("rule_name", "unknown-rule"))
        rule = rule_value if isinstance(rule_value, str) else str(rule_value)
        source_id = finding.get("source_id")
        path = finding.get("path")
        target = (
            source_id
            if isinstance(source_id, str) and source_id
            else " → ".join(str(segment) for segment in path)
            if isinstance(path, list | tuple) and path
            else report_id
        )
        message_value = finding.get("message")
        if isinstance(message_value, str) and message_value:
            message = message_value
        else:
            message = f"Actual {finding.get('actual', 'unknown')}; configured limit {finding.get('limit', 'unknown')}."
        related_ids_value = finding.get("guidance_ids", [])
        related_ids = (
            tuple(str(identifier) for identifier in related_ids_value)
            if isinstance(related_ids_value, list | tuple)
            else ()
        )
        remediation_value = finding.get("remediation", "architecture")
        return HealthFinding(
            rule=rule,
            target=target,
            message=message,
            related_ids=related_ids,
            remediation=remediation_value if isinstance(remediation_value, str) else str(remediation_value),
            next_action=f"Review {target} against {rule}.",
        )

    def _insight_findings(self, reports: tuple[dict[str, JsonValue], ...]) -> list[InsightFinding]:
        findings = []
        for report in reports:
            findings.extend(self._find_pressure_values(report))
        return findings

    def _find_pressure_values(self, value: JsonValue) -> list[InsightFinding]:
        findings = []
        if isinstance(value, Mapping):
            pressure = value.get("pressure_score")
            source_id = value.get("source_id")
            name = value.get("name")
            if (
                isinstance(pressure, int | float)
                and not isinstance(pressure, bool)
                and (isinstance(source_id, str) or isinstance(name, str))
            ):
                area = source_id if isinstance(source_id, str) else name if isinstance(name, str) else "unknown"
                findings.append(
                    InsightFinding(
                        kind=InsightFindingKind.HOTSPOT if isinstance(source_id, str) else InsightFindingKind.CLUSTER,
                        area=area,
                        pressure_score=float(pressure),
                        incoming_count=self._integer(value.get("incoming_count")),
                        outgoing_count=self._integer(value.get("outgoing_count")),
                    )
                )
            for item in value.values():
                findings.extend(self._find_pressure_values(item))
        elif isinstance(value, list | tuple):
            for item in value:
                findings.extend(self._find_pressure_values(item))
        return findings

    def _mappings(self, value: JsonValue) -> tuple[Mapping[str, JsonValue], ...]:
        if not isinstance(value, list | tuple):
            return ()
        return tuple(item for item in value if isinstance(item, Mapping))

    def _integer(self, value: JsonValue) -> int:
        return value if isinstance(value, int) and not isinstance(value, bool) else 0

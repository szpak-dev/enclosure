from collections.abc import Sequence
from dataclasses import dataclass
from operator import attrgetter

from wireup import injectable

from ....errors import ProjectsError
from ...architecture_manifests.assertions.model import ArchitectureAssertionKind
from ...architecture_manifests.model import ArchitectureComparison, ArchitectureComparisonState
from .model import ArchitectureConformanceCoverage, ArchitectureConformanceFinding, ArchitectureConformanceReport
from .projectors.base import ArchitectureConformanceFindingProjector


@injectable
@dataclass(frozen=True)
class ArchitectureConformanceService:
    projectors: Sequence[ArchitectureConformanceFindingProjector]

    def project(self, comparison: ArchitectureComparison) -> ArchitectureConformanceReport:
        projectors = tuple(sorted(self.projectors, key=attrgetter("order", "name")))
        findings: list[ArchitectureConformanceFinding] = []
        for result in comparison.results:
            if result.state == ArchitectureComparisonState.PASS:
                continue
            matches = tuple(projector for projector in projectors if projector.supports(result))
            if len(matches) != 1:
                raise ProjectsError(
                    f"Architecture assertion {result.assertion_id!r} has no unique health finding projector."
                )
            findings.append(matches[0].project(result))
        coverage = tuple(
            ArchitectureConformanceCoverage(
                assertion_kind=kind,
                passed=sum(
                    result.assertion_kind == kind and result.state == ArchitectureComparisonState.PASS
                    for result in comparison.results
                ),
                failed=sum(
                    result.assertion_kind == kind and result.state == ArchitectureComparisonState.FAIL
                    for result in comparison.results
                ),
                unverified=sum(
                    result.assertion_kind == kind and result.state == ArchitectureComparisonState.UNVERIFIED
                    for result in comparison.results
                ),
            )
            for kind in ArchitectureAssertionKind
        )
        return ArchitectureConformanceReport(
            id="architecture.conformance",
            title="Architecture conformance",
            conclusion=comparison.conclusion,
            coverage=coverage,
            findings=tuple(findings),
            comparison_digest=comparison.digest,
        )

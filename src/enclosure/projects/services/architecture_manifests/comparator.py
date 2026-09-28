import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from operator import attrgetter

from wireup import injectable

from ...errors import ProjectsError
from .facts.model import ArchitectureFactCapability
from .identity import ArchitectureComparisonIdentity
from .model import (
    ArchitectureAssertionResult,
    ArchitectureComparison,
    ArchitectureComparisonConclusion,
    ArchitectureComparisonState,
    ArchitectureContractManifest,
)
from .observed.model import ObservedImplementationManifest
from .rules.base import ArchitectureComparisonRule


@injectable
@dataclass(frozen=True)
class ArchitectureContractComparator:
    rules: Sequence[ArchitectureComparisonRule]
    identity: ArchitectureComparisonIdentity = field(default_factory=ArchitectureComparisonIdentity, init=False)

    def compare(
        self,
        expected: ArchitectureContractManifest,
        observed: ObservedImplementationManifest,
    ) -> ArchitectureComparison:
        rules = tuple(sorted(self.rules, key=attrgetter("order", "name")))
        rule_capabilities = tuple(rule.capability for rule in rules)
        if len(rule_capabilities) != len(set(rule_capabilities)):
            raise ProjectsError("Architecture comparison capabilities must have exactly one rule.")
        required_capabilities = set(ArchitectureFactCapability)
        if set(rule_capabilities) != required_capabilities:
            missing = sorted(capability.value for capability in required_capabilities - set(rule_capabilities))
            raise ProjectsError(f"Architecture comparison rules are missing capabilities: {', '.join(missing)}.")
        observed_capabilities = tuple(item.capability for item in observed.capabilities)
        if len(observed_capabilities) != len(set(observed_capabilities)):
            raise ProjectsError("Observed architecture capabilities must have exactly one support declaration.")
        if set(observed_capabilities) != required_capabilities:
            missing = sorted(capability.value for capability in required_capabilities - set(observed_capabilities))
            raise ProjectsError(f"Observed architecture support is missing capabilities: {', '.join(missing)}.")
        results: list[ArchitectureAssertionResult] = []
        for unit in expected.units:
            for rule in rules:
                results.extend(rule.compare(unit, observed))
        ordered_results = tuple(
            sorted(results, key=attrgetter("unit_key", "capability", "assertion_id", "fingerprint"))
        )
        passed = sum(result.state == ArchitectureComparisonState.PASS for result in ordered_results)
        failed = sum(result.state == ArchitectureComparisonState.FAIL for result in ordered_results)
        unverified = sum(result.state == ArchitectureComparisonState.UNVERIFIED for result in ordered_results)
        if failed:
            conclusion = ArchitectureComparisonConclusion.DOES_NOT_CONFORM
        elif unverified:
            conclusion = ArchitectureComparisonConclusion.UNVERIFIED
        else:
            conclusion = ArchitectureComparisonConclusion.CONFORMS
        payload = {
            "schema_version": self.identity.schema_version,
            "contract_digest": expected.digest,
            "implementation_digest": observed.document_digest,
            "source_digest": observed.source_digest,
            "capabilities": [coverage.model_dump(mode="json") for coverage in observed.capabilities],
            "conclusion": conclusion.value,
            "results": [result.model_dump(mode="json") for result in ordered_results],
            "passed": passed,
            "failed": failed,
            "unverified": unverified,
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        return ArchitectureComparison(
            schema_version=self.identity.schema_version,
            contract_digest=expected.digest,
            implementation_digest=observed.document_digest,
            source_digest=observed.source_digest,
            conclusion=conclusion,
            results=ordered_results,
            passed=passed,
            failed=failed,
            unverified=unverified,
            digest=digest,
        )

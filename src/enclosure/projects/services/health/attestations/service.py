import json
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from operator import attrgetter

from wireup import injectable

from ....errors import ProjectsError
from .contributors.base import ArchitectureAttestationContributor
from .model import (
    ArchitectureAttestationContext,
    ArchitectureAttestationEvidenceKind,
    ArchitectureConformanceAttestation,
)


@injectable
@dataclass(frozen=True)
class ArchitectureAttestationService:
    contributors: Sequence[ArchitectureAttestationContributor]

    def attest(self, context: ArchitectureAttestationContext) -> ArchitectureConformanceAttestation:
        contributors = tuple(sorted(self.contributors, key=attrgetter("order", "name")))
        kinds = tuple(contributor.kind for contributor in contributors)
        expected = tuple(ArchitectureAttestationEvidenceKind)
        if len(kinds) != len(set(kinds)) or set(kinds) != set(expected):
            raise ProjectsError("Architecture attestation requires exactly one contributor per evidence kind.")
        components = tuple(contributor.contribute(context) for contributor in contributors)
        indexed = {component.kind: component.digest for component in components}
        payload = {
            "schema_version": context.identity.attestation_schema_version,
            "digest_algorithm": "sha256",
            "components": [component.model_dump(mode="json") for component in components],
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArchitectureConformanceAttestation(
            schema_version=context.identity.attestation_schema_version,
            digest_algorithm="sha256",
            components=components,
            contract_digest=indexed[ArchitectureAttestationEvidenceKind.CONTRACT],
            implementation_evidence_digest=indexed[
                ArchitectureAttestationEvidenceKind.IMPLEMENTATION_EVIDENCE
            ],
            realization_digest=indexed[ArchitectureAttestationEvidenceKind.REALIZATION],
            source_digest=context.implementation.source_digest,
            policy_digest=indexed[ArchitectureAttestationEvidenceKind.POLICIES],
            configuration_digest=indexed[ArchitectureAttestationEvidenceKind.CONFIGURATION],
            schema_digest=indexed[ArchitectureAttestationEvidenceKind.SCHEMAS],
            tools_digest=indexed[ArchitectureAttestationEvidenceKind.TOOLS],
            comparator_digest=indexed[ArchitectureAttestationEvidenceKind.COMPARATOR],
            findings_digest=indexed[ArchitectureAttestationEvidenceKind.FINDINGS],
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )

from abc import ABC
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ...architecture_manifests.assertions.model import (
    ArchitectureAssertionKind,
    ArchitectureDiagramEvidence,
)
from ...architecture_manifests.evidence.model import EvidenceProviderReceipt
from ...architecture_manifests.model import (
    ArchitectureComparisonConclusion,
    ArchitectureComparisonState,
    ArchitectureContractManifest,
    ArchitectureDiagramRevision,
    ArchitectureFindingKind,
    ArchitectureFindingOwner,
    ArchitectureSemanticValue,
)
from ...contracts.model import OperatingContractRevision, OperatingContractUpdatePolicy
from ..attestations.model import ArchitectureConformanceAttestation


class ArchitectureHealthInputIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    modwire_source_digest: str
    artifact_inventory_digest: str
    provider_receipts: tuple[EvidenceProviderReceipt, ...]
    digest: str


class ArchitectureHealthContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest: ArchitectureContractManifest
    operating_contract: OperatingContractRevision
    update_policy: OperatingContractUpdatePolicy
    configuration_revision: str


class ArchitectureConformanceCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    assertion_kind: ArchitectureAssertionKind
    passed: int
    failed: int
    unverified: int


class ArchitectureConformanceEvidence(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArchitectureAssertionEvidence(ArchitectureConformanceEvidence):
    kind: Literal["assertion"] = "assertion"
    diagram_evidence: tuple[ArchitectureDiagramEvidence, ...]
    implementation_evidence_ids: tuple[str, ...]


class ArchitectureUnexpectedEvidence(ArchitectureConformanceEvidence):
    kind: Literal["unexpected"] = "unexpected"
    implementation_evidence_ids: tuple[str, ...]


class ArchitectureCoverageEvidence(ArchitectureConformanceEvidence):
    kind: Literal["coverage"] = "coverage"
    diagram_revisions: tuple[ArchitectureDiagramRevision, ...]
    assertion_kind: ArchitectureAssertionKind


class ArchitectureConformanceFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

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
    rule: str
    target: str
    message: str
    next_action: str


class ArchitectureConformanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    conclusion: ArchitectureComparisonConclusion
    coverage: tuple[ArchitectureConformanceCoverage, ...]
    findings: tuple[ArchitectureConformanceFinding, ...]
    comparison_digest: str


class ArchitectureHealthResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    healthy: bool
    reports: tuple[dict[str, JsonValue], ...]
    conformance: ArchitectureConformanceReport
    attestation: ArchitectureConformanceAttestation
    input_identity: ArchitectureHealthInputIdentity

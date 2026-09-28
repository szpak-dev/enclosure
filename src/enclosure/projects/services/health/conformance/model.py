from abc import ABC
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ...architecture_manifests.facts.model import ArchitectureDiagramEvidence, ArchitectureFactCapability
from ...architecture_manifests.model import (
    ArchitectureComparisonConclusion,
    ArchitectureComparisonState,
    ArchitectureContractManifest,
    ArchitectureDiagramRevision,
    ArchitectureFindingKind,
    ArchitectureSupportState,
)
from ...contracts.model import OperatingContractRevision, OperatingContractUpdatePolicy
from ..attestations.model import ArchitectureConformanceAttestation


class ArchitectureHealthContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest: ArchitectureContractManifest
    operating_contract: OperatingContractRevision
    update_policy: OperatingContractUpdatePolicy
    configuration_revision: str


class ArchitectureConformanceCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability: ArchitectureFactCapability
    passed: int
    failed: int
    unverified: int


class ArchitectureConformanceEvidence(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArchitectureAssertionEvidence(ArchitectureConformanceEvidence):
    kind: Literal["assertion"] = "assertion"
    diagram_evidence: tuple[ArchitectureDiagramEvidence, ...]
    source_symbol: str


class ArchitectureUnexpectedEvidence(ArchitectureConformanceEvidence):
    kind: Literal["unexpected"] = "unexpected"
    diagram_revisions: tuple[ArchitectureDiagramRevision, ...]
    source_symbol: str


class ArchitectureCoverageEvidence(ArchitectureConformanceEvidence):
    kind: Literal["coverage"] = "coverage"
    diagram_revisions: tuple[ArchitectureDiagramRevision, ...]
    capability: ArchitectureFactCapability


class ArchitectureConformanceFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fingerprint: str
    contract_unit: str
    evidence: Annotated[
        ArchitectureAssertionEvidence | ArchitectureUnexpectedEvidence | ArchitectureCoverageEvidence,
        Field(discriminator="kind"),
    ]
    expected: dict[str, JsonValue]
    actual: tuple[dict[str, JsonValue], ...]
    support: ArchitectureSupportState
    state: ArchitectureComparisonState
    finding_kind: ArchitectureFindingKind
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


class ArchitectureConformanceEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ArchitectureConformanceReport
    attestation: ArchitectureConformanceAttestation


class ArchitectureHealthResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    healthy: bool
    reports: tuple[dict[str, JsonValue], ...]
    conformance: ArchitectureConformanceReport
    attestation: ArchitectureConformanceAttestation

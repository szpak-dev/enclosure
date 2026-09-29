from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ...architecture_manifests.bindings.model import ArchitectureRealizationMap
from ...architecture_manifests.evidence.model import ImplementationEvidenceManifest
from ...architecture_manifests.model import (
    ArchitectureComparison,
    ArchitectureContractManifest,
    ArchitectureFindingKind,
    ArchitectureFindingOwner,
)
from ...contracts.model import OperatingContractRevision, OperatingContractUpdatePolicy
from .identity import ArchitectureConformanceIdentity


class ArchitectureAttestationEvidenceKind(StrEnum):
    CONTRACT = "contract"
    IMPLEMENTATION_EVIDENCE = "implementation_evidence"
    REALIZATION = "realization"
    POLICIES = "policies"
    CONFIGURATION = "configuration"
    SCHEMAS = "schemas"
    TOOLS = "tools"
    COMPARATOR = "comparator"
    FINDINGS = "findings"


class ArchitectureFindingAttestationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fingerprint: str
    owner: ArchitectureFindingOwner
    kind: ArchitectureFindingKind
    message: str
    next_action: str


class ArchitectureAttestationContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: ArchitectureContractManifest
    implementation: ImplementationEvidenceManifest
    realization: ArchitectureRealizationMap
    comparison: ArchitectureComparison
    findings: tuple[ArchitectureFindingAttestationEvidence, ...]
    operating_contract: OperatingContractRevision
    update_policy: OperatingContractUpdatePolicy
    configuration_revision: str
    identity: ArchitectureConformanceIdentity


class ArchitectureAttestationComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ArchitectureAttestationEvidenceKind
    digest: str


class ArchitectureConformanceAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    digest_algorithm: str
    components: tuple[ArchitectureAttestationComponent, ...]
    contract_digest: str
    implementation_evidence_digest: str
    realization_digest: str
    source_digest: str
    policy_digest: str
    configuration_digest: str
    schema_digest: str
    tools_digest: str
    comparator_digest: str
    findings_digest: str
    digest: str

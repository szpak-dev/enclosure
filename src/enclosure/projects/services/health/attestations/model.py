from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ...architecture_manifests.model import ArchitectureComparison, ArchitectureContractManifest
from ...architecture_manifests.observed.model import ObservedImplementationManifest
from ...contracts.model import OperatingContractRevision, OperatingContractUpdatePolicy
from .identity import ArchitectureConformanceIdentity


class ArchitectureAttestationEvidenceKind(StrEnum):
    CONTRACT = "contract"
    SOURCE = "source"
    POLICIES = "policies"
    CONFIGURATION = "configuration"
    SCHEMAS = "schemas"
    TOOLS = "tools"
    COMPARATOR = "comparator"
    FINDINGS = "findings"


class ArchitectureAttestationContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: ArchitectureContractManifest
    observed: ObservedImplementationManifest
    comparison: ArchitectureComparison
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
    source_digest: str
    policy_digest: str
    configuration_digest: str
    schema_digest: str
    tools_digest: str
    comparator_digest: str
    findings_digest: str
    digest: str

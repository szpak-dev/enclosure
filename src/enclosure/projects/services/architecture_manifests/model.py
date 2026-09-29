from abc import ABC
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, JsonValue, SerializeAsAny

from ..architecture_contracts.model import ArchitectureContractCoverage, ArchitectureContractExclusion
from .assertions.model import ArchitectureAssertion, ArchitectureAssertionKind, ArchitectureDiagramEvidence
from .bindings.model import ArchitectureRealizationMap
from .evidence.model import ImplementationEvidenceManifest


class ArchitectureComparisonState(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNVERIFIED = "unverified"


class ArchitectureAssertionScope(StrEnum):
    ASSERTION = "assertion"
    COVERAGE = "coverage"


class ArchitectureComparisonConclusion(StrEnum):
    CONFORMS = "conforms"
    DOES_NOT_CONFORM = "does_not_conform"
    UNVERIFIED = "unverified"


class ArchitectureFindingKind(StrEnum):
    MISSING = "missing"
    UNEXPECTED = "unexpected"
    MISMATCHED = "mismatched"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


class ArchitectureFindingOwner(StrEnum):
    CONTRACT = "contract"
    REALIZATION = "realization"
    IMPLEMENTATION = "implementation"
    OBSERVER = "observer"


class ArchitectureDiagramRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    diagram_revision: int


class ArchitectureContractManifestUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    source_root: str
    coverage: ArchitectureContractCoverage
    diagram_revisions: tuple[ArchitectureDiagramRevision, ...]
    exclusions: tuple[ArchitectureContractExclusion, ...]
    assertions: tuple[SerializeAsAny[ArchitectureAssertion], ...]


class ArchitectureContractManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    project_id: str
    publication_id: str
    publication_version: int
    publication_revision: str
    units: tuple[ArchitectureContractManifestUnit, ...]
    digest_algorithm: str
    digest: str


class ArchitectureSemanticValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ArchitectureAssertionKind
    fields: dict[str, JsonValue]


class ArchitectureAssertionResult(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fingerprint: str
    assertion_id: str
    unit_key: str
    assertion_kind: ArchitectureAssertionKind
    scope: ArchitectureAssertionScope
    state: ArchitectureComparisonState
    owner: ArchitectureFindingOwner
    evidence: tuple[ArchitectureDiagramEvidence, ...]
    implementation_evidence_ids: tuple[str, ...]


class ArchitectureAssertionPass(ArchitectureAssertionResult):
    evidence_id: str


class ArchitectureAssertionFailure(ArchitectureAssertionResult):
    kind: ArchitectureFindingKind
    expected: ArchitectureSemanticValue
    observed: tuple[ArchitectureSemanticValue, ...]


class ArchitectureAssertionUnverified(ArchitectureAssertionResult):
    kind: ArchitectureFindingKind
    expected: ArchitectureSemanticValue
    diagram_revisions: tuple[ArchitectureDiagramRevision, ...]
    explanation: str


class ArchitectureComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    contract_digest: str
    implementation_digest: str
    realization_digest: str
    source_digest: str
    conclusion: ArchitectureComparisonConclusion
    results: tuple[SerializeAsAny[ArchitectureAssertionResult], ...]
    passed: int
    failed: int
    unverified: int
    digest: str


class ArchitectureComparisonBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: ArchitectureContractManifest
    implementation: ImplementationEvidenceManifest
    realization: ArchitectureRealizationMap
    comparison: ArchitectureComparison

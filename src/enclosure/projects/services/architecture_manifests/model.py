from abc import ABC
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, JsonValue, SerializeAsAny

from ..architecture_contracts.model import ArchitectureContractCoverage, ArchitectureContractExclusion
from .facts.model import ArchitectureContractFact, ArchitectureDiagramEvidence, ArchitectureFactCapability


class ArchitectureComparisonState(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNVERIFIED = "unverified"


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


class ArchitectureSupportState(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"


class ArchitectureContractManifestUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    source_root: str
    coverage: ArchitectureContractCoverage
    exclusions: tuple[ArchitectureContractExclusion, ...]
    facts: tuple[SerializeAsAny[ArchitectureContractFact], ...]


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


class ArchitectureAssertionResult(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fingerprint: str
    assertion_id: str
    unit_key: str
    capability: ArchitectureFactCapability
    state: ArchitectureComparisonState
    evidence: tuple[ArchitectureDiagramEvidence, ...]


class ArchitectureAssertionPass(ArchitectureAssertionResult):
    actual_id: str


class ArchitectureAssertionFailure(ArchitectureAssertionResult):
    kind: ArchitectureFindingKind
    actual: tuple[dict[str, JsonValue], ...]


class ArchitectureExpectedFailure(ArchitectureAssertionFailure):
    expected: dict[str, JsonValue]


class ArchitectureUnexpectedFailure(ArchitectureAssertionFailure):
    pass


class ArchitectureAssertionUnverified(ArchitectureAssertionResult):
    kind: ArchitectureFindingKind
    support: ArchitectureSupportState
    explanation: str


class ArchitectureComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    contract_digest: str
    implementation_digest: str
    source_digest: str
    conclusion: ArchitectureComparisonConclusion
    results: tuple[SerializeAsAny[ArchitectureAssertionResult], ...]
    passed: int
    failed: int
    unverified: int
    digest: str

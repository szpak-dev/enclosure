from abc import ABC
from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue, SerializeAsAny

from ...architecture_contracts.model import ArchitectureContractCoverage, ArchitectureContractExclusionContract
from ..assertions.model import (
    ArchitectureArtifactKind,
    ArchitectureAssertionKind,
    ArchitectureCardinality,
    ArchitectureClassifierKind,
    ArchitectureEntityKey,
    ArchitectureMemberKind,
    ArchitectureMemberOwnership,
    ArchitectureParameter,
    ArchitectureRelationshipKind,
    ArchitectureTypeReference,
    ArchitectureVisibility,
    ArtifactAssertion,
)


class ArchitectureSupportState(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"


class EvidenceSupport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    support: ArchitectureSupportState
    explanation: str


class ImplementationContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    implementation_document: Mapping[str, JsonValue]
    artifact_inventory: "ArtifactObservationManifest"


class ArtifactObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    artifact_kind: ArchitectureArtifactKind
    exists: bool
    content_digest: str


class ArtifactObservationScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_key: str
    source_root: str
    coverage: ArchitectureContractCoverage
    exclusions: tuple[ArchitectureContractExclusionContract, ...]
    declared_artifacts: tuple[ArtifactAssertion, ...]


class ArtifactObservationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scopes: tuple[ArtifactObservationScope, ...]
    digest: str


class ArtifactObservationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    support: ArchitectureSupportState
    plan_digest: str
    observations: tuple[ArtifactObservation, ...]
    digest: str


class ProviderManifest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    provider: str
    language: str
    version: str
    source_digest: str
    payload: BaseModel


class EvidenceCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ArchitectureAssertionKind
    semantics: EvidenceSupport
    inventory: EvidenceSupport


class EvidenceProviderReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    version: str
    language: str
    source_digest: str
    capabilities: tuple[EvidenceCapability, ...]


class ImplementationLocator(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    coordinate: str
    path: str


class ImplementationEvidence(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    kind: ArchitectureAssertionKind
    locator: ImplementationLocator
    reference: str


class ArtifactEvidence(ImplementationEvidence):
    kind: Literal[ArchitectureAssertionKind.ARTIFACT] = ArchitectureAssertionKind.ARTIFACT
    path: str
    artifact_kind: ArchitectureArtifactKind
    content_digest: str


class ClassifierEvidence(ImplementationEvidence):
    kind: Literal[ArchitectureAssertionKind.CLASSIFIER] = ArchitectureAssertionKind.CLASSIFIER
    name: str
    classifier_kind: ArchitectureClassifierKind
    abstract: bool


class MemberEvidence(ImplementationEvidence):
    kind: Literal[ArchitectureAssertionKind.MEMBER] = ArchitectureAssertionKind.MEMBER
    owner_id: str
    name: str
    member_kind: ArchitectureMemberKind
    type: ArchitectureTypeReference
    visibility: ArchitectureVisibility
    ownership: ArchitectureMemberOwnership
    abstract: bool
    parameters: tuple[ArchitectureParameter, ...]


class RelationshipEvidence(ImplementationEvidence):
    kind: Literal[ArchitectureAssertionKind.RELATIONSHIP] = ArchitectureAssertionKind.RELATIONSHIP
    source_id: str
    target_reference: str
    relationship_kind: ArchitectureRelationshipKind
    source_cardinality: ArchitectureCardinality
    target_cardinality: ArchitectureCardinality


class EntityEvidence(ImplementationEvidence):
    kind: Literal[ArchitectureAssertionKind.ENTITY] = ArchitectureAssertionKind.ENTITY
    name: str


class EntityFieldEvidence(ImplementationEvidence):
    kind: Literal[ArchitectureAssertionKind.ENTITY_FIELD] = ArchitectureAssertionKind.ENTITY_FIELD
    owner_id: str
    name: str
    type: ArchitectureTypeReference
    keys: tuple[ArchitectureEntityKey, ...]
    cardinality: ArchitectureCardinality


class ImplementationEvidenceSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt: EvidenceProviderReceipt
    evidence: tuple[
        SerializeAsAny[
            ArtifactEvidence
            | ClassifierEvidence
            | MemberEvidence
            | RelationshipEvidence
            | EntityEvidence
            | EntityFieldEvidence
        ],
        ...,
    ]


class ImplementationEvidenceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    provider_receipts: tuple[EvidenceProviderReceipt, ...]
    evidence: tuple[
        SerializeAsAny[
            ArtifactEvidence
            | ClassifierEvidence
            | MemberEvidence
            | RelationshipEvidence
            | EntityEvidence
            | EntityFieldEvidence
        ],
        ...,
    ]
    source_digest: str
    digest: str

    def support(self, kind: ArchitectureAssertionKind) -> EvidenceSupport:
        return self._support(kind, "semantics")

    def inventory_support(self, kind: ArchitectureAssertionKind) -> EvidenceSupport:
        return self._support(kind, "inventory")

    def _support(self, kind: ArchitectureAssertionKind, dimension: str) -> EvidenceSupport:
        declarations = tuple(
            getattr(capability, dimension)
            for receipt in self.provider_receipts
            for capability in receipt.capabilities
            if capability.kind == kind
        )
        supported = tuple(
            declaration for declaration in declarations if declaration.support == ArchitectureSupportState.SUPPORTED
        )
        partial = tuple(
            declaration for declaration in declarations if declaration.support == ArchitectureSupportState.PARTIAL
        )
        if supported:
            return EvidenceSupport(support=ArchitectureSupportState.SUPPORTED, explanation="")
        if partial:
            return EvidenceSupport(
                support=ArchitectureSupportState.PARTIAL,
                explanation="; ".join(item.explanation for item in partial if item.explanation),
            )
        return EvidenceSupport(
            support=ArchitectureSupportState.UNSUPPORTED,
            explanation="; ".join(item.explanation for item in declarations if item.explanation),
        )

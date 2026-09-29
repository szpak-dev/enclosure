from abc import ABC
from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, JsonValue, SerializeAsAny

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
)


class ArchitectureSupportState(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"


class ImplementationContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    implementation_document: Mapping[str, JsonValue]
    artifact_paths: tuple[str, ...]


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
    support: ArchitectureSupportState
    explanation: str


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
    path: str
    artifact_kind: ArchitectureArtifactKind
    content_digest: str


class ClassifierEvidence(ImplementationEvidence):
    name: str
    classifier_kind: ArchitectureClassifierKind
    abstract: bool


class MemberEvidence(ImplementationEvidence):
    owner_id: str
    name: str
    member_kind: ArchitectureMemberKind
    type: ArchitectureTypeReference
    visibility: ArchitectureVisibility
    ownership: ArchitectureMemberOwnership
    abstract: bool
    parameters: tuple[ArchitectureParameter, ...]


class RelationshipEvidence(ImplementationEvidence):
    source_id: str
    target_reference: str
    relationship_kind: ArchitectureRelationshipKind
    source_cardinality: ArchitectureCardinality
    target_cardinality: ArchitectureCardinality


class EntityEvidence(ImplementationEvidence):
    name: str


class EntityFieldEvidence(ImplementationEvidence):
    owner_id: str
    name: str
    type: ArchitectureTypeReference
    keys: tuple[ArchitectureEntityKey, ...]
    cardinality: ArchitectureCardinality


class ImplementationEvidenceSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt: EvidenceProviderReceipt
    evidence: tuple[SerializeAsAny[ImplementationEvidence], ...]


class ImplementationEvidenceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    provider_receipts: tuple[EvidenceProviderReceipt, ...]
    evidence: tuple[SerializeAsAny[ImplementationEvidence], ...]
    source_digest: str
    digest: str

    def support(self, kind: ArchitectureAssertionKind) -> EvidenceCapability:
        declarations = tuple(
            capability
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
            return EvidenceCapability(kind=kind, support=ArchitectureSupportState.SUPPORTED, explanation="")
        if partial:
            return EvidenceCapability(
                kind=kind,
                support=ArchitectureSupportState.PARTIAL,
                explanation="; ".join(item.explanation for item in partial if item.explanation),
            )
        return EvidenceCapability(
            kind=kind,
            support=ArchitectureSupportState.UNSUPPORTED,
            explanation="; ".join(item.explanation for item in declarations if item.explanation),
        )

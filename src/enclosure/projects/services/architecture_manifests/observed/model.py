from abc import ABC

from pydantic import BaseModel, ConfigDict, SerializeAsAny

from ..facts.model import ArchitectureFactCapability, ArchitectureRelationKind
from ..model import ArchitectureSupportState


class ObservedCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability: ArchitectureFactCapability
    support: ArchitectureSupportState
    explanation: str


class ObservedImplementationFact(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    capability: ArchitectureFactCapability


class ObservedSourceFact(ObservedImplementationFact):
    path: str
    content_digest: str


class ObservedSymbolFact(ObservedImplementationFact):
    path: str
    family: str
    qualified_name: str
    visibility: str


class ObservedCallableFact(ObservedImplementationFact):
    owner_id: str
    callable_kind: str


class ObservedParameterFact(ObservedImplementationFact):
    owner_id: str
    position: int
    name: str
    kind: str
    has_default: bool
    annotations: tuple[str, ...]


class ObservedAttributeFact(ObservedImplementationFact):
    owner_id: str
    name: str
    optional: bool
    annotation: str
    visibility: str
    member_kind: str


class ObservedAnnotationFact(ObservedImplementationFact):
    target_id: str
    role: str
    expression: str


class ObservedInheritanceFact(ObservedImplementationFact):
    owner_id: str
    kind: ArchitectureRelationKind
    target: str


class ObservedDependencyFact(ObservedImplementationFact):
    source_path: str
    kind: ArchitectureRelationKind
    target: str
    target_kind: str
    specifier: str
    resolution: str


class ObservedImplementationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    document_digest: str
    source_digest: str
    modwire_version: str
    extractor_id: str
    language: str
    capabilities: tuple[ObservedCapability, ...]
    facts: tuple[SerializeAsAny[ObservedImplementationFact], ...]

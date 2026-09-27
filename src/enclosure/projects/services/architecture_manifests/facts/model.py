from abc import ABC
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ArchitectureFactCapability(StrEnum):
    SOURCES = "sources"
    SYMBOLS = "symbols"
    CALLABLES = "callables"
    PARAMETERS = "parameters"
    ANNOTATIONS = "annotations"
    MODIFIERS = "modifiers"
    ATTRIBUTES = "attributes"
    INHERITANCE = "inheritance"
    DEPENDENCIES = "dependencies"
    SPANS = "spans"


class ArchitectureDiagramEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    diagram_revision: int
    element_id: str


class ArchitectureContractFact(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    capability: ArchitectureFactCapability
    required: bool
    evidence: tuple[ArchitectureDiagramEvidence, ...]


class SourceContractFact(ArchitectureContractFact):
    path: str


class SymbolContractFact(ArchitectureContractFact):
    path: str
    family: str
    qualified_name: str
    kind: str


class CallableContractFact(ArchitectureContractFact):
    owner_id: str
    callable_kind: str


class ParameterContractFact(ArchitectureContractFact):
    owner_id: str
    position: int
    name: str
    annotation: str


class AttributeContractFact(ArchitectureContractFact):
    owner_id: str
    name: str
    optional: bool


class AnnotationContractFact(ArchitectureContractFact):
    target_id: str
    role: str
    expression: str


class ModifierContractFact(ArchitectureContractFact):
    target_id: str
    role: str
    value: str


class InheritanceContractFact(ArchitectureContractFact):
    owner_id: str
    kind: str
    target: str


class DependencyContractFact(ArchitectureContractFact):
    source_path: str
    kind: str
    target: str
    specifier: str
    resolution: str

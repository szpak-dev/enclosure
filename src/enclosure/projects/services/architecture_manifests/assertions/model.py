from abc import ABC
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ArchitectureAssertionKind(StrEnum):
    ARTIFACT = "artifact"
    CLASSIFIER = "classifier"
    MEMBER = "member"
    RELATIONSHIP = "relationship"
    ENTITY = "entity"
    ENTITY_FIELD = "entity_field"


class ArchitectureCardinality(StrEnum):
    ONE = "one"
    OPTIONAL = "optional"
    MANY = "many"
    NONEMPTY_MANY = "nonempty_many"


class ArchitectureArtifactKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"


class ArchitectureClassifierKind(StrEnum):
    CLASS = "class"
    INTERFACE = "interface"
    ENUMERATION = "enumeration"


class ArchitectureMemberKind(StrEnum):
    PROPERTY = "property"
    OPERATION = "operation"


class ArchitectureMemberOwnership(StrEnum):
    INSTANCE = "instance"
    TYPE = "type"


class ArchitectureVisibility(StrEnum):
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    PACKAGE = "package"


class ArchitectureRelationshipKind(StrEnum):
    ASSOCIATION = "association"
    GENERALIZATION = "generalization"
    COMPOSITION = "composition"
    AGGREGATION = "aggregation"
    DEPENDENCY = "dependency"
    REALIZATION = "realization"
    IDENTIFYING = "identifying"
    NON_IDENTIFYING = "non_identifying"


class ArchitectureEntityKey(StrEnum):
    PRIMARY = "primary"
    FOREIGN = "foreign"
    UNIQUE = "unique"


class ArchitectureTypeReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    arguments: tuple["ArchitectureTypeReference", ...]
    cardinality: ArchitectureCardinality


class ArchitectureParameter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    position: int
    type: ArchitectureTypeReference


class ArchitectureDiagramEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    diagram_revision: int
    element_id: str


class ArchitectureAssertion(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    unit_key: str
    subject_id: str
    kind: ArchitectureAssertionKind
    required: bool
    evidence: tuple[ArchitectureDiagramEvidence, ...]


class ArtifactAssertion(ArchitectureAssertion):
    path: str
    artifact_kind: ArchitectureArtifactKind


class ClassifierAssertion(ArchitectureAssertion):
    name: str
    classifier_kind: ArchitectureClassifierKind
    abstract: bool


class MemberAssertion(ArchitectureAssertion):
    owner_id: str
    name: str
    member_kind: ArchitectureMemberKind
    type: ArchitectureTypeReference
    visibility: ArchitectureVisibility
    ownership: ArchitectureMemberOwnership
    abstract: bool
    parameters: tuple[ArchitectureParameter, ...]


class RelationshipAssertion(ArchitectureAssertion):
    source_id: str
    target_id: str
    relationship_kind: ArchitectureRelationshipKind
    source_cardinality: ArchitectureCardinality
    target_cardinality: ArchitectureCardinality


class EntityAssertion(ArchitectureAssertion):
    name: str


class EntityFieldAssertion(ArchitectureAssertion):
    owner_id: str
    name: str
    type: ArchitectureTypeReference
    keys: tuple[ArchitectureEntityKey, ...]
    cardinality: ArchitectureCardinality

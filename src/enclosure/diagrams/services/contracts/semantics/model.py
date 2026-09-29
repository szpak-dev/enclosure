from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DiagramContractCardinality(StrEnum):
    ONE = "one"
    OPTIONAL = "optional"
    MANY = "many"
    NONEMPTY_MANY = "nonempty_many"


class DiagramContractType(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    arguments: tuple["DiagramContractType", ...]
    cardinality: DiagramContractCardinality


class DiagramContractParameter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    type: DiagramContractType
    position: int


class DiagramContractMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    kind: str
    type: DiagramContractType
    visibility: str
    modifier: str
    parameters: tuple[DiagramContractParameter, ...]
    keys: tuple[str, ...]
    cardinality: DiagramContractCardinality


class DiagramContractPath(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    element_id: str
    path: str
    kind: str


class DiagramContractSymbol(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    element_id: str
    label: str
    kind: str
    annotations: tuple[str, ...]
    members: tuple[DiagramContractMember, ...]


class DiagramContractRelation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    source_id: str
    target_id: str
    kind: str
    label: str
    source_cardinality: DiagramContractCardinality
    target_cardinality: DiagramContractCardinality
    identifying: bool


class DiagramContractSemantics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    paths: tuple[DiagramContractPath, ...]
    symbols: tuple[DiagramContractSymbol, ...]
    relations: tuple[DiagramContractRelation, ...]

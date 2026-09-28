from pydantic import BaseModel, ConfigDict


class DiagramContractParameter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    type: str
    position: int


class DiagramContractMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    kind: str
    type: str
    visibility: str
    modifier: str
    parameters: tuple[DiagramContractParameter, ...]


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


class DiagramContractSemantics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    paths: tuple[DiagramContractPath, ...]
    symbols: tuple[DiagramContractSymbol, ...]
    relations: tuple[DiagramContractRelation, ...]

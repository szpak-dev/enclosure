from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ArchitectureDiagramRole(StrEnum):
    TREE = "tree"
    UML = "uml"
    ENTITY = "entity"


class ArchitectureDiagramScope(StrEnum):
    COMPLETE = "complete"
    FOCUSED = "focused"
    REFERENCE = "reference"


class ArchitectureContractCoverage(StrEnum):
    CLOSED = "closed"
    DECLARED = "declared"


class ArchitectureContractDiagramInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    expected_revision: int
    role: ArchitectureDiagramRole
    scope: ArchitectureDiagramScope


class ArchitectureContractExclusionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    reason: str


class ArchitectureContractUnitInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    diagram_set_id: str
    source_root: str
    coverage: ArchitectureContractCoverage
    diagrams: tuple[ArchitectureContractDiagramInput, ...] = Field(min_length=1)
    exclusions: tuple[ArchitectureContractExclusionInput, ...]


class PublishArchitectureContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    units: tuple[ArchitectureContractUnitInput, ...] = Field(min_length=1)


class ArchitectureContractDiagramContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    diagram_id: str
    diagram_revision: int
    role: ArchitectureDiagramRole
    scope: ArchitectureDiagramScope
    kind: str
    snapshot_version: int
    registry_fingerprint: str
    snapshot_digest: str
    snapshot: dict[str, JsonValue]


class ArchitectureContractDiagram(ArchitectureContractDiagramContract):
    id: str
    position: int


class ArchitectureContractExclusionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    reason: str


class ArchitectureContractExclusion(ArchitectureContractExclusionContract):
    id: str
    position: int


class ArchitectureContractUnitContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    diagram_set_id: str
    source_root: str
    coverage: ArchitectureContractCoverage
    diagrams: tuple[ArchitectureContractDiagramContract, ...] = Field(min_length=1)
    exclusions: tuple[ArchitectureContractExclusionContract, ...]


class ArchitectureContractUnit(ArchitectureContractUnitContract):
    id: str
    position: int
    diagrams: tuple[ArchitectureContractDiagram, ...] = Field(min_length=1)
    exclusions: tuple[ArchitectureContractExclusion, ...]


class ArchitectureContractCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    authority: str
    revision: str
    units: tuple[ArchitectureContractUnitContract, ...] = Field(min_length=1)


class ArchitectureContractPublication(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    project_id: str
    version: int
    authority: str
    revision: str
    units: tuple[ArchitectureContractUnit, ...] = Field(min_length=1)

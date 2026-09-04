from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    language_id: str
    language_version: str
    package_manager_id: str
    scaffolding_id: str


class ArchitectureConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    project_id: str
    revision: str
    boundaries_yaml: str
    shape_yaml: str


class ArchitectureConfigurationDocument(StrEnum):
    BOUNDARIES = "boundaries_yaml"
    SHAPE = "shape_yaml"


class ArchitectureConfigurationContent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    configuration_id: str
    revision: str
    document: ArchitectureConfigurationDocument
    offset: int
    limit: int
    total_characters: int
    content: str
    has_more: bool
    next_offset: int

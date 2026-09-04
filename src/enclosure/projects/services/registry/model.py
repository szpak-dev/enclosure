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
    boundaries_yaml: str
    shape_yaml: str

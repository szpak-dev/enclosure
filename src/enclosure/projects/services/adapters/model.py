from pydantic import BaseModel, ConfigDict


class WorkspaceGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    summary: str
    authority: str
    revision: str
    schema_revision: int
    current_schema_revision: int
    applies_when: tuple[str, ...]
    guidance: tuple[str, ...]
    checks: tuple[str, ...]


class WorkspaceGuidanceResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    guidance: tuple[WorkspaceGuidance, ...]
    selected_ids: tuple[str, ...]
    missing_ids: tuple[str, ...]

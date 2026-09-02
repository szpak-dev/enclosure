from typing import Annotated, Literal

from ninja import Schema
from pydantic import Field, JsonValue

from ..services.stack import DiscoveredProject

ProjectId = Annotated[str, Field(description="Project identifier.")]


class DiscoverProject(Schema):
    root: str = Field(description="Absolute path to the project directory.")


class FindProjectByRoot(Schema):
    root: str = Field(description="Absolute path to the registered project directory.")


class GetWorkspaceContext(Schema):
    root: str = Field(description="Absolute path to the registered project directory.")
    task: str = Field(description="Current task used to select relevant project guidance.")


class WorkspaceGuidance(Schema):
    id: str = Field(description="Guidance record identifier.")
    title: str = Field(description="Guidance title.")
    summary: str = Field(description="Compact statement of the guidance purpose.")
    authority: str = Field(description="Stable authority claimed by this guidance source.")
    revision: str = Field(description="Deterministic revision of the resolved guidance source.")
    schema_revision: int = Field(description="Category schema revision assigned to this guidance source.", ge=1)
    current_schema_revision: int = Field(description="Current category schema revision.", ge=1)
    applies_when: list[str] = Field(description="Situations in which the guidance applies.")
    guidance: list[str] = Field(description="Constraints applicable to the task.")
    checks: list[str] = Field(description="Checks required before handoff.")


class WorkspaceAuthority(Schema):
    kind: Literal["project-record-bindings"] = Field(description="Authority mechanism used for this response.")
    id: str = Field(description="Stable identifier of the effective authority.")
    revision: str = Field(description="Deterministic revision of the effective authority.")


class WorkspaceContextDiagnostic(Schema):
    code: str = Field(description="Stable machine-readable readiness diagnostic code.")
    message: str = Field(description="Actionable explanation of the readiness problem.")
    guidance_ids: list[str] = Field(description="Bound guidance records affected by the diagnostic.")


class WorkspaceContext(Schema):
    project_id: ProjectId
    root: str = Field(description="Registered project root.")
    readiness: Literal["ready", "incomplete", "conflicted"] = Field(
        description="Whether the returned context is safe to treat as complete."
    )
    authority: WorkspaceAuthority = Field(description="Authority and revision used to resolve this response.")
    guidance: list[WorkspaceGuidance] = Field(description="Relevant linked guidance, ordered by task relevance.")
    diagnostics: list[WorkspaceContextDiagnostic] = Field(
        description="Stable reasons the response is incomplete or conflicted."
    )


class RegisterProject(Schema):
    discovery: DiscoveredProject = Field(description="Detected project root and technology stack.")
    architecture_root: str = Field(description="Absolute path analyzed by the architecture rules.")
    boundaries_yaml: str = Field(description="Modwire boundary configuration in YAML.")
    shape_yaml: str = Field(description="Modwire architecture-shape configuration in YAML.")
    scaffolding_id: str = Field(description="Identifier of the scaffolding used to generate project source code.")
    record_ids: list[str] = Field(description="Identifiers of records that provide project context.")


class GenerateProjectSource(Schema):
    destination: str = Field(
        description="Destination directory relative to the registered project root.",
        min_length=1,
    )
    parameters: dict[str, JsonValue] = Field(description="Values for the associated scaffolding variables.")


class GeneratedProjectSource(Schema):
    files: tuple[str, ...] = Field(description="Written file paths relative to the registered project root.")


class ProjectReference(Schema):
    id: ProjectId
    root: str = Field(description="Absolute path to the project directory.")


class Project(Schema):
    id: ProjectId
    root: str = Field(description="Absolute path to the project directory.")
    architecture_root: str = Field(description="Absolute path analyzed by the architecture rules.")
    language_id: str = Field(description="Detected programming-language identifier.")
    language_version: str = Field(description="Detected programming-language version, when available.")
    package_manager_id: str = Field(description="Detected package-manager identifier.")
    scaffolding_id: str = Field(description="Identifier of the scaffolding used to generate project source code.")


class ProjectArchitectureConfigurationReference(Schema):
    id: str = Field(description="Architecture configuration identifier within the project.")
    project_id: ProjectId


class ProjectArchitectureConfiguration(ProjectArchitectureConfigurationReference):
    boundaries_yaml: str = Field(description="Modwire boundary configuration in YAML.")
    shape_yaml: str = Field(description="Modwire architecture-shape configuration in YAML.")


class HealthReport(Schema):
    healthy: bool = Field(description="Whether all gating architecture rules pass.")
    reports: tuple[dict[str, JsonValue], ...] = Field(description="Results from gating architecture rules.")


class InsightsReport(Schema):
    reports: tuple[dict[str, JsonValue], ...] = Field(description="Results from non-gating architecture rules.")

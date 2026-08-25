from typing import Annotated

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
    applies_when: list[str] = Field(description="Situations in which the guidance applies.")
    guidance: list[str] = Field(description="Constraints applicable to the task.")
    checks: list[str] = Field(description="Checks required before handoff.")


class WorkspaceContext(Schema):
    project_id: ProjectId
    root: str = Field(description="Registered project root.")
    guidance: list[WorkspaceGuidance] = Field(description="Relevant linked guidance, ordered by task relevance.")


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


class ProjectArchitectureConfiguration(Schema):
    boundaries_yaml: str = Field(description="Modwire boundary configuration in YAML.")
    shape_yaml: str = Field(description="Modwire architecture-shape configuration in YAML.")


class HealthReport(Schema):
    healthy: bool = Field(description="Whether all gating architecture rules pass.")
    reports: tuple[dict[str, JsonValue], ...] = Field(description="Results from gating architecture rules.")


class InsightsReport(Schema):
    reports: tuple[dict[str, JsonValue], ...] = Field(description="Results from non-gating architecture rules.")

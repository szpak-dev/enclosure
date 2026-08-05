from typing import Annotated

from ninja import Schema
from pydantic import Field, JsonValue

from ..services.stack import DiscoveredProject

ProjectId = Annotated[str, Field(description="Project identifier.")]


class DiscoverProject(Schema):
    root: str = Field(description="Absolute path to the project directory.")


class RegisterProject(Schema):
    discovery: DiscoveredProject = Field(description="Detected project root and technology stack.")
    architecture_root: str = Field(description="Absolute path analyzed by the architecture rules.")
    boundaries_yaml: str = Field(description="Modwire boundary configuration in YAML.")
    shape_yaml: str = Field(description="Modwire architecture-shape configuration in YAML.")
    scaffolding_id: str = Field(description="Identifier of the scaffolding used to generate project source code.")
    record_ids: list[str] = Field(description="Identifiers of records that provide project context.")


class Project(Schema):
    id: ProjectId
    root: str = Field(description="Absolute path to the project directory.")
    architecture_root: str = Field(description="Absolute path analyzed by the architecture rules.")
    language_id: str = Field(description="Detected programming-language identifier.")
    language_version: str = Field(description="Detected programming-language version, when available.")
    package_manager_id: str = Field(description="Detected package-manager identifier.")
    boundaries_yaml: str = Field(description="Modwire boundary configuration in YAML.")
    shape_yaml: str = Field(description="Modwire architecture-shape configuration in YAML.")
    scaffolding_id: str = Field(description="Identifier of the scaffolding used to generate project source code.")


class HealthReport(Schema):
    healthy: bool = Field(description="Whether all gating architecture rules pass.")
    reports: tuple[dict[str, JsonValue], ...] = Field(description="Results from gating architecture rules.")


class InsightsReport(Schema):
    reports: tuple[dict[str, JsonValue], ...] = Field(description="Results from non-gating architecture rules.")

from datetime import datetime
from typing import Annotated, Literal

from ninja import Schema
from pydantic import ConfigDict, Field, JsonValue

DiagramId = Annotated[str, Field(description="Diagram identifier.")]
DiagramSetId = Annotated[str, Field(description="Diagram set identifier.")]
DiagramKindId = Annotated[str, Field(description="Mermaiden diagram-kind identifier.")]


class StrictSchema(Schema):
    model_config = ConfigDict(extra="forbid")


class DiagramKind(Schema):
    id: DiagramKindId
    name: str = Field(description="Human-readable diagram-kind name.")


class DiagramKindDescription(DiagramKind):
    elements: dict[str, dict[str, JsonValue]] = Field(
        description="Element kinds and their JSON Schemas."
    )
    relations: dict[str, dict[str, JsonValue]] = Field(
        description="Relation kinds and their JSON Schemas."
    )
    annotations: dict[str, dict[str, JsonValue]] = Field(
        description="Annotation kinds and their JSON Schemas."
    )
    commands: dict[str, dict[str, JsonValue]] = Field(
        description="Available commands keyed by operation name, with their argument JSON Schemas."
    )


class DiagramCommandSchema(Schema):
    kind: DiagramKindId
    operation: str = Field(description="Command operation name.")
    arguments_schema: dict[str, JsonValue] = Field(description="JSON Schema for the command arguments.")


class CreateDiagramSet(StrictSchema):
    title: str = Field(description="Human-readable diagram-set title.", min_length=1, max_length=255)
    description: str = Field(default="", description="Purpose and topic of the diagram set.")


class UpdateDiagramSet(StrictSchema):
    title: str | None = Field(
        default=None,
        description="Replacement diagram-set title when supplied.",
        min_length=1,
        max_length=255,
    )
    description: str | None = Field(
        default=None,
        description="Replacement diagram-set description when supplied.",
    )


class CreateDiagram(StrictSchema):
    title: str = Field(description="Human-readable diagram title.", min_length=1, max_length=255)
    kind: DiagramKindId = Field(description="Mermaiden diagram kind used to create the diagram.", max_length=64)


class ApplyDiagramCommand(StrictSchema):
    expected_revision: int = Field(
        description="Diagram revision on which the command is based.",
        ge=1,
    )
    operation: str = Field(description="Mermaiden command operation name.", min_length=1)
    arguments: dict[str, JsonValue] = Field(description="Arguments validated against the command schema.")


class NavigateInteraction(StrictSchema):
    action: Literal["navigate"] = Field(description="Navigate to an application-relative destination.")
    target: str = Field(description="Application-relative destination opened when the element is activated.")


class ShowDetailsInteraction(StrictSchema):
    action: Literal["show_details"] = Field(description="Show structured details for the activated element.")
    payload: dict[str, JsonValue] = Field(description="Details shown when the element is activated.")


Interaction = Annotated[
    NavigateInteraction | ShowDetailsInteraction,
    Field(discriminator="action"),
]


class UpdateDiagramInteractions(StrictSchema):
    expected_revision: int = Field(
        description="Diagram revision on which the interaction update is based.",
        ge=1,
    )
    interactions: dict[str, Interaction] = Field(
        description="Declarative browser interactions keyed by diagram element identifier."
    )


class DiagramSummary(Schema):
    id: DiagramId
    diagram_set_id: DiagramSetId
    title: str = Field(description="Human-readable diagram title.")
    kind: DiagramKindId
    revision: int = Field(description="Current optimistic-concurrency revision.", ge=1)
    created_at: datetime = Field(description="Time at which the diagram was created.")
    updated_at: datetime = Field(description="Time at which the diagram was last updated.")


class Diagram(DiagramSummary):
    snapshot: dict[str, JsonValue] = Field(description="Canonical versioned Mermaiden snapshot.")
    source: str = Field(description="Mermaid source generated from the canonical snapshot.")
    interactions: dict[str, Interaction] = Field(
        description="Declarative browser interactions keyed by diagram element identifier."
    )


class DiagramSetSummary(Schema):
    id: DiagramSetId
    title: str = Field(description="Human-readable diagram-set title.")
    description: str = Field(description="Purpose and topic of the diagram set.")
    created_at: datetime = Field(description="Time at which the diagram set was created.")
    updated_at: datetime = Field(description="Time at which the diagram set was last updated.")


class DiagramSet(DiagramSetSummary):
    pass

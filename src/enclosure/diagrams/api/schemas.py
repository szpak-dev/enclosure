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
    elements: dict[str, dict[str, JsonValue]] = Field(description="Element kinds and their JSON Schemas.")
    relations: dict[str, dict[str, JsonValue]] = Field(description="Relation kinds and their JSON Schemas.")
    annotations: dict[str, dict[str, JsonValue]] = Field(description="Annotation kinds and their JSON Schemas.")
    placements: dict[str, dict[str, JsonValue]] = Field(
        description="Element kinds and the parent kinds in which they may be placed."
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


class UpdateDiagram(StrictSchema):
    expected_revision: int = Field(
        description="Diagram revision on which the metadata update is based.",
        ge=1,
    )
    title: str = Field(description="Replacement diagram title.", min_length=1, max_length=255)


class ApplyDiagramCommand(StrictSchema):
    expected_revision: int = Field(
        description="Diagram revision on which the command is based.",
        ge=1,
    )
    operation: str = Field(description="Mermaiden command operation name.", min_length=1)
    arguments: dict[str, JsonValue] = Field(description="Arguments validated against the command schema.")


class DiagramCommand(StrictSchema):
    operation: str = Field(description="Mermaiden command operation name.", min_length=1)
    arguments: dict[str, JsonValue] = Field(description="Arguments validated against the command schema.")


class CreateDiagramBatch(CreateDiagram):
    commands: list[DiagramCommand] = Field(
        description="Ordered semantic commands applied atomically while creating the diagram.",
        min_length=1,
        max_length=1000,
    )


class ApplyDiagramCommandBatch(StrictSchema):
    expected_revision: int = Field(
        description="Diagram revision on which the ordered command batch is based.",
        ge=1,
    )
    commands: list[DiagramCommand] = Field(
        description="Ordered semantic commands applied atomically to one diagram.",
        min_length=1,
        max_length=1000,
    )


class DiagramCommandBatchReceipt(Schema):
    diagram_id: DiagramId
    revision: int = Field(description="Resulting optimistic-concurrency revision.", ge=1)
    applied_count: int = Field(description="Number of commands applied by the accepted batch.", ge=1, le=1000)


class DiagramReference(Schema):
    id: DiagramId
    title: str = Field(description="Human-readable diagram title.")
    kind: DiagramKindId
    revision: int = Field(description="Current optimistic-concurrency revision.", ge=1)


class DiagramSummary(DiagramReference):
    diagram_set_id: DiagramSetId
    created_at: datetime = Field(description="Time at which the diagram was created.")
    updated_at: datetime = Field(description="Time at which the diagram was last updated.")


class Diagram(DiagramSummary):
    snapshot: dict[str, JsonValue] = Field(description="Canonical versioned Mermaiden snapshot.")
    source: str = Field(description="Mermaid source generated from the canonical snapshot.")


class ReadDiagramContent(Schema):
    document: Literal["source", "snapshot"] = Field(description="Diagram document to read.")
    expected_revision: int = Field(description="Diagram revision on which this read is based.", ge=1)
    offset: int = Field(description="Character offset at which the bounded read starts.", ge=0)
    limit: int = Field(description="Maximum characters returned by the bounded read.", ge=1, le=512)


class DiagramContent(Schema):
    diagram_id: DiagramId
    revision: int = Field(description="Diagram revision used for this read.", ge=1)
    document: Literal["source", "snapshot"] = Field(description="Diagram document that was read.")
    offset: int = Field(description="Character offset at which this page starts.", ge=0)
    limit: int = Field(description="Maximum characters requested for this page.", ge=1)
    total_characters: int = Field(description="Total characters in the selected document.", ge=0)
    content: str = Field(description="Bounded diagram content.")
    has_more: bool = Field(description="Whether another bounded page remains.")
    next_offset: int = Field(description="Character offset for the next read.", ge=0)


class DiagramSetSummary(Schema):
    id: DiagramSetId
    title: str = Field(description="Human-readable diagram-set title.")
    description: str = Field(description="Purpose and topic of the diagram set.")
    created_at: datetime = Field(description="Time at which the diagram set was created.")
    updated_at: datetime = Field(description="Time at which the diagram set was last updated.")


class DiagramSet(DiagramSetSummary):
    pass


class FindPage(Schema):
    offset: int = Field(default=0, description="Item offset at which the page starts.", ge=0)
    limit: int = Field(default=50, description="Maximum items returned by the page.", ge=1, le=100)


class DiagramSetPage(Schema):
    items: list[DiagramSetSummary] = Field(description="Diagram-set summaries in this bounded page.")
    has_more: bool = Field(description="Whether another page of diagram sets remains.")
    next_offset: int = Field(description="Item offset for the next page.", ge=0)
    limit: int = Field(description="Maximum items requested for this page.", ge=1, le=100)


class DiagramPage(Schema):
    items: list[DiagramReference] = Field(description="Diagram references in this bounded page.")
    has_more: bool = Field(description="Whether another page of diagrams remains.")
    next_offset: int = Field(description="Item offset for the next page.", ge=0)
    limit: int = Field(description="Maximum items requested for this page.", ge=1, le=100)

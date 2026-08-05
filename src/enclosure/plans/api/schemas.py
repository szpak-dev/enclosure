from typing import Annotated, Any
from uuid import UUID

from ninja import Schema
from pydantic import ConfigDict, Field

PlanRunId = Annotated[UUID, Field(description="Plan run identifier.")]


class StrictSchema(Schema):
    model_config = ConfigDict(extra="forbid")


class ArtifactDefinitionInput(Schema):
    id: str = Field(description="Artifact identifier within the plan definition.")
    producer_operation_id: str = Field(description="Identifier of the operation that produces the artifact.")
    output_schema: dict[str, Any] = Field(description="JSON Schema used to validate the artifact payload.")


class GateDefinitionInput(Schema):
    id: str = Field(description="Gate identifier within the plan definition.")
    stage_id: str = Field(description="Identifier of the stage guarded by the gate.")
    evidence_schema: dict[str, Any] = Field(description="JSON Schema used to validate gate evidence.")


class GateSatisfactionInput(Schema):
    evidence: dict[str, Any] = Field(description="Evidence validated against the gate's schema.")


class OperationDefinitionInput(Schema):
    id: str = Field(description="Operation identifier within the plan definition.")
    stage_id: str = Field(description="Identifier of the stage that exposes the operation.")
    extension_key: str = Field(description="Key of the extension that implements the operation.")
    extension_version: int = Field(description="Required version of the operation extension.")
    configuration: dict[str, Any] = Field(description="Extension-specific operation configuration.")
    input_schema: dict[str, Any] = Field(description="JSON Schema used to validate operation input.")
    output_schema: dict[str, Any] = Field(description="JSON Schema used to validate operation output.")
    produced_artifact_id: str = Field(description="Identifier of the artifact produced by the operation.")
    required_artifact_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers of artifacts required by the operation.",
    )


class StageDefinitionInput(Schema):
    id: str = Field(description="Stage identifier within the plan definition.")
    input_schema: dict[str, Any] = Field(description="JSON Schema used to validate stage input.")
    submission_schema: dict[str, Any] = Field(description="JSON Schema used to validate stage submissions.")


class StageSubmissionInput(Schema):
    payload: dict[str, Any] = Field(description="Result validated against the active stage's submission schema.")


class TransitionDefinitionInput(Schema):
    source_stage_id: str = Field(description="Identifier of the stage where the transition begins.")
    target_stage_id: str = Field(description="Identifier of the stage where the transition ends.")


class PlanDefinitionInput(StrictSchema):
    name: str = Field(description="Human-readable plan name.")
    start_stage_id: str = Field(description="Identifier of the first stage in each plan run.")
    stages: list[StageDefinitionInput] = Field(description="Stages available in the plan.")
    transitions: list[TransitionDefinitionInput] = Field(description="Allowed transitions between stages.")
    gates: list[GateDefinitionInput] = Field(description="Evidence gates that guard stages.")
    operations: list[OperationDefinitionInput] = Field(description="Operations available during plan runs.")
    artifacts: list[ArtifactDefinitionInput] = Field(
        default_factory=list,
        description="Artifacts produced and consumed by plan operations.",
    )


class PlanDefinitionOutput(Schema):
    id: str = Field(description="Published plan definition identifier.")
    version: int = Field(description="Immutable plan definition version.")
    start_stage_id: str = Field(description="Identifier of the first stage in each plan run.")


class PlanRunInput(Schema):
    definition_id: str = Field(description="Identifier of the published plan definition to run.")
    initial_input: dict[str, Any] = Field(description="Input validated against the plan's starting stage schema.")


class PlanRunOutput(Schema):
    id: PlanRunId
    current_stage_id: str = Field(description="Identifier of the run's active stage.")
    status: str = Field(description="Current plan run status.")

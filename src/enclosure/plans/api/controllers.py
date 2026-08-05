from typing import Annotated, Any
from uuid import UUID

from modwire_hex.django import DjangoRequest
from ninja import Path
from ninja_extra import ControllerBase, api_controller, route

from ...domain.artifact.artifact_definition import ArtifactDefinition
from ...domain.definition.stage_definition import StageDefinition
from ...domain.definition.transition_definition import TransitionDefinition
from ...domain.gate.gate_definition import GateDefinition
from ...domain.operation.operation_definition import OperationDefinition
from ..use_cases.execute_stage_operation import ExecuteStageOperation
from ..use_cases.publish_plan_definition import PublishPlanDefinition
from ..use_cases.satisfy_stage_gate import SatisfyStageGate
from ..use_cases.start_plan_run import StartPlanRun
from ..use_cases.submit_stage_result import SubmitStageResult
from .schemas import (
    GateSatisfactionInput,
    PlanDefinitionInput,
    PlanDefinitionOutput,
    PlanRunInput,
    PlanRunOutput,
    StageSubmissionInput,
)


@api_controller("/plans/runs", tags=["plans"])
class ExecuteStageOperationController(ControllerBase):
    @route.post(
        "/{run_id}/operations/{operation_id}",
        response={204: None},
        operation_id="execute_plan_run_operation",
        summary="Execute a plan operation",
        description="Execute an available operation for the active stage of a plan run.",
    )
    def execute(
        self,
        request: Any,
        run_id: Annotated[UUID, Path(description="Plan run identifier.")],
        operation_id: Annotated[str, Path(description="Plan operation identifier.")],
    ) -> int:
        DjangoRequest.resolve(request, ExecuteStageOperation).execute(run_id, operation_id)
        return 204


@api_controller("/plans/definitions", tags=["plans"])
class PublishDefinitionController(ControllerBase):
    @route.post(
        "",
        response={201: PlanDefinitionOutput},
        operation_id="publish_plan_definition",
        summary="Publish a plan definition",
        description="Publish an immutable version of a plan definition.",
    )
    def publish(self, request: Any, payload: PlanDefinitionInput) -> tuple[int, PlanDefinitionOutput]:
        stages = [StageDefinition(stage.id, stage.input_schema, stage.submission_schema) for stage in payload.stages]
        transitions = [TransitionDefinition(item.source_stage_id, item.target_stage_id) for item in payload.transitions]
        gates = [GateDefinition(item.id, item.stage_id, item.evidence_schema) for item in payload.gates]
        operations = [
            OperationDefinition(
                item.id,
                item.stage_id,
                item.extension_key,
                item.extension_version,
                item.configuration,
                item.input_schema,
                item.output_schema,
                item.produced_artifact_id,
                tuple(item.required_artifact_ids),
            )
            for item in payload.operations
        ]
        artifacts = [
            ArtifactDefinition(item.id, item.producer_operation_id, item.output_schema) for item in payload.artifacts
        ]
        definition = DjangoRequest.resolve(request, PublishPlanDefinition).execute(
            payload.name, payload.start_stage_id, stages, transitions, gates, operations, artifacts
        )
        return 201, PlanDefinitionOutput(
            id=str(definition.identifier), version=definition.version, start_stage_id=definition.start_stage_id
        )


@api_controller("/plans/runs", tags=["plans"])
class SatisfyStageGateController(ControllerBase):
    @route.post(
        "/{run_id}/gates/{gate_id}/satisfactions",
        response={204: None},
        operation_id="satisfy_stage_gate",
        summary="Satisfy a stage gate",
        description="Record evidence that satisfies a gate for a plan run.",
    )
    def satisfy(
        self,
        request: Any,
        run_id: Annotated[UUID, Path(description="Plan run identifier.")],
        gate_id: Annotated[str, Path(description="Stage gate identifier.")],
        payload: GateSatisfactionInput,
    ) -> int:
        DjangoRequest.resolve(request, SatisfyStageGate).execute(run_id, gate_id, payload.evidence)
        return 204


@api_controller("/plans/runs", tags=["plans"])
class StartPlanRunController(ControllerBase):
    @route.post(
        "",
        response={201: PlanRunOutput},
        operation_id="start_plan_run",
        summary="Start a plan run",
        description="Start a run for a published plan definition.",
    )
    def start(self, request: Any, payload: PlanRunInput) -> tuple[int, PlanRunOutput]:
        run = DjangoRequest.resolve(request, StartPlanRun).execute(UUID(payload.definition_id), payload.initial_input)
        return 201, PlanRunOutput(id=str(run.identifier), current_stage_id=run.current_stage_id, status=run.status)


@api_controller("/plans/runs", tags=["plans"])
class SubmitStageResultController(ControllerBase):
    @route.post(
        "/{run_id}/submissions",
        response={200: PlanRunOutput},
        operation_id="submit_stage_result",
        summary="Submit a stage result",
        description="Submit the result for the active stage of a plan run.",
    )
    def submit(
        self,
        request: Any,
        run_id: Annotated[UUID, Path(description="Plan run identifier.")],
        payload: StageSubmissionInput,
    ) -> tuple[int, PlanRunOutput]:
        run = DjangoRequest.resolve(request, SubmitStageResult).execute(run_id, payload.payload)
        return 200, PlanRunOutput(id=str(run.identifier), current_stage_id=run.current_stage_id, status=run.status)

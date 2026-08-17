from typing import Annotated

from modwire_hex.django import DjangoRequest
from ninja import Path, Status
from ninja_extra import ControllerBase, api_controller, route

from ..services import DiagramsService
from . import schemas


@api_controller("/diagrams/kinds", tags=["Diagram kinds"])
class DiagramKindsController(ControllerBase):
    @route.get(
        "",
        response=list[schemas.DiagramKind],
        operation_id="find_diagram_kinds",
        summary="List diagram kinds",
        description="Return the Mermaiden diagram kinds available to agents.",
    )
    def find_all(self, request):
        return DjangoRequest.resolve(request, DiagramsService).find_kinds()

    @route.get(
        "/{kind}",
        response=schemas.DiagramKindDescription,
        operation_id="get_diagram_kind",
        summary="Get a diagram kind",
        description="Return the elements, relations, annotations, and commands available for a diagram kind.",
    )
    def get(self, request, kind: Annotated[str, Path(description="Mermaiden diagram-kind identifier.")]):
        return DjangoRequest.resolve(request, DiagramsService).describe_kind(kind)

    @route.get(
        "/{kind}/commands/{operation}",
        response=schemas.DiagramCommandSchema,
        operation_id="get_diagram_command_schema",
        summary="Get a diagram command schema",
        description="Return the JSON Schema for one diagram command's arguments.",
    )
    def get_command_schema(
        self,
        request,
        kind: Annotated[str, Path(description="Mermaiden diagram-kind identifier.")],
        operation: Annotated[str, Path(description="Diagram command operation name.")],
    ):
        arguments_schema = DjangoRequest.resolve(request, DiagramsService).get_command_schema(kind, operation)
        return {"kind": kind, "operation": operation, "arguments_schema": arguments_schema}


@api_controller("/diagram-sets", tags=["Diagram sets"])
class DiagramSetsController(ControllerBase):
    @route.post(
        "",
        response={201: schemas.DiagramSet},
        operation_id="create_diagram_set",
        summary="Create a diagram set",
        description="Create a collection in which an agent can build diagrams for one topic.",
    )
    def create(self, request, body: schemas.CreateDiagramSet):
        diagram_set = DjangoRequest.resolve(request, DiagramsService).create_set(body.model_dump(mode="json"))
        return Status(201, diagram_set)

    @route.get(
        "",
        response=list[schemas.DiagramSetSummary],
        operation_id="find_diagram_sets",
        summary="List diagram sets",
        description="Return all diagram-set summaries.",
    )
    def find_all(self, request):
        return DjangoRequest.resolve(request, DiagramsService).find_all_sets()

    @route.get(
        "/{diagram_set_id}",
        response=schemas.DiagramSet,
        operation_id="get_diagram_set",
        summary="Get a diagram set",
        description="Return a diagram set and the diagrams belonging to it.",
    )
    def get(
        self,
        request,
        diagram_set_id: Annotated[str, Path(description="Diagram set identifier.")],
    ):
        return DjangoRequest.resolve(request, DiagramsService).get_set(diagram_set_id)

    @route.patch(
        "/{diagram_set_id}",
        response=schemas.DiagramSet,
        operation_id="update_diagram_set",
        summary="Update a diagram set",
        description="Update the supplied diagram-set fields.",
    )
    def update(
        self,
        request,
        diagram_set_id: Annotated[str, Path(description="Diagram set identifier.")],
        body: schemas.UpdateDiagramSet,
    ):
        return DjangoRequest.resolve(request, DiagramsService).update_set(
            diagram_set_id,
            body.model_dump(mode="json", exclude_none=True),
        )

    @route.delete(
        "/{diagram_set_id}",
        response={204: None},
        operation_id="delete_diagram_set",
        summary="Delete a diagram set",
        description="Delete a diagram set and all diagrams belonging to it.",
    )
    def delete(
        self,
        request,
        diagram_set_id: Annotated[str, Path(description="Diagram set identifier.")],
    ):
        DjangoRequest.resolve(request, DiagramsService).delete_set(diagram_set_id)
        return Status(204, None)

    @route.post(
        "/{diagram_set_id}/diagrams",
        response={201: schemas.Diagram},
        operation_id="create_diagram",
        summary="Create a diagram",
        description="Create an empty typed diagram in a diagram set.",
    )
    def create_diagram(
        self,
        request,
        diagram_set_id: Annotated[str, Path(description="Diagram set identifier.")],
        body: schemas.CreateDiagram,
    ):
        diagram = DjangoRequest.resolve(request, DiagramsService).create_diagram(
            diagram_set_id,
            body.model_dump(mode="json"),
        )
        return Status(201, diagram)

    @route.get(
        "/{diagram_set_id}/diagrams",
        response=list[schemas.DiagramSummary],
        operation_id="find_diagram_set_diagrams",
        summary="List diagrams in a diagram set",
        description="Return summaries for the diagrams belonging to one diagram set.",
    )
    def find_diagrams(
        self,
        request,
        diagram_set_id: Annotated[str, Path(description="Diagram set identifier.")],
    ):
        return DjangoRequest.resolve(request, DiagramsService).find_diagrams_in_set(diagram_set_id)

    @route.get(
        "/{diagram_set_id}/diagrams/{diagram_id}",
        response=schemas.Diagram,
        operation_id="get_diagram_set_diagram",
        summary="Get a diagram from a diagram set",
        description="Return a diagram only when it belongs to the selected diagram set.",
    )
    def get_diagram(
        self,
        request,
        diagram_set_id: Annotated[str, Path(description="Diagram set identifier.")],
        diagram_id: Annotated[str, Path(description="Diagram identifier.")],
    ):
        return DjangoRequest.resolve(request, DiagramsService).get_diagram_in_set(
            diagram_set_id,
            diagram_id,
        )


@api_controller("/diagrams", tags=["Diagrams"])
class DiagramsController(ControllerBase):
    @route.get(
        "",
        response=list[schemas.DiagramSummary],
        operation_id="find_diagrams",
        summary="List diagrams",
        description="Return all diagram summaries.",
    )
    def find_all(self, request):
        return DjangoRequest.resolve(request, DiagramsService).find_all_diagrams()

    @route.get(
        "/{diagram_id}",
        response=schemas.Diagram,
        operation_id="get_diagram",
        summary="Get a diagram",
        description="Return a diagram's canonical snapshot, generated source, and browser interactions.",
    )
    def get(self, request, diagram_id: Annotated[str, Path(description="Diagram identifier.")]):
        return DjangoRequest.resolve(request, DiagramsService).get_diagram(diagram_id)

    @route.delete(
        "/{diagram_id}",
        response={204: None},
        operation_id="delete_diagram",
        summary="Delete a diagram",
        description="Delete a diagram from its set.",
    )
    def delete(self, request, diagram_id: Annotated[str, Path(description="Diagram identifier.")]):
        DjangoRequest.resolve(request, DiagramsService).delete_diagram(diagram_id)
        return Status(204, None)

    @route.post(
        "/{diagram_id}/commands",
        response=schemas.Diagram,
        operation_id="apply_diagram_command",
        summary="Apply a diagram command",
        description="Apply one catalog command and persist the regenerated snapshot and Mermaid source.",
    )
    def apply_command(
        self,
        request,
        diagram_id: Annotated[str, Path(description="Diagram identifier.")],
        body: schemas.ApplyDiagramCommand,
    ):
        return DjangoRequest.resolve(request, DiagramsService).apply_command(
            diagram_id,
            body.expected_revision,
            body.operation,
            body.arguments,
        )

    @route.put(
        "/{diagram_id}/interactions",
        response=schemas.Diagram,
        operation_id="update_diagram_interactions",
        summary="Update diagram interactions",
        description="Replace the diagram's declarative browser interactions.",
    )
    def update_interactions(
        self,
        request,
        diagram_id: Annotated[str, Path(description="Diagram identifier.")],
        body: schemas.UpdateDiagramInteractions,
    ):
        return DjangoRequest.resolve(request, DiagramsService).update_interactions(
            diagram_id,
            body.expected_revision,
            body.model_dump(mode="json")["interactions"],
        )

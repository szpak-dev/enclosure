from typing import Annotated

from modwire_hex.django import DjangoRequest
from ninja import Path, Query, Status
from ninja_extra import ControllerBase, api_controller, http_get, route
from sirenity import (
    SirenContinuation,
    SirenFollowUp,
    SirenItemFollowUp,
    SirenScope,
    SirenSourceInput,
    siren_follow_ups,
    siren_pagination,
)

from ..services.facade import DiagramsService
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

    @siren_follow_ups(
        http_get,
        "/{kind}",
        response=schemas.DiagramKindDescription,
        operation_id="get_diagram_kind",
        follow_ups={
            "content": SirenFollowUp(
                operation_id="read_diagram_kind_content",
                parameters={
                    "path.kind": "id",
                    "query.expected_revision": "content_revision",
                },
                rel="item",
                scope=SirenScope.ENTITY,
            )
        },
        status=200,
        summary="Get a diagram kind",
        description="Return the objects, placements, and commands available for a diagram kind.",
    )
    def get(self, request, kind: Annotated[str, Path(description="Mermaiden diagram-kind identifier.")]):
        return DjangoRequest.resolve(request, DiagramsService).describe_kind(kind)

    @SirenContinuation(
        http_get,
        "/{kind}/content",
        response=schemas.DiagramKindContent,
        operation_id="read_diagram_kind_content",
        continuation={"offset": "next_offset", "limit": "limit"},
        source_inputs={
            "kind": SirenSourceInput(location="path", name="kind"),
            "expected_revision": SirenSourceInput(location="query", name="expected_revision"),
        },
        summary="Read diagram-kind content",
        description="Read one bounded page from a revision-pinned diagram-kind contract.",
    )
    def read_kind_content(
        self,
        request,
        kind: Annotated[str, Path(description="Mermaiden diagram-kind identifier.")],
        query: Query[schemas.ReadDiagramKindContent],
    ):
        return DjangoRequest.resolve(request, DiagramsService).read_kind_content(
            kind,
            query.expected_revision,
            query.offset,
            query.limit,
        )

    @siren_follow_ups(
        http_get,
        "/{kind}/commands/{operation}",
        response=schemas.DiagramCommandSchema,
        operation_id="get_diagram_command_schema",
        follow_ups={
            "content": SirenFollowUp(
                operation_id="read_diagram_kind_content",
                parameters={
                    "path.kind": "kind",
                    "query.expected_revision": "content_revision",
                },
                rel="item",
                scope=SirenScope.ENTITY,
            )
        },
        status=200,
        summary="Get a diagram command schema",
        description="Return the JSON Schema for one diagram command's arguments.",
    )
    def get_command_schema(
        self,
        request,
        kind: Annotated[str, Path(description="Mermaiden diagram-kind identifier.")],
        operation: Annotated[str, Path(description="Diagram command operation name.")],
    ):
        service = DjangoRequest.resolve(request, DiagramsService)
        description = service.describe_kind(kind)
        return {
            "kind": kind,
            "operation": operation,
            "content_revision": description["content_revision"],
            "content_total_characters": description["content_total_characters"],
            "arguments_schema": service.get_command_schema(kind, operation),
        }


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

    @siren_pagination(
        http_get,
        "",
        response=schemas.DiagramSetPage,
        operation_id="find_diagram_sets",
        continuation={"offset": "next_offset", "limit": "limit"},
        source_inputs={},
        item_follow_ups={
            "diagram_set": SirenItemFollowUp(
                operation_id="get_diagram_set",
                parameters={"path.diagram_set_id": "id"},
                rel="item",
                scope=SirenScope.ENTITY,
                item_collection="items",
            )
        },
        status=200,
        summary="List diagram sets",
        description="Return one bounded page of diagram-set summaries.",
    )
    def find_all(self, request, query: Query[schemas.FindPage]):
        return DjangoRequest.resolve(request, DiagramsService).find_set_page(query.offset, query.limit)

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

    @route.post(
        "/{diagram_set_id}/diagram-batches",
        response={201: schemas.DiagramCommandBatchReceipt},
        operation_id="create_diagram_batch",
        summary="Create a diagram from a command batch",
        description="Create a typed diagram from an ordered command batch and return a compact receipt.",
    )
    def create_diagram_batch(
        self,
        request,
        diagram_set_id: Annotated[str, Path(description="Diagram set identifier.")],
        body: schemas.CreateDiagramBatch,
    ):
        receipt = DjangoRequest.resolve(request, DiagramsService).create_diagram_batch(
            diagram_set_id,
            {"title": body.title, "kind": body.kind},
            tuple((command.operation, command.arguments) for command in body.commands),
        )
        return Status(201, receipt)

    @siren_pagination(
        http_get,
        "/{diagram_set_id}/diagrams",
        response=schemas.DiagramPage,
        operation_id="find_diagram_set_diagrams",
        continuation={"offset": "next_offset", "limit": "limit"},
        source_inputs={"diagram_set_id": SirenSourceInput(location="path", name="diagram_set_id")},
        item_follow_ups={
            "diagram": SirenItemFollowUp(
                operation_id="get_diagram_set_diagram",
                parameters={"path.diagram_id": "id"},
                rel="item",
                scope=SirenScope.ENTITY,
                source_inputs={"diagram_set_id": SirenSourceInput(location="path", name="diagram_set_id")},
                item_collection="items",
            )
        },
        status=200,
        summary="List diagrams in a diagram set",
        description="Return one bounded page of diagrams belonging to one diagram set.",
    )
    def find_diagrams(
        self,
        request,
        diagram_set_id: Annotated[str, Path(description="Diagram set identifier.")],
        query: Query[schemas.FindPage],
    ):
        return DjangoRequest.resolve(request, DiagramsService).find_diagram_set_page(
            diagram_set_id,
            query.offset,
            query.limit,
        )

    @siren_follow_ups(
        http_get,
        "/{diagram_set_id}/diagrams/{diagram_id}",
        response=schemas.Diagram,
        operation_id="get_diagram_set_diagram",
        follow_ups={
            "source": SirenFollowUp(
                operation_id="read_diagram_content",
                parameters={
                    "path.diagram_id": "id",
                    "query.document": "source_document",
                    "query.expected_revision": "revision",
                },
                rel="item",
                scope=SirenScope.ENTITY,
            ),
            "snapshot": SirenFollowUp(
                operation_id="read_diagram_content",
                parameters={
                    "path.diagram_id": "id",
                    "query.document": "snapshot_document",
                    "query.expected_revision": "revision",
                },
                rel="item",
                scope=SirenScope.ENTITY,
            ),
        },
        status=200,
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
    @siren_pagination(
        http_get,
        "",
        response=schemas.DiagramPage,
        operation_id="find_diagrams",
        continuation={"offset": "next_offset", "limit": "limit"},
        source_inputs={},
        item_follow_ups={
            "diagram": SirenItemFollowUp(
                operation_id="get_diagram",
                parameters={"path.diagram_id": "id"},
                rel="item",
                scope=SirenScope.ENTITY,
                item_collection="items",
            )
        },
        status=200,
        summary="List diagrams",
        description="Return one bounded page of diagram summaries.",
    )
    def find_all(self, request, query: Query[schemas.FindPage]):
        return DjangoRequest.resolve(request, DiagramsService).find_diagram_page(query.offset, query.limit)

    @SirenContinuation(
        http_get,
        "/{diagram_id}/content",
        response=schemas.DiagramContent,
        operation_id="read_diagram_content",
        continuation={"offset": "next_offset", "limit": "limit"},
        source_inputs={
            "diagram_id": SirenSourceInput(location="path", name="diagram_id"),
            "document": SirenSourceInput(location="query", name="document"),
            "expected_revision": SirenSourceInput(location="query", name="expected_revision"),
        },
        summary="Read diagram content",
        description="Read one revision-pinned bounded page from a diagram's source or canonical snapshot.",
    )
    def read_content(
        self,
        request,
        diagram_id: Annotated[str, Path(description="Diagram identifier.")],
        query: Query[schemas.ReadDiagramContent],
    ):
        return DjangoRequest.resolve(request, DiagramsService).read_diagram_content(
            diagram_id,
            query.document,
            query.expected_revision,
            query.offset,
            query.limit,
        )

    @siren_follow_ups(
        http_get,
        "/{diagram_id}",
        response=schemas.Diagram,
        operation_id="get_diagram",
        follow_ups={
            "source": SirenFollowUp(
                operation_id="read_diagram_content",
                parameters={
                    "path.diagram_id": "id",
                    "query.document": "source_document",
                    "query.expected_revision": "revision",
                },
                rel="item",
                scope=SirenScope.ENTITY,
            ),
            "snapshot": SirenFollowUp(
                operation_id="read_diagram_content",
                parameters={
                    "path.diagram_id": "id",
                    "query.document": "snapshot_document",
                    "query.expected_revision": "revision",
                },
                rel="item",
                scope=SirenScope.ENTITY,
            ),
        },
        status=200,
        summary="Get a diagram",
        description="Return a diagram's canonical snapshot and Mermaid source when renderable.",
    )
    def get(self, request, diagram_id: Annotated[str, Path(description="Diagram identifier.")]):
        return DjangoRequest.resolve(request, DiagramsService).get_diagram(diagram_id)

    @route.patch(
        "/{diagram_id}",
        response=schemas.Diagram,
        operation_id="update_diagram",
        summary="Update a diagram",
        description="Replace diagram metadata without changing its canonical Mermaiden snapshot.",
    )
    def update(
        self,
        request,
        diagram_id: Annotated[str, Path(description="Diagram identifier.")],
        body: schemas.UpdateDiagram,
    ):
        return DjangoRequest.resolve(request, DiagramsService).update_diagram(
            diagram_id,
            body.expected_revision,
            body.title,
        )

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
        description="Apply one catalog command and persist its snapshot and source when renderable.",
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

    @route.post(
        "/{diagram_id}/command-batches",
        response=schemas.DiagramCommandBatchReceipt,
        operation_id="apply_diagram_command_batch",
        summary="Apply a diagram command batch",
        description="Apply an ordered command batch atomically and return a compact mutation receipt.",
    )
    def apply_command_batch(
        self,
        request,
        diagram_id: Annotated[str, Path(description="Diagram identifier.")],
        body: schemas.ApplyDiagramCommandBatch,
    ):
        return DjangoRequest.resolve(request, DiagramsService).apply_command_batch(
            diagram_id,
            body.expected_revision,
            tuple((command.operation, command.arguments) for command in body.commands),
        )

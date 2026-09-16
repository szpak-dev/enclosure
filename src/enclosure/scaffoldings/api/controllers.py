from typing import Annotated

from modwire_hex.django import DjangoRequest
from ninja import Path, Query, Status
from ninja_extra import ControllerBase, api_controller, http_get, route
from sirenity import SirenContinuation, siren_pagination

from ..services.facade import ScaffoldingService
from . import schemas


@api_controller("/scaffoldings", tags=["Scaffoldings"])
class ScaffoldingController(ControllerBase):
    @route.post(
        "",
        response={201: schemas.Scaffolding},
        operation_id="create_scaffolding",
        summary="Create a scaffolding",
        description="Store a reusable source-code template and its parameter specification.",
    )
    def create(self, request, body: schemas.ScaffoldingInput):
        value = DjangoRequest.resolve(request, ScaffoldingService).create(body.model_dump(mode="json"))
        return Status(201, value)

    @siren_pagination(
        http_get,
        response=schemas.ScaffoldingPage,
        operation_id="find_scaffoldings",
        continuation={"offset": "next_offset", "limit": "limit"},
        summary="List scaffoldings",
        description="Return one bounded page of compact scaffolding references.",
    )
    def find_all(self, request, query: Query[schemas.FindPage]):
        return DjangoRequest.resolve(request, ScaffoldingService).find_page(query.offset, query.limit)

    @route.post(
        "/name-search-results",
        response=list[schemas.ScaffoldingSummary],
        operation_id="search_scaffoldings",
        summary="Search scaffoldings",
        description="Find a bounded set of compact scaffolding references by name and language.",
    )
    def search(self, request, body: schemas.SearchScaffoldings):
        return DjangoRequest.resolve(request, ScaffoldingService).search(body.name, body.language_id, body.limit)

    @route.get(
        "/{scaffolding_id}",
        response=schemas.Scaffolding,
        operation_id="get_scaffolding",
        summary="Get a scaffolding",
        description="Return variables and revisioned template manifests without template bodies.",
    )
    def get(self, request, scaffolding_id: Annotated[str, Path(description="Scaffolding identifier.")]):
        return DjangoRequest.resolve(request, ScaffoldingService).get_detail(scaffolding_id)

    @SirenContinuation(
        http_get,
        "/{scaffolding_id}/template-content",
        response=schemas.ScaffoldingTemplateContent,
        operation_id="read_scaffolding_template",
        continuation={"offset": "next_offset", "limit": "limit"},
        summary="Read scaffolding template content",
        description="Read one bounded page from an exact revision-pinned template path.",
    )
    def read_template(
        self,
        request,
        scaffolding_id: Annotated[str, Path(description="Scaffolding identifier.")],
        query: Query[schemas.ReadScaffoldingTemplate],
    ):
        return DjangoRequest.resolve(request, ScaffoldingService).read_template(
            scaffolding_id,
            query.path,
            query.expected_revision,
            query.offset,
            query.limit,
        )

    @route.put(
        "/{scaffolding_id}",
        response=schemas.Scaffolding,
        operation_id="update_scaffolding",
        summary="Update a scaffolding",
        description="Replace a scaffolding's metadata and specification.",
    )
    def update(
        self,
        request,
        scaffolding_id: Annotated[str, Path(description="Scaffolding identifier.")],
        body: schemas.ScaffoldingInput,
    ):
        return DjangoRequest.resolve(request, ScaffoldingService).update(scaffolding_id, body.model_dump(mode="json"))

    @route.post(
        "/{scaffolding_id}/renderings",
        response=schemas.RenderingPage,
        operation_id="render_scaffolding",
        summary="Render a scaffolding",
        description="Return one bounded page of rendered-file manifests and previews.",
    )
    def create_rendering(
        self,
        request,
        scaffolding_id: Annotated[str, Path(description="Scaffolding identifier.")],
        body: schemas.RenderScaffolding,
    ):
        return DjangoRequest.resolve(request, ScaffoldingService).render_page(
            scaffolding_id,
            body.parameters,
            body.offset,
            body.limit,
        )

    @route.post(
        "/{scaffolding_id}/rendered-file-content",
        response=schemas.RenderedFileContent,
        operation_id="read_scaffolding_rendered_file",
        summary="Read rendered scaffolding content",
        description="Rerender and read one bounded page from a revision-pinned output path.",
    )
    def read_rendered_file(
        self,
        request,
        scaffolding_id: Annotated[str, Path(description="Scaffolding identifier.")],
        body: schemas.ReadScaffoldingRenderedFile,
    ):
        return DjangoRequest.resolve(request, ScaffoldingService).read_rendered_file(
            scaffolding_id,
            body.parameters,
            body.path,
            body.expected_revision,
            body.offset,
            body.limit,
        )

    @route.delete(
        "/{scaffolding_id}",
        response={204: None},
        operation_id="delete_scaffolding",
        summary="Delete a scaffolding",
        description="Permanently delete a scaffolding.",
    )
    def delete(self, request, scaffolding_id: Annotated[str, Path(description="Scaffolding identifier.")]):
        DjangoRequest.resolve(request, ScaffoldingService).delete(scaffolding_id)
        return Status(204, None)

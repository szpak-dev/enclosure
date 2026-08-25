from typing import Annotated

from modwire_hex.django import DjangoRequest
from ninja import Path, Status
from ninja_extra import ControllerBase, api_controller, route

from ..services import ScaffoldingService
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
        scaffolding = DjangoRequest.resolve(request, ScaffoldingService).create(body.model_dump(mode="json"))
        return Status(201, scaffolding)

    @route.get(
        "",
        response=list[schemas.ScaffoldingSummary],
        operation_id="find_scaffoldings",
        summary="List scaffoldings",
        description="Return summaries of all available scaffoldings.",
    )
    def find_all(self, request):
        return DjangoRequest.resolve(request, ScaffoldingService).find_all()

    @route.post(
        "/name-search-results",
        response=list[schemas.ScaffoldingSummary],
        operation_id="search_scaffoldings",
        summary="Search scaffoldings",
        description="Find compact scaffolding summaries by name, optionally constrained to one language.",
    )
    def search(self, request, body: schemas.SearchScaffoldings):
        return DjangoRequest.resolve(request, ScaffoldingService).search(body.name, body.language_id)

    @route.get(
        "/{scaffolding_id}",
        response=schemas.Scaffolding,
        operation_id="get_scaffolding",
        summary="Get a scaffolding",
        description="Return a scaffolding and its complete specification.",
    )
    def get(self, request, scaffolding_id: Annotated[str, Path(description="Scaffolding identifier.")]):
        return DjangoRequest.resolve(request, ScaffoldingService).get(scaffolding_id)

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
        response=schemas.Rendering,
        operation_id="render_scaffolding",
        summary="Render a scaffolding",
        description="Generate source files from a scaffolding using the supplied parameters.",
    )
    def create_rendering(
        self,
        request,
        scaffolding_id: Annotated[str, Path(description="Scaffolding identifier.")],
        body: schemas.GenerateSourceCode,
    ):
        return {
            "files": DjangoRequest.resolve(
                request,
                ScaffoldingService,
            )
            .render(scaffolding_id, body.parameters)
            .package.files,
        }

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

from modwire_hex.django import DjangoRequest
from ninja_extra import ControllerBase, api_controller, route

from ..services import DiagramsService
from . import schemas


@api_controller("/diagrams", tags=["Diagrams"])
class DiagramsController(ControllerBase):
    @route.get(
        "",
        response=schemas.Status,
        operation_id="get_diagrams_status",
        summary="Get diagrams status",
        description="Return the generated app status.",
    )
    def get(self, request):
        return {"status": DjangoRequest.resolve(request, DiagramsService).get_status()}

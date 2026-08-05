from modwire_hex.django import DjangoRequest
from ninja_extra import ControllerBase, api_controller, route

from ..services import LanguagesService
from . import schemas


@api_controller("/languages", tags=["Languages"])
class LanguagesController(ControllerBase):
    @route.get(
        "",
        response=schemas.Status,
        operation_id="get_languages_status",
        summary="Get languages status",
        description="Return the generated app status.",
    )
    def get(self, request):
        return {"status": DjangoRequest.resolve(request, LanguagesService).get_status()}

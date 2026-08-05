from modwire_hex.django import DjangoRequest
from ninja_extra import ControllerBase, api_controller, route

from ..services import LanguagesService
from . import schemas


@api_controller("/languages", tags=["Languages"])
class LanguagesController(ControllerBase):
    @route.get(
        "",
        response=list[schemas.Language],
        operation_id="find_languages",
        summary="List languages",
        description="Return languages supported for source processing and scaffolding.",
    )
    def find_all(self, request):
        return DjangoRequest.resolve(request, LanguagesService).find_all()

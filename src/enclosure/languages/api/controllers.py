from typing import Annotated

from modwire_hex.django import DjangoRequest
from ninja import Path
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

    @route.get(
        "/{language_id}",
        response=schemas.Language,
        operation_id="get_language",
        summary="Get a language",
        description="Return a supported source-processing and scaffolding language.",
    )
    def get(self, request, language_id: Annotated[str, Path(description="Language identifier.")]):
        return DjangoRequest.resolve(request, LanguagesService).get(language_id)

from django.conf import settings
from ninja_extra import ControllerBase, api_controller, route

from ..security.adapters.http import SecurityPermission


@api_controller("", tags=["Root"], permissions=[SecurityPermission])
class RootController(ControllerBase):
    @route.get(
        "/",
        response=dict,
        operation_id="get_api_root",
        summary="Discover the API",
        description="Return the API title, version, and public entry points.",
    )
    def get(self):
        return {
            "title": "Enclosure API",
            "version": settings.RELEASE_VERSION,
        }

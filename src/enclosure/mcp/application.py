from django.conf import settings
from starlette.types import ASGIApp

from .adapters.protocol import McpProtocolServer


class McpApplication:
    def build(self) -> ASGIApp:
        return McpProtocolServer(release=settings.RELEASE_VERSION).build()

import os

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application
from modwire_siren import siren_adapter
from starlette.types import ASGIApp, Receive, Scope, Send

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "enclosure.core.settings")

def build_applications() -> tuple[ASGIApp, ASGIApp]:
    django_application = get_asgi_application()
    if settings.DEBUG:
        django_application = ASGIStaticFilesHandler(django_application)

    from .api import api
    from .mcp.server import create_server

    siren_configuration = settings.MODWIRE_SIREN
    adapter = siren_adapter(
        api.get_openapi_schema(path_prefix=siren_configuration["SOURCE_PATH"]),
        source_path=siren_configuration["SOURCE_PATH"],
        public_path=siren_configuration["PUBLIC_PATH"],
    )
    mcp_server = create_server(
        adapter,
        django_application,
        version=settings.RELEASE_VERSION,
    )
    mcp_application = mcp_server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
    )
    return django_application, mcp_application


django_application, mcp_application = build_applications()


async def application(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        await mcp_application(scope, receive, send)
    elif scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
        await mcp_application(scope, receive, send)
    else:
        await django_application(scope, receive, send)

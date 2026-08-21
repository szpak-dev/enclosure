import os

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application
from django.core.wsgi import get_wsgi_application
from sirenity import siren_configuration
from starlette.types import ASGIApp, Receive, Scope, Send

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "enclosure.core.settings")


def build_applications() -> tuple[ASGIApp, ASGIApp]:
    django_application = get_asgi_application()
    if settings.DEBUG:
        django_application = ASGIStaticFilesHandler(django_application)

    from .mcp.server import create_server

    declaration = settings.SIRENITY
    configuration = siren_configuration(
        openapi=declaration["OPENAPI"],
        source_path=declaration["SOURCE_PATH"],
        public_path=declaration["PUBLIC_PATH"],
        policy=declaration["POLICY"],
        profiles=tuple(declaration["PROFILES"]),
    )
    mcp_server = create_server(
        configuration,
        get_wsgi_application(),
        version=settings.RELEASE_VERSION,
    )
    mcp_application = mcp_server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
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

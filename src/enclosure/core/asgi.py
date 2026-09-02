import os

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application
from starlette.types import ASGIApp, Receive, Scope, Send

from enclosure.mcp.application import McpApplication

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "enclosure.core.settings")


def build_applications() -> tuple[ASGIApp, ASGIApp]:
    django_application = get_asgi_application()
    if settings.DEBUG:
        django_application = ASGIStaticFilesHandler(django_application)

    mcp_application = McpApplication().build()
    return django_application, mcp_application


django_application, mcp_application = build_applications()


async def application(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        await mcp_application(scope, receive, send)
    elif scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
        await mcp_application(scope, receive, send)
    else:
        await django_application(scope, receive, send)

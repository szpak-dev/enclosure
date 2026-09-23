import asyncio
import os
from dataclasses import dataclass

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from enclosure.shared.execution import CancellationSignal, RequestCancellationContext


@dataclass(frozen=True)
class DisconnectAwareApplication:
    application: ASGIApp
    cancellation: RequestCancellationContext

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return
        signal = CancellationSignal()
        token = self.cancellation.bind(signal)
        messages: asyncio.Queue[Message] = asyncio.Queue(maxsize=1)
        receive_task = asyncio.create_task(self._receive(receive, messages, signal))
        try:
            await self.application(scope, messages.get, send)
        except asyncio.CancelledError:
            signal.cancel()
            raise
        finally:
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
            self.cancellation.reset(token)

    async def _receive(
        self,
        receive: Receive,
        messages: asyncio.Queue[Message],
        signal: CancellationSignal,
    ) -> None:
        while True:
            message = await receive()
            disconnected = message["type"] == "http.disconnect"
            if disconnected:
                signal.cancel()
            await messages.put(message)
            if disconnected:
                return


@dataclass(frozen=True)
class RoutingApplication:
    django: ASGIApp
    mcp: ASGIApp

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.mcp(scope, receive, send)
        elif scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
            await self.mcp(scope, receive, send)
        else:
            await self.django(scope, receive, send)


class ApplicationFactory:
    def build(self) -> ASGIApp:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "enclosure.core.settings")

        from django.conf import settings
        from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
        from django.core.asgi import get_asgi_application

        django_application = get_asgi_application()
        if settings.DEBUG:
            django_application = ASGIStaticFilesHandler(django_application)

        from enclosure.mcp.application import McpApplication

        return DisconnectAwareApplication(
            application=RoutingApplication(
                django=django_application,
                mcp=McpApplication().build(),
            ),
            cancellation=RequestCancellationContext(),
        )


application = ApplicationFactory().build()

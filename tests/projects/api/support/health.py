import asyncio
import os
from dataclasses import dataclass, field
from errno import ENXIO
from pathlib import Path
from typing import cast

from starlette.types import ASGIApp, Message, Scope


@dataclass(frozen=True)
class BlockingArchitectureSource:
    path: Path

    @classmethod
    def create(cls, root: Path) -> "BlockingArchitectureSource":
        (root / "uv.lock").write_text("", encoding="utf-8")
        path = root / "app.py"
        os.mkfifo(path)
        return cls(path=path)

    async def connect_writer_when_ready(self) -> int:
        while True:
            try:
                return os.open(self.path, os.O_WRONLY | os.O_NONBLOCK)
            except OSError as error:
                if error.errno != ENXIO:
                    raise
                await asyncio.sleep(0.01)

    def replace(self) -> None:
        replacement = self.path.with_name(f".{self.path.name}.replacement")
        replacement.write_text("class ExampleApplication:\n    pass\n", encoding="utf-8")
        os.replace(replacement, self.path)

    def block(self) -> None:
        replacement = self.path.with_name(f".{self.path.name}.blocking")
        os.mkfifo(replacement)
        os.replace(replacement, self.path)


@dataclass
class DisconnectingHealthRequest:
    application: ASGIApp
    path: str
    source: BlockingArchitectureSource
    disconnect_sent: asyncio.Event = field(default_factory=asyncio.Event)
    receive_count: int = 0
    writers: list[int] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)

    async def run(self) -> None:
        scope = cast(
            Scope,
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": self.path,
                "raw_path": self.path.encode(),
                "query_string": b"",
                "root_path": "",
                "headers": [(b"host", b"testserver")],
                "client": ("127.0.0.1", 40000),
                "server": ("testserver", 80),
            },
        )
        application = asyncio.create_task(self.application(scope, self.receive, self.send))
        try:
            await asyncio.wait_for(self.disconnect_sent.wait(), timeout=15)
            await asyncio.wait_for(application, timeout=5)
        finally:
            if not application.done():
                application.cancel()
                try:
                    await application
                except asyncio.CancelledError:
                    pass
            for writer in self.writers:
                os.close(writer)
            self.source.replace()

    async def receive(self) -> Message:
        self.receive_count += 1
        if self.receive_count == 1:
            return {"type": "http.request", "body": b"", "more_body": False}
        writer = await self.source.connect_writer_when_ready()
        self.writers.append(writer)
        self.disconnect_sent.set()
        return {"type": "http.disconnect"}

    async def send(self, message: Message) -> None:
        self.messages.append(message)

    async def run_before(self, following: "DisconnectingHealthRequest") -> None:
        await self.run()
        self.source.block()
        await following.run()

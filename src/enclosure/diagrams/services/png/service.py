import fcntl
import json
import os
import tempfile
from base64 import b64encode
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from wireup import injectable

from enclosure.shared.errors import ServiceUnavailableError

from ...errors import DiagramsError
from ...models import Diagram
from ..mermaiden import MermaidenService
from ..repository import DiagramsRepository
from .model import DiagramPng


@injectable
@dataclass(frozen=True)
class DiagramPngService:
    repository: DiagramsRepository
    mermaiden: MermaidenService
    directory: Path = field(
        default=Path(
            os.environ.get(
                "DIAGRAM_PNG_CACHE_DIRECTORY",
                str(Path(tempfile.gettempdir()) / f"enclosure-png-{os.getuid()}"),
            )
        ),
        init=False,
    )

    def read(self, diagram_id: str, expected_revision: int) -> DiagramPng:
        diagram = self.repository.get_diagram(diagram_id)
        if diagram.revision != expected_revision:
            raise DiagramsError("Diagram changed; reload it before downloading PNG.")
        if not diagram.source.strip():
            raise DiagramsError("Diagram has no source to export.")
        try:
            content = self.content(diagram)
        except OSError as error:
            raise ServiceUnavailableError("The PNG artifact store is unavailable; retry the download.") from error
        if self.repository.get_diagram(diagram_id).revision != expected_revision:
            raise DiagramsError("Diagram changed; reload it before downloading PNG.")
        return DiagramPng(
            diagram_id=diagram.id,
            revision=diagram.revision,
            filename=f"diagram-{diagram.id}-r{diagram.revision}.png",
            media_type="image/png",
            content_revision=sha256(content).hexdigest(),
            content=b64encode(content).decode("ascii"),
            width=int.from_bytes(content[16:20], "big"),
            height=int.from_bytes(content[20:24], "big"),
            total_bytes=len(content),
        )

    def content(self, diagram: Diagram) -> bytes:
        identity = json.dumps(
            {
                "diagram_id": diagram.id,
                "revision": diagram.revision,
                "snapshot": diagram.snapshot,
                "renderer": self.mermaiden.renderer_identity(),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        key = sha256(identity.encode("utf-8")).hexdigest()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.directory / f"{key}.png"
        with (self.directory / f"{key}.lock").open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if not path.is_file():
                model = self.mermaiden.restore(diagram.snapshot)
                self.publish(path, self.mermaiden.render_png(model))
            return path.read_bytes()

    def publish(self, path: Path, content: bytes) -> None:
        with tempfile.NamedTemporaryFile(mode="wb", dir=self.directory) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            os.link(temporary.name, path)

import fcntl
import json
import os
import tempfile
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from wireup import injectable

from enclosure.shared.errors import ServiceUnavailableError

from ...errors import DiagramsError
from ...models import Diagram
from ..mermaiden.service import MermaidenService
from ..repository import DiagramsRepository
from .model import DiagramSvgPage


@injectable
@dataclass(frozen=True)
class DiagramSvgService:
    repository: DiagramsRepository
    mermaiden: MermaidenService
    directory: Path = field(
        default=Path(
            os.environ.get(
                "DIAGRAM_SVG_CACHE_DIRECTORY",
                str(Path(tempfile.gettempdir()) / f"enclosure-svg-{os.getuid()}"),
            )
        ),
        init=False,
    )

    def read(self, diagram_id: str, expected_revision: int, offset: int, limit: int) -> DiagramSvgPage:
        diagram = self.repository.get_diagram(diagram_id)
        if diagram.revision != expected_revision:
            raise DiagramsError("Diagram changed; reload it before downloading SVG.")
        if not diagram.source.strip():
            raise DiagramsError("Diagram has no source to export.")
        try:
            content = self.content(diagram)
        except OSError as error:
            raise ServiceUnavailableError("The SVG artifact store is unavailable; retry the download.") from error
        if offset > len(content):
            raise DiagramsError("SVG content offset is outside the document.")
        effective_limit = max(1, len(content) - offset) if limit == 0 else limit
        next_offset = min(offset + effective_limit, len(content))
        return DiagramSvgPage(
            diagram_id=diagram.id,
            revision=diagram.revision,
            filename=f"diagram-{diagram.id}-r{diagram.revision}.svg",
            media_type="image/svg+xml",
            content_revision=sha256(content.encode("utf-8")).hexdigest(),
            offset=offset,
            limit=effective_limit,
            total_characters=len(content),
            content=content[offset:next_offset],
            has_more=next_offset < len(content),
            next_offset=next_offset,
        )

    def content(self, diagram: Diagram) -> str:
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
        path = self.directory / f"{key}.svg"
        with (self.directory / f"{key}.lock").open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if not path.is_file():
                model = self.mermaiden.restore(diagram.snapshot)
                self.publish(path, self.mermaiden.render_svg(model))
            return path.read_text(encoding="utf-8")

    def publish(self, path: Path, content: str) -> None:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            os.link(temporary.name, path)

from dataclasses import dataclass
from hashlib import sha256
import json

from wireup import injectable

from ..mermaiden import MermaidenService
from ...errors import DiagramsError
from .model import DiagramKindContentPage


@injectable
@dataclass(frozen=True)
class DiagramCatalogService:
    mermaiden: MermaidenService

    def find_kinds(self) -> tuple[dict[str, str], ...]:
        return self.mermaiden.find_kinds()

    def describe_kind(self, kind: str) -> dict[str, object]:
        description = self.mermaiden.describe_kind(kind)
        content = self._canonical(description)
        return {
            **description,
            "content_revision": self._revision(content),
            "content_total_characters": len(content),
        }

    def read_content(
        self,
        kind: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> DiagramKindContentPage:
        content = self._canonical(self.mermaiden.describe_kind(kind))
        revision = self._revision(content)
        if revision != expected_revision:
            raise DiagramsError("Diagram-kind contract changed; get it again before reading content.")
        if offset > len(content):
            raise DiagramsError("Diagram-kind content offset is outside the document.")
        effective_limit = max(1, len(content) - offset) if limit == 0 else limit
        next_offset = min(offset + effective_limit, len(content))
        return DiagramKindContentPage(
            kind=kind,
            revision=revision,
            offset=offset,
            limit=effective_limit,
            total_characters=len(content),
            content=content[offset:next_offset],
            has_more=next_offset < len(content),
            next_offset=next_offset,
        )

    def get_command_schema(self, kind: str, operation: str) -> dict[str, object]:
        return self.mermaiden.get_command_schema(kind, operation)

    def _canonical(self, value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def _revision(self, content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()

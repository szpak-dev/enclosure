import json
from dataclasses import dataclass
from typing import ClassVar

from wireup import injectable

from ...errors import DiagramsError
from ..editing.service import DiagramEditingService
from .model import DiagramContentDocument, DiagramContentPage


@injectable
@dataclass(frozen=True)
class DiagramContentService:
    editing: DiagramEditingService

    MAX_CONTENT_CHARACTERS: ClassVar[int] = 512

    def read(
        self,
        diagram_id: str,
        document: DiagramContentDocument,
        expected_revision: int,
        offset: int,
        limit: int,
    ) -> DiagramContentPage:
        diagram = self.editing.get(diagram_id)
        if diagram.revision != expected_revision:
            raise DiagramsError("Diagram changed; get it again before reading content.")
        if limit < 1 or limit > self.MAX_CONTENT_CHARACTERS:
            raise DiagramsError(f"Diagram content limit must be between 1 and {self.MAX_CONTENT_CHARACTERS}.")
        content = {
            DiagramContentDocument.SOURCE: diagram.source,
            DiagramContentDocument.SNAPSHOT: json.dumps(
                diagram.snapshot,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        }[document]
        if offset < 0 or offset > len(content):
            raise DiagramsError("Diagram content offset is outside the document.")
        next_offset = min(offset + limit, len(content))
        return DiagramContentPage(
            diagram_id=diagram_id,
            revision=diagram.revision,
            document=document,
            offset=offset,
            limit=limit,
            total_characters=len(content),
            content=content[offset:next_offset],
            has_more=next_offset < len(content),
            next_offset=next_offset,
        )

from dataclasses import dataclass

from wireup import injectable

from ..operations import SirenDocument
from .model import McpPresentation


@injectable
@dataclass(frozen=True)
class PresentationService:
    def present(self, document: SirenDocument) -> McpPresentation:
        summary = document.detail if document.is_error else document.title
        return McpPresentation(
            markdown=summary or "Enclosure result",
            structured_content=document.document,
            is_error=document.is_error,
        )

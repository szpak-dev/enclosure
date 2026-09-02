import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from pydantic import JsonValue
from wireup import injectable

from enclosure.shared import TemplateService

from ..bootstrap import AgentBootstrapService
from ..operations import SirenDocument
from .model import McpPresentation


@injectable
@dataclass(frozen=True)
class PresentationService:
    bootstrap: AgentBootstrapService
    templates: TemplateService

    MAX_TEXT_BYTES: ClassVar[int] = 16_384
    MAX_STRUCTURED_BYTES: ClassVar[int] = 8_192

    def present(self, document: SirenDocument) -> McpPresentation:
        if document.is_error:
            return self._compatible(document)
        try:
            context = {
                "bootstrap": self.bootstrap.load(),
                "document": document.document,
                "properties": self._properties(document),
            }
            markdown = self.templates.render(
                "enclosure.mcp.services.presentation",
                f"{document.operation_id}.md.jinja",
                context,
            ).strip()
            envelope = json.loads(
                self.templates.render(
                    "enclosure.mcp.services.presentation",
                    f"{document.operation_id}.json.jinja",
                    context,
                )
            )
            structured_content = self._structured_content(envelope)
            is_error = self._is_error(envelope)
        except (json.JSONDecodeError, TypeError, ValueError):
            return self._compatible(document)
        return self._bounded(document.operation_id, markdown, structured_content, is_error)

    def _properties(self, document: SirenDocument) -> Mapping[str, JsonValue]:
        properties = document.document.get("properties")
        if not isinstance(properties, Mapping):
            raise ValueError("The Siren document has no properties object.")
        return properties

    def _structured_content(self, envelope: JsonValue) -> Mapping[str, JsonValue]:
        if not isinstance(envelope, Mapping):
            raise ValueError("The presentation envelope must be an object.")
        structured_content = envelope.get("structured_content")
        if not isinstance(structured_content, Mapping):
            raise ValueError("The presentation envelope has no structured content.")
        return structured_content

    def _is_error(self, envelope: JsonValue) -> bool:
        if not isinstance(envelope, Mapping):
            raise ValueError("The presentation envelope must be an object.")
        is_error = envelope.get("is_error")
        if not isinstance(is_error, bool):
            raise ValueError("The presentation envelope has no error state.")
        return is_error

    def _bounded(
        self,
        operation_id: str,
        markdown: str,
        structured_content: Mapping[str, JsonValue],
        is_error: bool,
    ) -> McpPresentation:
        text_bytes = len(markdown.encode("utf-8"))
        structured_bytes = len(
            json.dumps(
                structured_content,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        if text_bytes <= self.MAX_TEXT_BYTES and structured_bytes <= self.MAX_STRUCTURED_BYTES:
            return McpPresentation(
                markdown=markdown,
                structured_content=structured_content,
                is_error=is_error,
            )
        return McpPresentation(
            markdown=(
                "Enclosure could not produce a complete bounded agent presentation. "
                "Read the operation through REST or Siren without treating this result as complete."
            ),
            structured_content={
                "operation_id": operation_id,
                "status": "incomplete",
                "reason": "presentation_budget_exceeded",
                "text_bytes": text_bytes,
                "text_budget": self.MAX_TEXT_BYTES,
                "structured_bytes": structured_bytes,
                "structured_budget": self.MAX_STRUCTURED_BYTES,
            },
            is_error=True,
        )

    def _compatible(self, document: SirenDocument) -> McpPresentation:
        summary = document.detail if document.is_error else document.title
        return McpPresentation(
            markdown=summary or "Enclosure result",
            structured_content=document.document,
            is_error=document.is_error,
        )

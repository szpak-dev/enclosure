import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from pydantic import JsonValue, ValidationError
from wireup import injectable

from enclosure.shared import TemplateService

from ..bootstrap import AgentBootstrapService
from ..operations import SirenDocument, ToolCatalogue
from .errors import PresentationTemplateNotFound
from .model import (
    McpPresentation,
    PresentationEnvelope,
    PresentationStatus,
    PresentationTemplate,
)
from .repository import PresentationTemplateRepository


@injectable
@dataclass(frozen=True)
class PresentationService:
    bootstrap: AgentBootstrapService
    templates: TemplateService
    repository: PresentationTemplateRepository

    MAX_TEXT_BYTES: ClassVar[int] = 16_384
    MAX_STRUCTURED_BYTES: ClassVar[int] = 8_192
    MAX_OPERATION_ID_BYTES: ClassVar[int] = 256

    def present(self, document: SirenDocument) -> McpPresentation:
        if document.is_error:
            return self._fallback(document, PresentationStatus.ERROR, document.detail or "Operation failed.")
        try:
            template = self.repository.find(document.operation_id)
            return self._render(document, template)
        except (
            ImportError,
            json.JSONDecodeError,
            OSError,
            PresentationTemplateNotFound,
            TypeError,
            ValidationError,
            ValueError,
        ):
            return self._fallback(
                document,
                PresentationStatus.INCOMPLETE,
                "The operation completed, but no complete bounded MCP presentation is available.",
            )

    def strategies(self, catalogue: ToolCatalogue) -> tuple[PresentationTemplate, ...]:
        return self.repository.find_all(tuple(tool.name for tool in catalogue.tools))

    def _render(self, document: SirenDocument, template: PresentationTemplate) -> McpPresentation:
        properties = document.document.get("properties")
        if not isinstance(properties, Mapping):
            properties = {}
        context = {
            "bootstrap": self.bootstrap.load(),
            "document": document.document,
            "operation_id": document.operation_id,
            "properties": properties,
            "summary": document.detail or document.title or "Enclosure result",
        }
        markdown = self.templates.render(
            template.package,
            template.markdown_path,
            context,
        ).strip()
        envelope = PresentationEnvelope.model_validate(
            json.loads(
                self.templates.render(
                    template.package,
                    template.structured_path,
                    context,
                )
            )
        )
        if envelope.operation_id != document.operation_id:
            raise ValueError("The presentation envelope does not match the invoked operation.")
        return self._bounded(markdown, envelope)

    def _bounded(self, markdown: str, envelope: PresentationEnvelope) -> McpPresentation:
        if self._within_budget(markdown, envelope):
            return McpPresentation(markdown=markdown, structured_content=envelope)
        status = (
            PresentationStatus.ERROR if envelope.status is PresentationStatus.ERROR else PresentationStatus.INCOMPLETE
        )
        return self._terminal(envelope.operation_id, status, "presentation_budget_exceeded")

    def _fallback(
        self,
        document: SirenDocument,
        status: PresentationStatus,
        summary: str,
    ) -> McpPresentation:
        properties = document.document.get("properties")
        safe_data: dict[str, JsonValue] = {}
        if isinstance(properties, Mapping):
            for name in (
                "id",
                "project_id",
                "workspace_id",
                "title",
                "state",
                "status",
                "revision",
                "version",
                "root",
                "authority",
                "provenance",
                "created_at",
                "updated_at",
            ):
                value = properties.get(name)
                if isinstance(value, str | int | float | bool):
                    safe_data[name] = value
        safe_data["classes"] = list(document.classes)
        safe_data["reason"] = "operation_failed" if status is PresentationStatus.ERROR else "presentation_incomplete"
        context = {
            "data": safe_data,
            "follow_ups": [],
            "operation_id": document.operation_id,
            "status": status.value,
            "summary": summary,
        }
        try:
            template = self.repository.error() if status is PresentationStatus.ERROR else self.repository.incomplete()
            markdown = self.templates.render(
                template.package,
                template.markdown_path,
                context,
            ).strip()
            envelope = PresentationEnvelope.model_validate(
                json.loads(
                    self.templates.render(
                        template.package,
                        template.structured_path,
                        context,
                    )
                )
            )
            return self._bounded(markdown, envelope)
        except (
            ImportError,
            json.JSONDecodeError,
            OSError,
            PresentationTemplateNotFound,
            TypeError,
            ValidationError,
            ValueError,
        ):
            return self._terminal(document.operation_id, status, "presentation_fallback_failed")

    def _terminal(
        self,
        operation_id: str,
        status: PresentationStatus,
        reason: str,
    ) -> McpPresentation:
        markdown = "Enclosure returned a bounded operation receipt. Use REST or Siren for complete detail."
        envelope = PresentationEnvelope(
            operation_id=self._bounded_operation_id(operation_id),
            status=status,
            summary="The complete MCP presentation is unavailable.",
            data={"reason": reason},
            follow_ups=(),
        )
        if self._within_budget(markdown, envelope):
            return McpPresentation(markdown=markdown, structured_content=envelope)
        minimal = PresentationEnvelope(
            operation_id="",
            status=status,
            summary="",
            data={},
            follow_ups=(),
        )
        if not self._within_budget("", minimal):
            raise RuntimeError("The minimal MCP presentation exceeds its output budget.")
        return McpPresentation(markdown="", structured_content=minimal)

    def _within_budget(self, markdown: str, envelope: PresentationEnvelope) -> bool:
        text_bytes = len(markdown.encode("utf-8"))
        structured_bytes = len(
            json.dumps(
                envelope.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        return text_bytes <= self.MAX_TEXT_BYTES and structured_bytes <= self.MAX_STRUCTURED_BYTES

    def _bounded_operation_id(self, operation_id: str) -> str:
        return operation_id.encode("utf-8")[: self.MAX_OPERATION_ID_BYTES].decode("utf-8", errors="ignore")

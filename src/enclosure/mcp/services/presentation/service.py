import json
from dataclasses import dataclass

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
from .projection import SirenProjectionService
from .recovery import PresentationRecoveryService
from .repository import PresentationTemplateRepository


@injectable
@dataclass(frozen=True)
class PresentationService:
    bootstrap: AgentBootstrapService
    templates: TemplateService
    repository: PresentationTemplateRepository
    projection: SirenProjectionService
    recovery: PresentationRecoveryService

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
        context = {
            "bootstrap": self.bootstrap.load(),
            "content_limit": self.recovery.PREFERRED_CONTENT_CHARACTERS,
            "data": self.projection.project(document),
            "document": document.document,
            "follow_ups": [
                navigation.model_dump(mode="json")
                for navigation in (*document.follow_ups, *document.continuations, *document.verifications)
            ],
            "invocation": document.arguments,
            "operation_id": document.operation_id,
            "properties": document.document.get("properties", {}),
            "summary": document.detail or document.title or "Enclosure result",
        }
        envelope = PresentationEnvelope.model_validate(
            json.loads(
                self.templates.render(
                    template.package,
                    template.structured_path,
                    context,
                )
            )
        )
        markdown = self.templates.render(
            template.package,
            template.markdown_path,
            context,
        ).strip()
        if envelope.operation_id != document.operation_id:
            raise ValueError("The presentation envelope does not match the invoked operation.")
        return self.recovery.bound(document, markdown, envelope)

    def _fallback(
        self,
        document: SirenDocument,
        status: PresentationStatus,
        summary: str,
    ) -> McpPresentation:
        safe_data: dict[str, JsonValue] = dict(self.projection.project(document))
        safe_data["classes"] = list(document.classes)
        safe_data["reason"] = "operation_failed" if status is PresentationStatus.ERROR else "presentation_incomplete"
        context = {
            "data": safe_data,
            "follow_ups": [
                navigation.model_dump(mode="json")
                for navigation in (*document.follow_ups, *document.continuations, *document.verifications)
            ],
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
            return self.recovery.bound(document, markdown, envelope)
        except (
            ImportError,
            json.JSONDecodeError,
            OSError,
            PresentationTemplateNotFound,
            TypeError,
            ValidationError,
            ValueError,
        ):
            return self.recovery.terminal(document.operation_id, status, "presentation_fallback_failed")

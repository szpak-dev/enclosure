import json
from dataclasses import dataclass
from typing import ClassVar, cast

from pydantic import JsonValue
from wireup import injectable

from ..operations import SirenDocument, ToolInvocation
from .model import McpPresentation, PresentationEnvelope, PresentationStatus


@injectable
@dataclass(frozen=True)
class PresentationRecoveryService:
    MAX_TEXT_BYTES: ClassVar[int] = 16_384
    MAX_STRUCTURED_BYTES: ClassVar[int] = 8_192
    MAX_OPERATION_ID_BYTES: ClassVar[int] = 256
    PREFERRED_CONTENT_CHARACTERS: ClassVar[int] = MAX_STRUCTURED_BYTES // 2

    def bound(
        self,
        document: SirenDocument,
        markdown: str,
        envelope: PresentationEnvelope,
    ) -> McpPresentation:
        if self.within_budget(markdown, envelope):
            return McpPresentation(markdown=markdown, structured_content=envelope)
        if self.structured_within_budget(envelope):
            return McpPresentation(markdown=envelope.summary, structured_content=envelope)
        if envelope.status is PresentationStatus.ERROR:
            return self.terminal(envelope.operation_id, PresentationStatus.ERROR, "presentation_budget_exceeded")
        if self._page_recovery_available(envelope):
            return self._paged(document, envelope)
        if "collection" in document.classes:
            return self._collection_receipt(envelope, (), {})
        return self._receipt(document, envelope)

    def terminal(
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
        if self.within_budget(markdown, envelope):
            return McpPresentation(markdown=markdown, structured_content=envelope)
        minimal = PresentationEnvelope(
            operation_id="",
            status=status,
            summary="",
            data={},
            follow_ups=(),
        )
        if not self.within_budget("", minimal):
            raise RuntimeError("The minimal MCP presentation exceeds its output budget.")
        return McpPresentation(markdown="", structured_content=minimal)

    def within_budget(self, markdown: str, envelope: PresentationEnvelope) -> bool:
        return len(markdown.encode("utf-8")) <= self.MAX_TEXT_BYTES and self.structured_within_budget(envelope)

    def structured_within_budget(self, envelope: PresentationEnvelope) -> bool:
        return self._encoded_size(envelope.model_dump(mode="json")) <= self.MAX_STRUCTURED_BYTES

    def _paged(self, document: SirenDocument, envelope: PresentationEnvelope) -> McpPresentation:
        offset = cast(int, document.arguments.get("offset", envelope.data.get("offset", 0)))
        argument_limit = cast(int, document.arguments.get("limit", 0))
        requested_limit = argument_limit if argument_limit > 0 else cast(int, envelope.data["limit"])
        retry_limit = max(1, requested_limit // 2)
        if retry_limit == requested_limit:
            if "collection" in document.classes:
                return self._collection_receipt(envelope, (), {})
            return self._receipt(document, envelope)
        retry = ToolInvocation(
            operation_id=document.operation_id,
            arguments={
                **document.arguments,
                "limit": retry_limit,
            },
        )
        recovery_data: dict[str, JsonValue] = {
            "reason": "presentation_budget_exceeded",
            "offset": offset,
            "requested_limit": requested_limit,
            "retry_limit": retry_limit,
        }
        if "collection" in document.classes:
            return self._collection_receipt(envelope, (retry,), recovery_data)
        recovery = PresentationEnvelope(
            operation_id=envelope.operation_id,
            status=PresentationStatus.INCOMPLETE,
            summary="The operation completed, but this page needs a smaller presentation window.",
            data=recovery_data,
            follow_ups=(retry,),
        )
        markdown = (
            "The operation completed, but its presentation exceeded the MCP budget. "
            "Retry the supplied operation at the same offset with the smaller limit."
        )
        if self.within_budget(markdown, recovery):
            return McpPresentation(markdown=markdown, structured_content=recovery)
        return self.terminal(envelope.operation_id, PresentationStatus.INCOMPLETE, "presentation_budget_exceeded")

    def _collection_receipt(
        self,
        envelope: PresentationEnvelope,
        follow_ups: tuple[ToolInvocation, ...],
        recovery_data: dict[str, JsonValue],
    ) -> McpPresentation:
        summary = (
            "The operation completed and returned a safe prefix plus a smaller-window retry."
            if follow_ups
            else "The operation completed and returned a safe prefix of the collection."
        )
        items = cast(list[JsonValue], envelope.data["items"])
        data: dict[str, JsonValue] = {
            "reason": "presentation_budget_exceeded",
            "count": envelope.data["count"],
            "items": [],
            **recovery_data,
        }
        prefix: list[JsonValue] = []
        for item in items:
            candidate_prefix = [*prefix, item]
            candidate = PresentationEnvelope(
                operation_id=envelope.operation_id,
                status=PresentationStatus.INCOMPLETE,
                summary=summary,
                data={**data, "items": candidate_prefix, "returned_count": len(candidate_prefix)},
                follow_ups=follow_ups,
            )
            if not self.structured_within_budget(candidate):
                break
            prefix = candidate_prefix
        if not prefix and items:
            return self._receipt_data(envelope, follow_ups)
        recovery = PresentationEnvelope(
            operation_id=envelope.operation_id,
            status=PresentationStatus.INCOMPLETE,
            summary=summary,
            data={**data, "items": prefix, "returned_count": len(prefix)},
            follow_ups=follow_ups,
        )
        markdown = "The operation completed, but only a bounded prefix fits in the MCP presentation."
        if self.within_budget(markdown, recovery):
            return McpPresentation(markdown=markdown, structured_content=recovery)
        return self.terminal(envelope.operation_id, PresentationStatus.INCOMPLETE, "presentation_budget_exceeded")

    def _receipt(self, document: SirenDocument, envelope: PresentationEnvelope) -> McpPresentation:
        follow_ups = document.verifications[:1]
        return self._receipt_data(envelope, follow_ups)

    def _receipt_data(
        self,
        envelope: PresentationEnvelope,
        follow_ups: tuple[ToolInvocation, ...],
    ) -> McpPresentation:
        summary = (
            "The operation completed; use the supplied verification operation for authoritative state."
            if follow_ups
            else "The operation completed and a compact receipt was retained."
        )
        data: dict[str, JsonValue] = {"reason": "presentation_budget_exceeded"}
        candidates = sorted(
            ((name, value) for name, value in envelope.data.items() if name not in data),
            key=lambda item: (self._encoded_size(item[1]), item[0]),
        )
        for name, value in candidates:
            candidate = PresentationEnvelope(
                operation_id=envelope.operation_id,
                status=PresentationStatus.INCOMPLETE,
                summary=summary,
                data={**data, name: value},
                follow_ups=follow_ups,
            )
            if self.structured_within_budget(candidate):
                data[name] = value
        recovery = PresentationEnvelope(
            operation_id=envelope.operation_id,
            status=PresentationStatus.INCOMPLETE,
            summary=summary,
            data=data,
            follow_ups=follow_ups,
        )
        markdown = "The operation completed, but its full presentation exceeded the MCP budget."
        if self.within_budget(markdown, recovery):
            return McpPresentation(markdown=markdown, structured_content=recovery)
        return self.terminal(envelope.operation_id, PresentationStatus.INCOMPLETE, "presentation_budget_exceeded")

    def _page_recovery_available(self, envelope: PresentationEnvelope) -> bool:
        return "limit" in envelope.data and "has_more" in envelope.data

    def _encoded_size(self, value: JsonValue) -> int:
        return len(
            json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )

    def _bounded_operation_id(self, operation_id: str) -> str:
        return operation_id.encode("utf-8")[: self.MAX_OPERATION_ID_BYTES].decode("utf-8", errors="ignore")

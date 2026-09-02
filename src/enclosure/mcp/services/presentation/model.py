from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import JsonValue

WorkspaceContextStatus = Literal["ready", "incomplete", "conflicted"]


@dataclass(frozen=True, slots=True)
class McpPresentation:
    markdown: str
    structured_content: Mapping[str, JsonValue] | None
    is_error: bool


@dataclass(frozen=True, slots=True)
class WorkspaceContextReceipt:
    status: WorkspaceContextStatus
    project_id: str
    bootstrap_revision: str
    guidance_ids: tuple[str, ...]
    required_check_ids: tuple[str, ...]
    omitted_count: int

    def as_json(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "project_id": self.project_id,
            "bootstrap_revision": self.bootstrap_revision,
            "guidance_ids": list(self.guidance_ids),
            "required_check_ids": list(self.required_check_ids),
            "omitted_count": self.omitted_count,
        }

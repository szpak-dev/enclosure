from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ...errors import DiagramsError


@injectable
@dataclass(frozen=True)
class DiagramValidationService:
    def diagram_set(self, data: Mapping[str, str], *, require_title: bool = False) -> dict[str, str]:
        self._allowed_fields(data, {"title", "description"}, "diagram set")
        validated: dict[str, str] = {}
        if "title" in data:
            validated["title"] = self._required_string(data["title"], "Diagram set title", maximum=255)
        elif require_title:
            raise DiagramsError("Diagram set title is required.")
        if "description" in data:
            validated["description"] = data["description"]
        return validated

    def diagram_creation(self, data: Mapping[str, str]) -> dict[str, str]:
        self._allowed_fields(data, {"title", "kind"}, "diagram")
        return {
            "title": self._required_string(data["title"], "Diagram title", maximum=255),
            "kind": self._required_string(data["kind"], "Diagram kind", maximum=64),
        }

    def diagram_title(self, value: str) -> str:
        return self._required_string(value, "Diagram title", maximum=255)

    def expected_revision(self, value: int) -> int:
        if value < 1:
            raise DiagramsError("Expected diagram revision must be a positive integer.")
        return value

    def _allowed_fields(self, data: Mapping[str, str], allowed: set[str], subject: str) -> None:
        unknown = set(data) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise DiagramsError(f"Unsupported {subject} fields: {names}.")

    def _required_string(self, value: str, name: str, *, maximum: int) -> str:
        normalized = value.strip()
        if not normalized:
            raise DiagramsError(f"{name} must be a non-empty string.")
        if len(normalized) > maximum:
            raise DiagramsError(f"{name} must not exceed {maximum} characters.")
        return normalized

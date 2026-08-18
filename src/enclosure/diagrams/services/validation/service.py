from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ...errors import DiagramsError


@injectable
@dataclass(frozen=True)
class DiagramValidationService:
    def diagram_set(self, data: Mapping[str, object], *, require_title: bool = False) -> dict[str, str]:
        self._allowed_fields(data, {"title", "description"}, "diagram set")
        validated: dict[str, str] = {}
        if "title" in data:
            validated["title"] = self._required_string(data["title"], "Diagram set title", maximum=255)
        elif require_title:
            raise DiagramsError("Diagram set title is required.")
        if "description" in data:
            validated["description"] = self._string(data["description"], "Diagram set description")
        return validated

    def diagram_creation(self, data: Mapping[str, object]) -> dict[str, str]:
        self._allowed_fields(data, {"title", "kind"}, "diagram")
        return {
            "title": self._required_string(data.get("title"), "Diagram title", maximum=255),
            "kind": self._required_string(data.get("kind"), "Diagram kind", maximum=64),
        }

    @staticmethod
    def expected_revision(value: object) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise DiagramsError("Expected diagram revision must be a positive integer.")
        return value

    @staticmethod
    def _allowed_fields(data: Mapping[str, object], allowed: set[str], subject: str) -> None:
        unknown = set(data) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise DiagramsError(f"Unsupported {subject} fields: {names}.")

    @classmethod
    def _required_string(cls, value: object, name: str, *, maximum: int) -> str:
        normalized = cls._string(value, name).strip()
        if not normalized:
            raise DiagramsError(f"{name} must be a non-empty string.")
        if len(normalized) > maximum:
            raise DiagramsError(f"{name} must not exceed {maximum} characters.")
        return normalized

    @staticmethod
    def _string(value: object, name: str) -> str:
        if not isinstance(value, str):
            raise DiagramsError(f"{name} must be a string.")
        return value

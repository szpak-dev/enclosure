from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue, TypeAdapter, ValidationError
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

    def interactions(self, value: object) -> dict[str, dict[str, object]]:
        if not isinstance(value, Mapping):
            raise DiagramsError("Diagram interactions must be an object keyed by element ID.")
        interactions: dict[str, dict[str, object]] = {}
        for element_id, interaction in value.items():
            target = self._required_string(element_id, "Interaction element ID", maximum=255)
            interactions[target] = self._interaction(interaction, target)
        return interactions

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

    def _interaction(self, value: object, element_id: str) -> dict[str, object]:
        if not isinstance(value, Mapping):
            raise DiagramsError(f"Interaction for element {element_id!r} must be an object.")
        action = value.get("action")
        if action == "navigate":
            self._allowed_fields(value, {"action", "target"}, "navigate interaction")
            target = self._required_string(value.get("target"), "Navigation target", maximum=2048)
            if not target.startswith("/") or target.startswith("//") or "\\" in target:
                raise DiagramsError("Navigation target must be an application-relative path.")
            return {"action": action, "target": target}
        if action == "show_details":
            self._allowed_fields(value, {"action", "payload"}, "show-details interaction")
            try:
                payload = TypeAdapter(dict[str, JsonValue]).validate_python(value.get("payload"), strict=True)
            except ValidationError as error:
                raise DiagramsError("Interaction details payload must be a JSON object.") from error
            return {"action": action, "payload": payload}
        raise DiagramsError(f"Unsupported interaction action for element {element_id!r}: {action!r}.")

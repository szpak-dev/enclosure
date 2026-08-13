from collections.abc import Mapping
from dataclasses import dataclass

from django.db.models import QuerySet
from wireup import injectable

from ...errors import DiagramsError
from ...models import DiagramSet
from ..repository import DiagramsRepository


@injectable
@dataclass(frozen=True)
class DiagramSetService:
    repository: DiagramsRepository

    def create(self, data: Mapping[str, object]) -> DiagramSet:
        return self.repository.create_set(self._validate(data, require_title=True))

    def get(self, id: str) -> DiagramSet:
        try:
            return self.repository.get_set(id)
        except DiagramSet.DoesNotExist as error:
            raise DiagramsError(f"Diagram set {id!r} does not exist.") from error

    def find_all(self) -> QuerySet[DiagramSet]:
        return self.repository.find_all_sets()

    def update(self, id: str, data: Mapping[str, object]) -> DiagramSet:
        self.get(id)
        return self.repository.update_set(id, self._validate(data))

    def delete(self, id: str) -> None:
        self.get(id)
        self.repository.delete_set(id)

    @staticmethod
    def _validate(data: Mapping[str, object], *, require_title: bool = False) -> dict[str, str]:
        unknown = set(data) - {"title", "description"}
        if unknown:
            names = ", ".join(sorted(unknown))
            raise DiagramsError(f"Unsupported diagram set fields: {names}.")

        validated: dict[str, str] = {}
        if "title" in data:
            title = data["title"]
            if not isinstance(title, str) or not title.strip():
                raise DiagramsError("Diagram set title must be a non-empty string.")
            if len(title.strip()) > 255:
                raise DiagramsError("Diagram set title must not exceed 255 characters.")
            validated["title"] = title.strip()
        elif require_title:
            raise DiagramsError("Diagram set title is required.")

        if "description" in data:
            description = data["description"]
            if not isinstance(description, str):
                raise DiagramsError("Diagram set description must be a string.")
            validated["description"] = description

        return validated

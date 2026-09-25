from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ...operations import SirenDocument


@injectable
@dataclass(frozen=True)
class SirenProjectionService:
    def project(self, document: SirenDocument) -> Mapping[str, JsonValue]:
        if "collection" in document.classes:
            entities = document.document.get("entities", ())
            data = self._properties(document.document)
            data.update(self._collection(entities))
        else:
            data = self._properties(document.document)
        self._navigation(document.document, data)
        return data

    def _collection(
        self,
        entities: Sequence[Mapping[str, JsonValue]],
    ) -> dict[str, JsonValue]:
        items: list[JsonValue] = []
        for entity in entities:
            item = self._properties(entity)
            self._self_link(entity, item)
            items.append(item)
        return {
            "count": len(entities),
            "items": items,
        }

    def _navigation(self, document: Mapping[str, JsonValue], data: dict[str, JsonValue]) -> None:
        actions = [
            {
                "name": action["name"],
                "method": action["method"],
                "href": action["href"],
            }
            for action in document.get("actions", ())
        ]
        links = [
            {name: link[name] for name in ("rel", "title", "href") if name in link}
            for link in document.get("links", ())
        ]
        if actions:
            data["actions"] = actions
        if links:
            data["links"] = links

    def _self_link(self, entity: Mapping[str, JsonValue], item: dict[str, JsonValue]) -> None:
        for link in entity.get("links", ()):
            if "self" in link["rel"]:
                item["href"] = link["href"]
                return

    def _properties(self, entity: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        return {str(name): item for name, item in entity.get("properties", {}).items()}

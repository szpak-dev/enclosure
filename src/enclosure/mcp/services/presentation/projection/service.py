from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from pydantic import JsonValue
from wireup import injectable

from ...operations import SirenDocument


@injectable
@dataclass(frozen=True)
class SirenProjectionService:
    MAX_STRING_CHARACTERS: ClassVar[int] = 512

    def project(self, document: SirenDocument) -> Mapping[str, JsonValue]:
        entities = document.document.get("entities")
        if "collection" in document.classes and isinstance(entities, list | tuple):
            data = self._collection(entities)
        else:
            properties = document.document.get("properties")
            projected = self._value(properties if isinstance(properties, Mapping) else {})
            data = projected if isinstance(projected, dict) else {}
        self._navigation(document.document, data)
        return data

    def _collection(self, entities: list[JsonValue] | tuple[JsonValue, ...]) -> dict[str, JsonValue]:
        items = []
        for entity in entities:
            if not isinstance(entity, Mapping):
                continue
            properties = entity.get("properties")
            projected = self._value(properties if isinstance(properties, Mapping) else {})
            item = projected if isinstance(projected, dict) else {}
            self._self_link(entity, item)
            items.append(item)
        return {
            "count": len(entities),
            "items": items,
        }

    def _navigation(self, document: Mapping[str, JsonValue], data: dict[str, JsonValue]) -> None:
        actions = []
        for action in self._mappings(document.get("actions")):
            projected = self._named_values(action, ("name", "method", "href"))
            if projected:
                actions.append(projected)
        links = []
        for link in self._mappings(document.get("links")):
            projected = self._named_values(link, ("rel", "title", "href"))
            if projected:
                links.append(projected)
        if actions:
            data["actions"] = actions
        if links:
            data["links"] = links

    def _self_link(self, entity: Mapping[str, JsonValue], item: dict[str, JsonValue]) -> None:
        for link in self._mappings(entity.get("links")):
            relations = link.get("rel")
            href = link.get("href")
            if isinstance(relations, list | tuple) and "self" in relations and isinstance(href, str):
                item["href"] = href
                return

    def _named_values(
        self,
        source: Mapping[str, JsonValue],
        names: tuple[str, ...],
    ) -> dict[str, JsonValue]:
        projected = {}
        for name in names:
            if name not in source:
                continue
            value = self._value(source[name])
            if value is not None:
                projected[name] = value
        return projected

    def _value(self, value: JsonValue) -> JsonValue:
        if isinstance(value, Mapping):
            projected = {}
            for name, item in value.items():
                result = self._value(item)
                if result is not None:
                    projected[str(name)] = result
            return projected
        if isinstance(value, str):
            if len(value) <= self.MAX_STRING_CHARACTERS:
                return value
            return f"{value[: self.MAX_STRING_CHARACTERS - 3]}..."
        if isinstance(value, list | tuple):
            return [self._value(item) for item in value]
        return value

    def _mappings(self, value: JsonValue) -> tuple[Mapping[str, JsonValue], ...]:
        if not isinstance(value, list | tuple):
            return ()
        return tuple(item for item in value if isinstance(item, Mapping))

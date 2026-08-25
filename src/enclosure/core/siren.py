from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from sirenity import SirenResponseContext


@dataclass(frozen=True)
class SirenRelationshipDefinition:
    source_operation: str
    relation: tuple[str, ...]
    title: str
    path_template: str
    source_property: str

    def build(self, result: Mapping[str, JsonValue], base_url: str) -> dict[str, JsonValue]:
        return {
            "rel": list(self.relation),
            "title": self.title,
            "href": f"{base_url.rstrip('/')}{self.path_template.format(value=result[self.source_property])}",
        }


@dataclass(frozen=True)
class SirenRelationshipRegistry:
    definitions: tuple[SirenRelationshipDefinition, ...]

    def links_for(
        self,
        operation_id: str | None,
        result: JsonValue,
        base_url: str,
    ) -> tuple[dict[str, JsonValue], ...]:
        if operation_id is None or not isinstance(result, Mapping):
            return ()
        return tuple(
            definition.build(result, base_url)
            for definition in self.definitions
            if definition.source_operation == operation_id
        )


RELATIONSHIPS = SirenRelationshipRegistry(
    definitions=(
        SirenRelationshipDefinition(
            source_operation="get_project",
            relation=("related",),
            title="Architecture configuration",
            path_template="/siren/projects/{value}/architecture-configuration",
            source_property="id",
        ),
    )
)


@dataclass(frozen=True)
class EnclosureRelationshipsProfile:
    relationships: SirenRelationshipRegistry = RELATIONSHIPS

    def apply(
        self,
        operation_id: str | None,
        operation_input: object,
        operation_inputs: Mapping[str, object],
        document: Mapping[str, JsonValue],
        context: SirenResponseContext,
    ) -> Mapping[str, JsonValue]:
        links = self.relationships.links_for(operation_id, context.result, context.base_url)
        if not links:
            return document
        return {**document, "links": [*document["links"], *links]}

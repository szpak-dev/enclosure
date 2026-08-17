from pydantic import JsonValue
from sirenity import SirenAdapterPolicy, SirenRelationship, SirenScope


class EnclosureSirenPolicy:
    diagram_set_representations = frozenset(
        {
            "create_diagram_set",
            "get_diagram_set",
            "update_diagram_set",
        }
    )

    def select(
        self,
        operation_id: str | None,
        status: int,
        request: object,
        result: JsonValue,
    ) -> SirenAdapterPolicy:
        if operation_id not in self.diagram_set_representations or status >= 300:
            return SirenAdapterPolicy(all_capabilities=True)
        return SirenAdapterPolicy(
            all_capabilities=True,
            relationships=(
                SirenRelationship(
                    rel=("collection",),
                    resource="diagram",
                    scope=SirenScope.COLLECTION,
                    path_values={"diagram_set_id": result["id"]},
                ),
            ),
        )

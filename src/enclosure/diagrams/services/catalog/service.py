from dataclasses import dataclass

from wireup import injectable

from ..mermaiden import MermaidenService


@injectable
@dataclass(frozen=True)
class DiagramCatalogService:
    mermaiden: MermaidenService

    def find_kinds(self) -> tuple[dict[str, str], ...]:
        return self.mermaiden.find_kinds()

    def describe_kind(self, kind: str) -> dict[str, object]:
        return self.mermaiden.describe_kind(kind)

    def get_command_schema(self, kind: str, operation: str) -> dict[str, object]:
        return self.mermaiden.get_command_schema(kind, operation)

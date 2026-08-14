from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from enclosure.scaffoldings.services import RenderedFile, ScaffoldingService


@injectable
@dataclass(frozen=True)
class ScaffoldingsAdapter:
    scaffoldings: ScaffoldingService

    def check_scaffolding_existence(self, scaffolding_id: str) -> None:
        self.scaffoldings.get(scaffolding_id)

    def render(
        self,
        scaffolding_id: str,
        parameters: Mapping[str, JsonValue],
    ) -> tuple[RenderedFile, ...]:
        return self.scaffoldings.render_files(scaffolding_id, parameters)

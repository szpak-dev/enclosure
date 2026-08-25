from collections.abc import Mapping
from dataclasses import dataclass

from django.db.models import QuerySet
from pydantic import JsonValue
from wireup import injectable

from enclosure.shared import SourceCodePackage, SourceCodeRenderer

from ..models import Scaffolding
from .renderings import RenderedFile, RenderingService
from .repository import ScaffoldingRepository
from .spec.service import ScaffoldingSpecService


@injectable
@dataclass(frozen=True)
class ScaffoldingService:
    repository: ScaffoldingRepository
    renderer: SourceCodeRenderer
    renderings: RenderingService
    spec_service: ScaffoldingSpecService

    def create(self, data: dict) -> Scaffolding:
        self.spec_service.validate(data["spec"])
        return self.repository.save(**data)

    def get(self, id: str) -> Scaffolding:
        return self.repository.get(id)

    def find_all(self) -> QuerySet[Scaffolding]:
        return self.repository.find_all()

    def search(self, name: str, language_id: str) -> QuerySet[Scaffolding]:
        return self.repository.search(name, language_id)

    def update(self, id: str, data: dict) -> Scaffolding:
        self.spec_service.validate(data["spec"])
        return self.repository.update(id, **data)

    def delete(self, id: str) -> None:
        self.repository.delete(id)

    def render(self, id: str, parameters: Mapping[str, JsonValue]) -> SourceCodePackage:
        prepared = self.spec_service.prepare(self.get(id).spec, parameters)
        return self.renderer.render(prepared.source, prepared.parameters)

    def render_files(self, id: str, parameters: Mapping[str, JsonValue]) -> tuple[RenderedFile, ...]:
        return self.renderings.render(self.get(id).spec, parameters)

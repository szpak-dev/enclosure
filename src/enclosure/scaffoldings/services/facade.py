from collections.abc import Mapping
from dataclasses import dataclass

from django.db.models import QuerySet
from pydantic import JsonValue
from wireup import injectable

from enclosure.shared.source_code.package import SourceCodePackage

from ..models import Scaffolding
from .content.model import ScaffoldingDetail, ScaffoldingPage, ScaffoldingTemplateContent, TemplateManifestPage
from .content.service import ScaffoldingContentService
from .renderings.model import RenderedFile, RenderedFileContent, RenderingPage
from .renderings.service import RenderingService
from .repository import ScaffoldingRepository
from .spec.service import ScaffoldingSpecService


@injectable
@dataclass(frozen=True)
class ScaffoldingService:
    repository: ScaffoldingRepository
    renderings: RenderingService
    spec_service: ScaffoldingSpecService
    content: ScaffoldingContentService

    def create(self, data: dict) -> ScaffoldingDetail:
        self.spec_service.validate(data["spec"])
        return self.content.detail(self.repository.save(**data))

    def get(self, id: str) -> Scaffolding:
        return self.repository.get(id)

    def find_all(self) -> QuerySet[Scaffolding]:
        return self.repository.find_all()

    def find_page(self, offset: int, limit: int) -> ScaffoldingPage:
        found = self.repository.find_page(offset, limit)
        items = found[:limit]
        return ScaffoldingPage(
            items=items,
            has_more=len(found) > limit,
            next_offset=offset + len(items),
            limit=limit,
        )

    def search(self, name: str, language_id: str, limit: int) -> QuerySet[Scaffolding]:
        return self.repository.search(name, language_id, limit)

    def get_detail(self, id: str) -> ScaffoldingDetail:
        return self.content.detail(self.get(id))

    def update(self, id: str, data: dict) -> ScaffoldingDetail:
        self.spec_service.validate(data["spec"])
        return self.content.detail(self.repository.update(id, **data))

    def delete(self, id: str) -> None:
        self.repository.delete(id)

    def render(self, id: str, parameters: Mapping[str, JsonValue]) -> SourceCodePackage:
        scaffolding = self.get(id)
        spec = self.spec_service.validate(scaffolding.spec)
        files = self.renderings.render(spec, parameters)
        return SourceCodePackage(
            language=spec.language,
            package={"files": {file.path: file.content for file in files}},
        )

    def render_files(self, id: str, parameters: Mapping[str, JsonValue]) -> tuple[RenderedFile, ...]:
        return self.renderings.render(self.get(id).spec, parameters)

    def read_template(
        self,
        id: str,
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> ScaffoldingTemplateContent:
        return self.content.read_template(self.get(id), path, expected_revision, offset, limit)

    def read_template_manifests(
        self,
        id: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> TemplateManifestPage:
        return self.content.read_template_manifests(self.get(id), expected_revision, offset, limit)

    def render_page(
        self,
        id: str,
        parameters: Mapping[str, JsonValue],
        offset: int,
        limit: int,
    ) -> RenderingPage:
        scaffolding = self.get(id)
        return self.renderings.page(str(scaffolding.id), scaffolding.spec, parameters, offset, limit)

    def read_rendered_file(
        self,
        id: str,
        parameters: Mapping[str, JsonValue],
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RenderedFileContent:
        scaffolding = self.get(id)
        return self.renderings.read_file(
            str(scaffolding.id),
            scaffolding.spec,
            parameters,
            path,
            expected_revision,
            offset,
            limit,
        )

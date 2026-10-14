from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from enclosure.shared.source_code.package import CodePackage, SourceCodePackage

from ..api.schemas import ReadScaffoldingRenderedFile, RenderScaffolding, ScaffoldingInput
from .content.model import ScaffoldingDetail, ScaffoldingPage, ScaffoldingTemplateContent, TemplateManifestPage
from .content.service import ScaffoldingContentService
from .registry.model import ScaffoldingCandidate, ScaffoldingValue
from .registry.repository import ScaffoldingRepository
from .renderings.model import RenderedFile, RenderedFileContent, RenderingPage
from .renderings.service import RenderingService
from .spec.model import ScaffoldingSpec, Template, Variable, VariableType, WriteMode
from .spec.service import ScaffoldingSpecService


@injectable
@dataclass(frozen=True)
class ScaffoldingService:
    repository: ScaffoldingRepository
    renderings: RenderingService
    spec_service: ScaffoldingSpecService
    content: ScaffoldingContentService

    def candidate(self, input: ScaffoldingInput) -> ScaffoldingCandidate:
        spec = ScaffoldingSpec(
            language=input.spec.language,
            variables=tuple(
                Variable(name=variable.name, type=VariableType(variable.type)) for variable in input.spec.variables
            ),
            templates=tuple(
                Template(
                    path=template.path,
                    content=template.content,
                    write_mode=WriteMode(template.write_mode),
                )
                for template in input.spec.templates
            ),
        )
        return ScaffoldingCandidate(
            language_id=input.language_id,
            name=input.name,
            description=input.description,
            spec=spec,
        )

    def create(self, input: ScaffoldingInput) -> ScaffoldingDetail:
        return self.content.detail(self.repository.create(self.candidate(input)))

    def get(self, id: str) -> ScaffoldingValue:
        return self.repository.get(id)

    def find_all(self) -> tuple[ScaffoldingValue, ...]:
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

    def search(self, name: str, language_id: str, limit: int) -> tuple[ScaffoldingValue, ...]:
        return self.repository.search(name, language_id, limit)

    def get_detail(self, id: str) -> ScaffoldingDetail:
        return self.content.detail(self.get(id))

    def update(self, id: str, input: ScaffoldingInput) -> ScaffoldingDetail:
        return self.content.detail(self.repository.replace(id, self.candidate(input)))

    def delete(self, id: str) -> None:
        self.repository.delete(id)

    def render(self, id: str, parameters: dict[str, JsonValue]) -> SourceCodePackage:
        scaffolding = self.get(id)
        files = self.renderings.render(self.spec_service.prepare(scaffolding.spec, parameters))
        return SourceCodePackage.model_construct(
            language=scaffolding.spec.language,
            package=CodePackage.model_construct(files={file.path: file.content for file in files}),
        )

    def render_files(self, id: str, parameters: dict[str, JsonValue]) -> tuple[RenderedFile, ...]:
        scaffolding = self.get(id)
        return self.renderings.render(self.spec_service.prepare(scaffolding.spec, parameters))

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

    def render_page(self, id: str, input: RenderScaffolding) -> RenderingPage:
        scaffolding = self.get(id)
        prepared = self.spec_service.prepare(scaffolding.spec, input.parameters)
        return self.renderings.page(scaffolding.id, prepared, input.offset, input.limit)

    def read_rendered_file(
        self,
        id: str,
        input: ReadScaffoldingRenderedFile,
    ) -> RenderedFileContent:
        scaffolding = self.get(id)
        prepared = self.spec_service.prepare(scaffolding.spec, input.parameters)
        return self.renderings.read_file(
            scaffolding.id,
            prepared,
            input.path,
            input.expected_revision,
            input.offset,
            input.limit,
        )

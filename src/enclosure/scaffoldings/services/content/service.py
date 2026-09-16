import hashlib
from dataclasses import dataclass

from wireup import injectable

from ...errors import ScaffoldingError
from ...models import Scaffolding
from ..spec.service import ScaffoldingSpecService
from .model import (
    ScaffoldingDetail,
    ScaffoldingSpecManifest,
    ScaffoldingTemplateContent,
    TemplateManifest,
)


@injectable
@dataclass(frozen=True)
class ScaffoldingContentService:
    spec_service: ScaffoldingSpecService

    def detail(self, scaffolding: Scaffolding) -> ScaffoldingDetail:
        spec = self.spec_service.validate(scaffolding.spec)
        return ScaffoldingDetail(
            id=str(scaffolding.id),
            language_id=scaffolding.language_id,
            name=scaffolding.name,
            description=scaffolding.description,
            spec=ScaffoldingSpecManifest(
                language=spec.language,
                variables=tuple(variable.model_dump(mode="json") for variable in spec.variables),
                templates=tuple(
                    TemplateManifest(
                        path=template.path,
                        write_mode=template.write_mode,
                        size_bytes=len(template.content.encode("utf-8")),
                        revision=self._revision(template.content),
                    )
                    for template in spec.templates
                ),
            ),
        )

    def read_template(
        self,
        scaffolding: Scaffolding,
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> ScaffoldingTemplateContent:
        spec = self.spec_service.validate(scaffolding.spec)
        template = next((candidate for candidate in spec.templates if candidate.path == path), None)
        if template is None:
            raise ScaffoldingError(f"Scaffolding template does not exist: {path}")

        revision = self._revision(template.content)
        self._require_revision(expected_revision, revision)
        if offset > len(template.content):
            raise ScaffoldingError("Template content offset exceeds its length.")

        content = template.content[offset : offset + limit]
        next_offset = offset + len(content)
        return ScaffoldingTemplateContent(
            scaffolding_id=str(scaffolding.id),
            path=template.path,
            write_mode=template.write_mode,
            revision=revision,
            offset=offset,
            limit=limit,
            total_characters=len(template.content),
            content=content,
            has_more=next_offset < len(template.content),
            next_offset=next_offset,
        )

    def _revision(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _require_revision(self, expected_revision: str, revision: str) -> None:
        if expected_revision != revision:
            raise ScaffoldingError("Scaffolding template revision changed; restart the read from its manifest.")

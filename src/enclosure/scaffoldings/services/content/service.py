import hashlib
import json
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
    TemplateManifestPage,
)


@injectable
@dataclass(frozen=True)
class ScaffoldingContentService:
    spec_service: ScaffoldingSpecService

    def detail(self, scaffolding: Scaffolding) -> ScaffoldingDetail:
        spec = self.spec_service.validate(scaffolding.spec)
        manifests = self._manifests(spec.templates)
        revision = self._manifest_revision(manifests)
        return ScaffoldingDetail(
            id=str(scaffolding.id),
            language_id=scaffolding.language_id,
            name=scaffolding.name,
            description=scaffolding.description,
            spec=ScaffoldingSpecManifest(
                language=spec.language,
                variables=tuple(variable.model_dump(mode="json") for variable in spec.variables),
                templates=manifests,
            ),
            templates_revision=revision,
            template_count=len(manifests),
        )

    def read_template_manifests(
        self,
        scaffolding: Scaffolding,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> TemplateManifestPage:
        manifests = self._manifests(self.spec_service.validate(scaffolding.spec).templates)
        revision = self._manifest_revision(manifests)
        self._require_revision(expected_revision, revision)
        if offset > len(manifests):
            raise ScaffoldingError("Template-manifest offset exceeds the collection length.")
        effective_limit = max(1, len(manifests) - offset) if limit == 0 else limit
        items = manifests[offset : offset + effective_limit]
        next_offset = offset + len(items)
        return TemplateManifestPage(
            scaffolding_id=str(scaffolding.id),
            revision=revision,
            offset=offset,
            limit=effective_limit,
            total=len(manifests),
            items=items,
            has_more=next_offset < len(manifests),
            next_offset=next_offset,
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

        effective_limit = max(1, len(template.content) - offset) if limit == 0 else limit
        content = template.content[offset : offset + effective_limit]
        next_offset = offset + len(content)
        return ScaffoldingTemplateContent(
            scaffolding_id=str(scaffolding.id),
            path=template.path,
            write_mode=template.write_mode,
            revision=revision,
            offset=offset,
            limit=effective_limit,
            total_characters=len(template.content),
            content=content,
            has_more=next_offset < len(template.content),
            next_offset=next_offset,
        )

    def _revision(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _manifests(self, templates) -> tuple[TemplateManifest, ...]:
        return tuple(
            TemplateManifest(
                path=template.path,
                write_mode=template.write_mode,
                size_bytes=len(template.content.encode("utf-8")),
                revision=self._revision(template.content),
            )
            for template in sorted(templates, key=lambda item: item.path)
        )

    def _manifest_revision(self, manifests: tuple[TemplateManifest, ...]) -> str:
        content = json.dumps(
            [manifest.model_dump(mode="json") for manifest in manifests],
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return self._revision(content)

    def _require_revision(self, expected_revision: str, revision: str) -> None:
        if expected_revision != revision:
            raise ScaffoldingError("Scaffolding template revision changed; restart the read from its manifest.")

import hashlib
import json
from dataclasses import dataclass

from wireup import injectable

from ...errors import ScaffoldingError
from ..model import ScaffoldingValue
from ..spec.template import Template
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
    def detail(self, scaffolding: ScaffoldingValue) -> ScaffoldingDetail:
        manifests = self.manifests(scaffolding.spec.templates)
        revision = self.manifest_revision(manifests)
        return ScaffoldingDetail(
            id=scaffolding.id,
            language_id=scaffolding.language_id,
            name=scaffolding.name,
            description=scaffolding.description,
            spec=ScaffoldingSpecManifest(
                language=scaffolding.spec.language,
                variables=scaffolding.spec.variables,
                templates=manifests,
            ),
            templates_revision=revision,
            template_count=len(manifests),
        )

    def read_template_manifests(
        self,
        scaffolding: ScaffoldingValue,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> TemplateManifestPage:
        manifests = self.manifests(scaffolding.spec.templates)
        revision = self.manifest_revision(manifests)
        self.require_revision(expected_revision, revision)
        if offset > len(manifests):
            raise ScaffoldingError("Template-manifest offset exceeds the collection length.")
        effective_limit = max(1, len(manifests) - offset) if limit == 0 else limit
        items = manifests[offset : offset + effective_limit]
        next_offset = offset + len(items)
        return TemplateManifestPage(
            scaffolding_id=scaffolding.id,
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
        scaffolding: ScaffoldingValue,
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> ScaffoldingTemplateContent:
        templates = {template.path: template for template in scaffolding.spec.templates}
        if path not in templates:
            raise ScaffoldingError(f"Scaffolding template does not exist: {path}")
        template = templates[path]

        revision = self.revision(template.content)
        self.require_revision(expected_revision, revision)
        if offset > len(template.content):
            raise ScaffoldingError("Template content offset exceeds its length.")

        effective_limit = max(1, len(template.content) - offset) if limit == 0 else limit
        content = template.content[offset : offset + effective_limit]
        next_offset = offset + len(content)
        return ScaffoldingTemplateContent(
            scaffolding_id=scaffolding.id,
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

    def revision(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def manifests(self, templates: tuple[Template, ...]) -> tuple[TemplateManifest, ...]:
        return tuple(
            TemplateManifest(
                path=template.path,
                write_mode=template.write_mode,
                size_bytes=len(template.content.encode("utf-8")),
                revision=self.revision(template.content),
            )
            for template in sorted(templates, key=lambda item: item.path)
        )

    def manifest_revision(self, manifests: tuple[TemplateManifest, ...]) -> str:
        content = json.dumps(
            [manifest.model_dump(mode="json") for manifest in manifests],
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return self.revision(content)

    def require_revision(self, expected_revision: str, revision: str) -> None:
        if expected_revision != revision:
            raise ScaffoldingError("Scaffolding template revision changed; restart the read from its manifest.")

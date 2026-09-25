import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from enclosure.shared.source_code.renderer import SourceCodeRenderer

from ...errors import ScaffoldingError
from ..spec.model import ScaffoldingSpec, WriteMode
from ..spec.service import ScaffoldingSpecService
from .model import RenderedFile, RenderedFileContent, RenderedFileManifest, RenderingPage


@injectable
@dataclass(frozen=True)
class RenderingService:
    renderer: SourceCodeRenderer
    spec_service: ScaffoldingSpecService

    def render(
        self,
        value: Mapping[str, object] | ScaffoldingSpec,
        parameters: Mapping[str, JsonValue],
    ) -> tuple[RenderedFile, ...]:
        spec = self.spec_service.validate(value)
        rendered_files: list[RenderedFile] = []
        rendered_paths: set[str] = set()

        for template in spec.templates:
            isolated_spec = spec.model_copy(update={"templates": (template,)})
            prepared = self.spec_service.prepare(isolated_spec, parameters)
            files = self.renderer.render(prepared.source, prepared.parameters).package.files
            if len(files) != 1:
                raise ScaffoldingError("Each scaffolding template must render exactly one file.")

            path, content = next(iter(files.items()))
            if path in rendered_paths:
                raise ScaffoldingError(f"Rendered scaffolding file path is not unique: {path}")

            rendered_paths.add(path)
            rendered_files.append(
                RenderedFile(
                    path=path,
                    content=content,
                    overwrite=template.write_mode == WriteMode.OVERWRITE,
                )
            )

        return tuple(rendered_files)

    def page(
        self,
        scaffolding_id: str,
        value: Mapping[str, object] | ScaffoldingSpec,
        parameters: Mapping[str, JsonValue],
        offset: int,
        limit: int,
    ) -> RenderingPage:
        files = self.render(value, parameters)
        selected = files[offset : offset + limit]
        next_offset = offset + len(selected)
        return RenderingPage(
            scaffolding_id=scaffolding_id,
            items=tuple(self._manifest(file) for file in selected),
            has_more=next_offset < len(files),
            next_offset=next_offset,
            limit=limit,
        )

    def read_file(
        self,
        scaffolding_id: str,
        value: Mapping[str, object] | ScaffoldingSpec,
        parameters: Mapping[str, JsonValue],
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RenderedFileContent:
        file = next((candidate for candidate in self.render(value, parameters) if candidate.path == path), None)
        if file is None:
            raise ScaffoldingError(f"Rendered scaffolding file does not exist: {path}")

        revision = self._revision(file.content)
        if revision != expected_revision:
            raise ScaffoldingError("Rendered file revision changed; render the scaffolding again.")
        if offset > len(file.content):
            raise ScaffoldingError("Rendered file content offset exceeds its length.")

        content = file.content[offset : offset + limit]
        next_offset = offset + len(content)
        return RenderedFileContent(
            scaffolding_id=scaffolding_id,
            path=file.path,
            overwrite=file.overwrite,
            revision=revision,
            offset=offset,
            limit=limit,
            total_characters=len(file.content),
            content=content,
            has_more=next_offset < len(file.content),
            next_offset=next_offset,
        )

    def _manifest(self, file: RenderedFile) -> RenderedFileManifest:
        return RenderedFileManifest(
            path=file.path,
            overwrite=file.overwrite,
            size_bytes=len(file.content.encode("utf-8")),
            revision=self._revision(file.content),
            preview=self._preview(file.content),
        )

    def _preview(self, content: str) -> str:
        return content if len(content) <= 256 else f"{content[:253]}..."

    def _revision(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

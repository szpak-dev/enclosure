import hashlib
from dataclasses import dataclass

from wireup import injectable

from enclosure.shared.source_code.package import CodePackage, SourceCodePackage
from enclosure.shared.source_code.renderer import SourceCodeRenderer

from ...errors import ScaffoldingError
from ..spec.model import PreparedScaffolding
from ..spec.template import WriteMode
from .model import RenderedFile, RenderedFileContent, RenderedFileManifest, RenderingPage


@injectable
@dataclass(frozen=True)
class RenderingService:
    renderer: SourceCodeRenderer

    def render(self, prepared: PreparedScaffolding) -> tuple[RenderedFile, ...]:
        rendered_files: list[RenderedFile] = []
        rendered_paths: set[str] = set()

        for template in prepared.spec.templates:
            source = SourceCodePackage.model_construct(
                language=prepared.source.language,
                package=CodePackage.model_construct(
                    files={template.path: prepared.source.package.files[template.path]}
                ),
            )
            files = self.renderer.render(source, prepared.parameters).package.files
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

        rendered_path_set = {file.path for file in rendered_files}
        topology_conflicts: list[tuple[str, str]] = []
        for file in rendered_files:
            parts = file.path.split("/")
            for index in range(1, len(parts)):
                ancestor = "/".join(parts[:index])
                if ancestor in rendered_path_set:
                    topology_conflicts.append((ancestor, file.path))

        if topology_conflicts:
            rendered_conflicts = ", ".join(
                f"{ancestor} and {descendant}" for ancestor, descendant in sorted(topology_conflicts)
            )
            raise ScaffoldingError(
                f"Rendered scaffolding paths conflict as files and directories: {rendered_conflicts}"
            )

        return tuple(rendered_files)

    def page(
        self,
        scaffolding_id: str,
        prepared: PreparedScaffolding,
        offset: int,
        limit: int,
    ) -> RenderingPage:
        files = self.render(prepared)
        selected = files[offset : offset + limit]
        next_offset = offset + len(selected)
        return RenderingPage(
            scaffolding_id=scaffolding_id,
            items=tuple(self.manifest(file) for file in selected),
            has_more=next_offset < len(files),
            next_offset=next_offset,
            limit=limit,
        )

    def read_file(
        self,
        scaffolding_id: str,
        prepared: PreparedScaffolding,
        path: str,
        expected_revision: str,
        offset: int,
        limit: int,
    ) -> RenderedFileContent:
        files = {file.path: file for file in self.render(prepared)}
        if path not in files:
            raise ScaffoldingError(f"Rendered scaffolding file does not exist: {path}")
        file = files[path]

        revision = self.revision(file.content)
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

    def manifest(self, file: RenderedFile) -> RenderedFileManifest:
        return RenderedFileManifest(
            path=file.path,
            overwrite=file.overwrite,
            size_bytes=len(file.content.encode("utf-8")),
            revision=self.revision(file.content),
            preview=self.preview(file.content),
        )

    def preview(self, content: str) -> str:
        return content if len(content) <= 256 else f"{content[:253]}..."

    def revision(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

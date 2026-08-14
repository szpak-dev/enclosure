from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from enclosure.shared import SourceCodeRenderer

from ...errors import ScaffoldingError
from ..spec.model import ScaffoldingSpec
from ..spec.service import ScaffoldingSpecService
from ..spec.template import WriteMode
from .model import RenderedFile


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

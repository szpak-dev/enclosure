from dataclasses import dataclass
from pathlib import Path

from wireup import injectable

from enclosure.scaffoldings.services import RenderedFile
from enclosure.shared import CodePackage, CodePackageWriter

from ....errors import ProjectsError


@injectable
@dataclass(frozen=True)
class FilesystemAdapter:
    writer: CodePackageWriter

    def write(
        self,
        project_root: str,
        destination: str,
        files: tuple[RenderedFile, ...],
    ) -> tuple[str, ...]:
        root = Path(project_root).resolve()
        if not root.is_dir():
            raise ProjectsError(f"Invalid project root: {root}")

        relative_destination = Path(destination)
        if relative_destination.is_absolute():
            raise ProjectsError("Generation destination must be relative to the project root.")

        output_root = (root / relative_destination).resolve()
        if not output_root.is_relative_to(root):
            raise ProjectsError("Generation destination escapes the project root.")

        self._validate_targets(root, output_root, files)
        for file in files:
            self.writer.write(
                CodePackage(files={file.path: file.content}),
                output_root,
                overwrite=file.overwrite,
            )

        return tuple(
            sorted((output_root / file.path).resolve().relative_to(root).as_posix() for file in files)
        )

    def _validate_targets(
        self,
        project_root: Path,
        output_root: Path,
        files: tuple[RenderedFile, ...],
    ) -> None:
        for file in files:
            target = (output_root / file.path).resolve()
            if not target.is_relative_to(project_root):
                raise ProjectsError(f"Rendered file path escapes the project root: {file.path}")
            if target.exists() and not file.overwrite:
                relative_target = target.relative_to(project_root).as_posix()
                raise ProjectsError(f"Destination already contains: {relative_target}")

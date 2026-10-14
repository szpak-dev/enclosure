from dataclasses import dataclass
from pathlib import Path

from wireup import injectable

from enclosure.scaffoldings.services.renderings.model import RenderedFile
from enclosure.shared.source_code.package import CodePackage
from enclosure.shared.source_code.writer import CodePackageWriter

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

        targets = tuple((file, (output_root / file.path).resolve()) for file in files)
        target_paths = tuple(target[1] for target in targets)
        if len(set(target_paths)) != len(target_paths):
            raise ProjectsError("Rendered file paths must resolve to unique destinations.")

        target_path_set = set(target_paths)
        for file, target in targets:
            if not target.is_relative_to(root):
                raise ProjectsError(f"Rendered file path escapes the project root: {file.path}")

            for parent in target.parents:
                if not parent.is_relative_to(root):
                    break
                if parent.exists() and not parent.is_dir():
                    relative_parent = parent.relative_to(root).as_posix()
                    raise ProjectsError(f"Generation path is occupied by a file: {relative_parent}")
                if parent == root:
                    break

            conflicting_parents = tuple(parent for parent in target.parents if parent in target_path_set)
            if conflicting_parents:
                conflicting_parent = conflicting_parents[0]
                relative_parent = conflicting_parent.relative_to(root).as_posix()
                relative_target = target.relative_to(root).as_posix()
                raise ProjectsError(
                    f"Rendered file destinations conflict as a file and directory: "
                    f"{relative_parent} and {relative_target}"
                )

            if target.is_dir():
                relative_target = target.relative_to(root).as_posix()
                raise ProjectsError(f"Generation destination is an existing directory: {relative_target}")
            if target.exists() and not file.overwrite:
                relative_target = target.relative_to(root).as_posix()
                raise ProjectsError(f"Destination already contains: {relative_target}")

        for file in files:
            self.writer.write(
                CodePackage(files={file.path: file.content}),
                output_root,
                overwrite=file.overwrite,
            )

        return tuple(sorted((output_root / file.path).resolve().relative_to(root).as_posix() for file in files))

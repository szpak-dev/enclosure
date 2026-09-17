from dataclasses import dataclass
from pathlib import Path

from modwire.shared.code.models.queryable_code_map import QueryableCodeMap
from wireup import injectable

from .code_map import QueryableCodeMapReader
from .package import SourceCodePackage
from .reader import CodePackageReader


@injectable
@dataclass(frozen=True)
class SourceCodeService:
    reader: CodePackageReader
    code_map_reader: QueryableCodeMapReader

    def read(self, root: Path, language: str, extensions: list[str]) -> SourceCodePackage:
        package = self.reader.read_package(root, extensions)
        return SourceCodePackage(language=language, package=package)

    def read_map(
        self,
        root: Path,
        language: str,
        excluded_patterns: tuple[str, ...] = (),
    ) -> QueryableCodeMap:
        return self.code_map_reader.read(root, language, excluded_patterns)

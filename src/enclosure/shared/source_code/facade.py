from dataclasses import dataclass
from pathlib import Path

from wireup import injectable

from .package import SourceCodePackage
from .reader import CodePackageReader


@injectable
@dataclass(frozen=True)
class SourceCodeService:
    reader: CodePackageReader

    def read(self, root: Path, language: str, extensions: list[str]) -> SourceCodePackage:
        package = self.reader.read_package(root, extensions)
        return SourceCodePackage(language=language, package=package)

from dataclasses import dataclass
from pathlib import Path

from modwire.application import ModwireApplication, ScanPolicy
from modwire.shared.code.models.queryable_code_map import QueryableCodeMap
from wireup import injectable

from .package import SourceCodePackage


@dataclass(frozen=True)
class SourceCodeMap:
    source: SourceCodePackage
    code_map: QueryableCodeMap


@injectable
class QueryableCodeMapReader:
    def read(
        self,
        root: Path,
        language: str,
        excluded_patterns: tuple[str, ...] = (),
    ) -> QueryableCodeMap:
        return ModwireApplication.create().generate_queryable_map(
            language,
            str(root),
            ScanPolicy(excluded_patterns=excluded_patterns),
        )

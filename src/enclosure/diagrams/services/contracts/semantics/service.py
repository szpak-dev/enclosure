from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from operator import attrgetter

from pydantic import JsonValue
from wireup import injectable

from ....errors import DiagramsError
from ...mermaiden.service import MermaidenService
from .extractors.base import DiagramSemanticExtractor
from .model import DiagramContractSemantics
from .snapshots import DiagramSnapshotRestorationService


@injectable
@dataclass(frozen=True)
class DiagramContractSemanticsService:
    mermaiden: MermaidenService
    snapshots: DiagramSnapshotRestorationService
    extractors: Sequence[DiagramSemanticExtractor]

    def interpret(
        self,
        kind: str,
        snapshot: Mapping[str, JsonValue],
        snapshot_version: int,
        registry_fingerprint: str,
    ) -> DiagramContractSemantics:
        diagram = self.snapshots.restore(kind, snapshot, snapshot_version, registry_fingerprint)
        self.mermaiden.validate_render(diagram)
        candidates = tuple(extractor for extractor in self.extractors if extractor.kind == kind)
        if len(candidates) != 1:
            raise DiagramsError(f"Diagram contract semantics require exactly one extractor for {kind!r}.")
        extractor = sorted(candidates, key=attrgetter("order", "kind"))[0]
        return extractor.extract(diagram)

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from operator import attrgetter

from wireup import injectable

from ....errors import DiagramsError
from ...mermaiden.service import MermaidenService
from .extractors.base import DiagramSemanticExtractor
from .model import DiagramContractSemantics


@injectable
@dataclass(frozen=True)
class DiagramContractSemanticsService:
    mermaiden: MermaidenService
    extractors: Sequence[DiagramSemanticExtractor]

    def interpret(
        self,
        kind: str,
        snapshot: Mapping[str, object],
        snapshot_version: int,
        registry_fingerprint: str,
    ) -> DiagramContractSemantics:
        identity = self.mermaiden.snapshot_contract_identity(kind)
        if identity.snapshot_version != snapshot_version or identity.registry_fingerprint != registry_fingerprint:
            raise DiagramsError("Archived diagram snapshot contract identity is not supported by this runtime.")
        diagram = self.mermaiden.restore(snapshot)
        if diagram.kind != kind:
            raise DiagramsError("Archived diagram snapshot kind does not match its accepted contract evidence.")
        candidates = tuple(extractor for extractor in self.extractors if extractor.kind == kind)
        if len(candidates) != 1:
            raise DiagramsError(f"Diagram contract semantics require exactly one extractor for {kind!r}.")
        extractor = sorted(candidates, key=attrgetter("order", "kind"))[0]
        return extractor.extract(diagram)

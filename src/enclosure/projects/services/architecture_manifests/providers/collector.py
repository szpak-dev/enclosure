import json
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from operator import attrgetter
from typing import cast

from wireup import injectable

from ....errors import ProjectsError
from ..assertions.model import ArchitectureAssertionKind
from ..evidence.model import (
    ArtifactEvidence,
    ImplementationContext,
    ImplementationEvidence,
    ImplementationEvidenceManifest,
)
from .base import ArchitectureEvidenceProvider


@injectable
@dataclass(frozen=True)
class ArchitectureEvidenceCollector:
    providers: Sequence[ArchitectureEvidenceProvider]

    def collect(self, context: ImplementationContext) -> ImplementationEvidenceManifest:
        providers = tuple(sorted(self.providers, key=attrgetter("order", "name")))
        names = tuple(provider.name for provider in providers)
        if len(names) != len(set(names)):
            raise ProjectsError("Architecture evidence provider names must be unique.")
        collected = tuple(provider.collect(context) for provider in providers)
        combined = tuple(item for result in collected for item in result.evidence)
        artifact_keys: set[tuple[str, str]] = set()
        unique: list[ImplementationEvidence] = []
        for item in combined:
            if item.kind == ArchitectureAssertionKind.ARTIFACT:
                artifact = cast(ArtifactEvidence, item)
                key = (artifact.path, artifact.artifact_kind.value)
                if key in artifact_keys:
                    continue
                artifact_keys.add(key)
            unique.append(item)
        evidence = tuple(sorted(unique, key=lambda item: (item.kind.value, item.id, item.locator.coordinate)))
        evidence_ids = tuple(item.id for item in evidence)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ProjectsError("Canonical implementation evidence identities must be unique.")
        receipts = tuple(result.receipt for result in collected)
        source_digests = tuple(sorted({receipt.source_digest for receipt in receipts if receipt.source_digest}))
        source_digest = (
            source_digests[0]
            if len(source_digests) == 1
            else sha256("\n".join(source_digests).encode("utf-8")).hexdigest()
        )
        payload = {
            "schema_version": 2,
            "provider_receipts": [receipt.model_dump(mode="json") for receipt in receipts],
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "source_digest": source_digest,
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ImplementationEvidenceManifest(
            schema_version=2,
            provider_receipts=receipts,
            evidence=evidence,
            source_digest=source_digest,
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )

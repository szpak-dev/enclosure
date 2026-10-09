import json
from dataclasses import dataclass
from hashlib import sha256

from wireup import injectable

from .model import ArchitectureSupportState, ArtifactObservation, ArtifactObservationManifest


@injectable
@dataclass(frozen=True)
class ArtifactObservationManifestIdentity:
    def manifest(
        self,
        support: ArchitectureSupportState,
        plan_digest: str,
        observations: tuple[ArtifactObservation, ...],
    ) -> ArtifactObservationManifest:
        payload = {
            "schema_version": 1,
            "support": support.value,
            "plan_digest": plan_digest,
            "observations": [observation.model_dump(mode="json") for observation in observations],
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArtifactObservationManifest(
            schema_version=1,
            support=support,
            plan_digest=plan_digest,
            observations=observations,
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )

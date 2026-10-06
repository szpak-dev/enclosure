import json
from dataclasses import dataclass
from hashlib import sha256

from wireup import injectable

from ....errors import ProjectsError
from .model import HealthCacheComponent, HealthCacheIdentity, HealthCacheStage


@injectable
@dataclass(frozen=True)
class HealthCacheIdentityService:
    def identity(
        self,
        stage: HealthCacheStage,
        components: tuple[HealthCacheComponent, ...],
    ) -> HealthCacheIdentity:
        names = tuple(component.name for component in components)
        if len(names) != len(set(names)):
            raise ProjectsError("Health cache identity component names must be unique.")
        payload = {
            "stage": stage.value,
            "components": [
                component.model_dump(mode="json")
                for component in sorted(components, key=lambda component: component.name)
            ],
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return HealthCacheIdentity(stage=stage, digest=sha256(canonical.encode("utf-8")).hexdigest())

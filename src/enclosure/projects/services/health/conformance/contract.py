from dataclasses import dataclass
from time import perf_counter_ns
from typing import ClassVar

import structlog
from wireup import injectable

from ....errors import ProjectsError
from ...architecture_manifests.model import ArchitectureContractManifest
from ...architecture_manifests.service import ArchitectureManifestService
from ...contracts.model import ConfiguredOperatingContractBinding
from ...registry.model import ArchitectureConfiguration
from ..execution.cache import HealthCacheIdentityService
from ..execution.gateway import ArchitectureHealthCache
from ..execution.model import CacheOutcomeState, HealthCacheComponent, HealthCacheStage
from .model import ArchitectureHealthContract


@injectable
@dataclass(frozen=True)
class ArchitectureHealthContractService:
    logger: ClassVar = structlog.get_logger(__name__)

    manifests: ArchitectureManifestService
    health_cache: ArchitectureHealthCache
    cache_identities: HealthCacheIdentityService

    def resolve(
        self,
        project_id: str,
        binding: ConfiguredOperatingContractBinding,
        configuration: ArchitectureConfiguration,
    ) -> ArchitectureHealthContract:
        resolution_started_ns = perf_counter_ns()
        authority = f"project:{project_id}:architecture-contract"
        references = tuple(
            reference
            for reference in binding.effective_revision.references
            if reference.kind == "architecture" and reference.authority == authority
        )
        if len(references) != 1:
            raise ProjectsError("Project health requires exactly one accepted project architecture contract.")
        reference = references[0]
        identity = self.cache_identities.identity(
            HealthCacheStage.ARCHITECTURE_CONTRACT,
            (
                HealthCacheComponent(name="project", digest=project_id),
                HealthCacheComponent(name="publication", digest=reference.id),
                HealthCacheComponent(name="publication-revision", digest=reference.revision),
                HealthCacheComponent(name="manifest-schema", digest="3"),
                HealthCacheComponent(name="compiler-engine", digest="architecture-contract-compiler-v2"),
            ),
        )
        cached = self.health_cache.load(identity)
        manifest: ArchitectureContractManifest
        store_outcome = CacheOutcomeState.NOT_APPLICABLE
        compilation_duration_ns = 0
        resolution_outcome = "reused"
        if cached.state == CacheOutcomeState.HIT:
            try:
                cached_manifest = ArchitectureContractManifest.model_validate_json(cached.payload)
            except ValueError:
                cached = cached.model_copy(
                    update={
                        "state": CacheOutcomeState.CORRUPT,
                        "payload": b"",
                        "detail": "Health cache payload violates the architecture-contract manifest schema.",
                    }
                )
            else:
                if (
                    cached_manifest.schema_version != 3
                    or cached_manifest.project_id != project_id
                    or cached_manifest.publication_id != reference.id
                    or cached_manifest.publication_revision != reference.revision
                    or cached_manifest.digest_algorithm != "sha256"
                ):
                    cached = cached.model_copy(
                        update={
                            "state": CacheOutcomeState.STALE,
                            "payload": b"",
                            "detail": "Health cache payload does not match the accepted architecture reference.",
                        }
                    )
                else:
                    manifest = cached_manifest
        if cached.state != CacheOutcomeState.HIT:
            compilation_started_ns = perf_counter_ns()
            manifest = self.manifests.compile(project_id, reference.id)
            compilation_duration_ns = perf_counter_ns() - compilation_started_ns
            if manifest.publication_revision != reference.revision:
                raise ProjectsError("The accepted project architecture contract revision has drifted.")
            store_outcome = self.health_cache.store(identity, manifest.model_dump_json().encode("utf-8"))
            resolution_outcome = "compiled"
        self.logger.info(
            "project_health_architecture_contract_cache",
            project_id=project_id,
            publication_id=reference.id,
            publication_revision=reference.revision,
            cache_identity=identity.digest,
            manifest_digest=manifest.digest,
            resolution_outcome=resolution_outcome,
            resolution_duration_ns=perf_counter_ns() - resolution_started_ns,
            compilation_duration_ns=compilation_duration_ns,
            lookup_outcome=cached.state.value,
            lookup_detail=cached.detail,
            store_outcome=store_outcome.value,
        )
        return ArchitectureHealthContract(
            manifest=manifest,
            operating_contract=binding.effective_revision,
            update_policy=binding.update_policy,
            configuration_revision=configuration.revision,
        )

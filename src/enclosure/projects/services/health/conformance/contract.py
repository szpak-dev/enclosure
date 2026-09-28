from dataclasses import dataclass

from wireup import injectable

from ....errors import ProjectsError
from ...architecture_manifests.service import ArchitectureManifestService
from ...contracts.model import ConfiguredOperatingContractBinding
from ...registry.model import ArchitectureConfiguration
from .model import ArchitectureHealthContract


@injectable
@dataclass(frozen=True)
class ArchitectureHealthContractService:
    manifests: ArchitectureManifestService

    def resolve(
        self,
        project_id: str,
        binding: ConfiguredOperatingContractBinding,
        configuration: ArchitectureConfiguration,
    ) -> ArchitectureHealthContract:
        authority = f"project:{project_id}:architecture-contract"
        references = tuple(
            reference
            for reference in binding.effective_revision.references
            if reference.kind == "architecture" and reference.authority == authority
        )
        if len(references) != 1:
            raise ProjectsError("Project health requires exactly one accepted project architecture contract.")
        reference = references[0]
        manifest = self.manifests.compile(project_id, reference.id)
        if manifest.publication_revision != reference.revision:
            raise ProjectsError("The accepted project architecture contract revision has drifted.")
        return ArchitectureHealthContract(
            manifest=manifest,
            operating_contract=binding.effective_revision,
            update_policy=binding.update_policy,
            configuration_revision=configuration.revision,
        )

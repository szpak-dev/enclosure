from dataclasses import dataclass
from typing import cast

from wireup import injectable

from ...errors import ProjectsError
from ..architecture_manifests.model import ArchitectureContractManifest
from ..architecture_manifests.providers.base import ArchitectureArtifactObserver
from ..architecture_manifests.providers.collector import ArchitectureEvidenceCollector
from ..contracts.model import ConfiguredOperatingContractBinding
from ..contracts.service import OperatingContractsService
from ..registry.model import ArchitectureConfiguration, Project
from ..registry.service import RegistryService
from ..reports.adapters.architecture import ArchitectureAdapter
from ..reports.model import ArchitectureSource
from ..workspaces.model import WorkspaceBinding
from ..workspaces.service import WorkspaceService
from .conformance.model import ArchitectureHealthInputIdentity


@injectable
@dataclass(frozen=True)
class ArchitectureHealthInputIdentityService:
    registry: RegistryService
    workspaces: WorkspaceService
    contracts: OperatingContractsService
    architecture: ArchitectureAdapter
    artifacts: ArchitectureArtifactObserver
    evidence: ArchitectureEvidenceCollector

    def verify(
        self,
        project: Project,
        workspace: WorkspaceBinding,
        configuration: ArchitectureConfiguration,
        binding: ConfiguredOperatingContractBinding,
        source: ArchitectureSource,
        contract: ArchitectureContractManifest,
        expected_identity: ArchitectureHealthInputIdentity,
        attestation_source_digest: str,
    ) -> None:
        self.architecture.verify_source_identity(source, expected_identity.modwire_source_digest)
        plan = self.artifacts.plan(contract)
        self.artifacts.verify(source.architecture_root, plan, expected_identity.artifact_inventory_digest)
        modwire_receipts = tuple(
            receipt for receipt in expected_identity.provider_receipts if receipt.provider == "modwire"
        )
        filesystem_receipts = tuple(
            receipt for receipt in expected_identity.provider_receipts if receipt.provider == "filesystem"
        )
        if len(modwire_receipts) != 1 or len(filesystem_receipts) != 1:
            raise ProjectsError("Project health provider identities are incomplete.")
        if (
            modwire_receipts[0].source_digest != expected_identity.modwire_source_digest
            or filesystem_receipts[0].source_digest != expected_identity.artifact_inventory_digest
            or self.evidence.source_digest(expected_identity.provider_receipts) != expected_identity.digest
            or expected_identity.digest != attestation_source_digest
        ):
            raise ProjectsError("Project health input identity is inconsistent.")
        current_project = self.registry.get(project.id)
        current_workspace = self.workspaces.get(project.id, workspace.id)
        current_configuration = self.registry.get_current_architecture_configuration(project.id)
        current_binding = self.contracts.get_binding(project.id)
        if current_binding.state == "unconfigured":
            raise ProjectsError("Project health inputs changed during evaluation.")
        if (
            current_project.language_id != project.language_id
            or current_workspace.architecture_root != workspace.architecture_root
            or current_configuration != configuration
            or cast(ConfiguredOperatingContractBinding, current_binding) != binding
        ):
            raise ProjectsError("Project health inputs changed during evaluation.")

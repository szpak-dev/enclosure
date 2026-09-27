from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ..adapters.modwire import ModwireManifestAdapter
from ..architecture_contracts.service import ArchitectureContractsService
from .comparator import ArchitectureContractComparator
from .compiler import ArchitectureContractCompiler
from .model import ArchitectureComparison, ArchitectureContractManifest


@injectable
@dataclass(frozen=True)
class ArchitectureManifestService:
    contracts: ArchitectureContractsService
    compiler: ArchitectureContractCompiler
    comparator: ArchitectureContractComparator
    modwire: ModwireManifestAdapter

    def compile(self, project_id: str, publication_id: str) -> ArchitectureContractManifest:
        publication = self.contracts.get(project_id, publication_id)
        return self.compiler.compile(publication)

    def compare(
        self,
        project_id: str,
        publication_id: str,
        implementation_document: Mapping[str, object],
    ) -> ArchitectureComparison:
        contract = self.compile(project_id, publication_id)
        implementation = self.modwire.read(implementation_document)
        return self.comparator.compare(contract, implementation)

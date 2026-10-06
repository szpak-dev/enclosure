import json
from dataclasses import dataclass
from hashlib import sha256

from wireup import injectable

from ..architecture_contracts.service import ArchitectureContractsService
from .bindings.model import ArchitectureRealizationMap
from .bindings.resolver import ArchitectureBindingResolver
from .comparator import ArchitectureContractComparator
from .compiler import ArchitectureContractCompiler
from .evidence.model import ImplementationContext, ImplementationEvidenceManifest
from .model import ArchitectureComparison, ArchitectureComparisonBundle, ArchitectureContractManifest
from .providers.collector import ArchitectureEvidenceCollector


@injectable
@dataclass(frozen=True)
class ArchitectureManifestService:
    contracts: ArchitectureContractsService
    compiler: ArchitectureContractCompiler
    evidence_collector: ArchitectureEvidenceCollector
    binding_resolver: ArchitectureBindingResolver
    comparator: ArchitectureContractComparator

    def compile(self, project_id: str, publication_id: str) -> ArchitectureContractManifest:
        publication = self.contracts.get(project_id, publication_id)
        units = self.compiler.compile(publication.units)
        payload = {
            "schema_version": 3,
            "project_id": publication.project_id,
            "publication_id": publication.id,
            "publication_version": publication.version,
            "publication_revision": publication.revision,
            "units": [unit.model_dump(mode="json") for unit in units],
            "digest_algorithm": "sha256",
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArchitectureContractManifest(
            schema_version=3,
            project_id=publication.project_id,
            publication_id=publication.id,
            publication_version=publication.version,
            publication_revision=publication.revision,
            units=units,
            digest_algorithm="sha256",
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )

    def compare(
        self,
        project_id: str,
        publication_id: str,
        context: ImplementationContext,
    ) -> ArchitectureComparison:
        return self.evaluate(self.compile(project_id, publication_id), context).comparison

    def collect_evidence(self, context: ImplementationContext) -> ImplementationEvidenceManifest:
        return self.evidence_collector.collect(context)

    def realize(
        self,
        contract: ArchitectureContractManifest,
        implementation: ImplementationEvidenceManifest,
    ) -> ArchitectureRealizationMap:
        return self.binding_resolver.resolve(contract, implementation)

    def compare_evidence(
        self,
        contract: ArchitectureContractManifest,
        implementation: ImplementationEvidenceManifest,
        realization: ArchitectureRealizationMap,
    ) -> ArchitectureComparison:
        return self.comparator.compare(contract, implementation, realization)

    def evaluate(
        self,
        contract: ArchitectureContractManifest,
        context: ImplementationContext,
    ) -> ArchitectureComparisonBundle:
        implementation = self.collect_evidence(context)
        realization = self.realize(contract, implementation)
        comparison = self.compare_evidence(contract, implementation, realization)
        return ArchitectureComparisonBundle(
            contract=contract,
            implementation=implementation,
            realization=realization,
            comparison=comparison,
        )

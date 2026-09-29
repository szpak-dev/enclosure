from dataclasses import dataclass

from wireup import injectable

from ..architecture_contracts.model import ArchitectureContractPublication
from .bindings.resolver import ArchitectureBindingResolver
from .comparator import ArchitectureContractComparator
from .compiler import ArchitectureContractCompiler
from .evidence.model import ImplementationContext
from .model import ArchitectureComparison, ArchitectureComparisonBundle, ArchitectureContractManifest
from .providers.collector import ArchitectureEvidenceCollector


@injectable
@dataclass(frozen=True)
class ArchitectureManifestService:
    compiler: ArchitectureContractCompiler
    evidence_collector: ArchitectureEvidenceCollector
    binding_resolver: ArchitectureBindingResolver
    comparator: ArchitectureContractComparator

    def compile(self, publication: ArchitectureContractPublication) -> ArchitectureContractManifest:
        return self.compiler.compile(publication)

    def compare(
        self,
        publication: ArchitectureContractPublication,
        context: ImplementationContext,
    ) -> ArchitectureComparison:
        return self.evaluate(self.compile(publication), context).comparison

    def evaluate(
        self,
        contract: ArchitectureContractManifest,
        context: ImplementationContext,
    ) -> ArchitectureComparisonBundle:
        implementation = self.evidence_collector.collect(context)
        realization = self.binding_resolver.resolve(contract, implementation)
        comparison = self.comparator.compare(contract, implementation, realization)
        return ArchitectureComparisonBundle(
            contract=contract,
            implementation=implementation,
            realization=realization,
            comparison=comparison,
        )

from abc import ABC, abstractmethod

from ..assertions.model import ArchitectureAssertion, ArchitectureAssertionKind
from ..evidence.model import (
    ArchitectureSupportState,
    ImplementationEvidence,
)
from .model import (
    ArchitectureAmbiguousBinding,
    ArchitectureBindingContext,
    ArchitectureBindingOutcome,
    ArchitectureBindingState,
    ArchitectureBoundBinding,
    ArchitectureMissingBinding,
    ArchitectureUnsupportedBinding,
)


class ArchitectureBindingRule(ABC):
    assertion_kind: ArchitectureAssertionKind
    name: str
    order: int

    @abstractmethod
    def bind(
        self,
        assertion: ArchitectureAssertion,
        context: ArchitectureBindingContext,
    ) -> ArchitectureBindingOutcome:
        raise NotImplementedError

    def outcome(
        self,
        assertion: ArchitectureAssertion,
        context: ArchitectureBindingContext,
        candidates: tuple[ImplementationEvidence, ...],
    ) -> ArchitectureBindingOutcome:
        candidate_ids = tuple(candidate.id for candidate in candidates)
        if len(candidates) == 1:
            return ArchitectureBoundBinding(
                unit_key=assertion.unit_key,
                assertion_id=assertion.id,
                state=ArchitectureBindingState.BOUND,
                candidate_ids=candidate_ids,
                evidence_id=candidates[0].id,
            )
        if len(candidates) > 1:
            return ArchitectureAmbiguousBinding(
                unit_key=assertion.unit_key,
                assertion_id=assertion.id,
                state=ArchitectureBindingState.AMBIGUOUS,
                candidate_ids=candidate_ids,
            )
        support = context.observed.inventory_support(assertion.kind)
        if support.support != ArchitectureSupportState.SUPPORTED:
            return ArchitectureUnsupportedBinding(
                unit_key=assertion.unit_key,
                assertion_id=assertion.id,
                state=ArchitectureBindingState.UNSUPPORTED,
                candidate_ids=(),
                explanation=support.explanation or "Implementation evidence is incomplete for this semantic.",
            )
        return ArchitectureMissingBinding(
            unit_key=assertion.unit_key,
            assertion_id=assertion.id,
            state=ArchitectureBindingState.MISSING,
            candidate_ids=(),
        )

    def blocked(self, assertion: ArchitectureAssertion, explanation: str) -> ArchitectureBindingOutcome:
        return ArchitectureUnsupportedBinding(
            unit_key=assertion.unit_key,
            assertion_id=assertion.id,
            state=ArchitectureBindingState.UNSUPPORTED,
            candidate_ids=(),
            explanation=explanation,
        )

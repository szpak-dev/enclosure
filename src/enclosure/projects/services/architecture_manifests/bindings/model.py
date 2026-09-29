from abc import ABC
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, SerializeAsAny

from ....errors import ProjectsError
from ..assertions.model import ArchitectureAssertion
from ..evidence.model import ImplementationEvidence, ImplementationEvidenceManifest


class ArchitectureBindingState(StrEnum):
    BOUND = "bound"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


class ArchitectureBindingOutcome(BaseModel, ABC):
    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_key: str
    assertion_id: str
    state: ArchitectureBindingState
    candidate_ids: tuple[str, ...]


class ArchitectureBoundBinding(ArchitectureBindingOutcome):
    evidence_id: str


class ArchitectureMissingBinding(ArchitectureBindingOutcome):
    pass


class ArchitectureAmbiguousBinding(ArchitectureBindingOutcome):
    pass


class ArchitectureUnsupportedBinding(ArchitectureBindingOutcome):
    explanation: str


class ArchitectureRealizationMap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bindings: tuple[SerializeAsAny[ArchitectureBindingOutcome], ...]
    digest: str


class ArchitectureBindingContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observed: ImplementationEvidenceManifest
    assertions: tuple[SerializeAsAny[ArchitectureAssertion], ...]
    outcomes: tuple[SerializeAsAny[ArchitectureBindingOutcome], ...]

    def subject(self, unit_key: str, subject_id: str) -> ArchitectureAssertion:
        matches = tuple(
            assertion
            for assertion in self.assertions
            if assertion.unit_key == unit_key and assertion.subject_id == subject_id
        )
        if len(matches) != 1:
            raise ProjectsError(f"Architecture subject {subject_id!r} has no unique declaration.")
        return matches[0]

    def outcome(self, assertion: ArchitectureAssertion) -> ArchitectureBindingOutcome:
        matches = tuple(
            outcome
            for outcome in self.outcomes
            if outcome.unit_key == assertion.unit_key and outcome.assertion_id == assertion.id
        )
        if len(matches) != 1:
            raise ProjectsError(f"Architecture assertion {assertion.id!r} has no binding outcome.")
        return matches[0]

    def evidence(self, evidence_id: str) -> ImplementationEvidence:
        matches = tuple(item for item in self.observed.evidence if item.id == evidence_id)
        if len(matches) != 1:
            raise ProjectsError(f"Implementation evidence {evidence_id!r} is not unique.")
        return matches[0]

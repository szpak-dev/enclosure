from abc import ABC
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, SerializeAsAny

from ....errors import ProjectsError
from ..assertions.model import ArchitectureArtifactKind, ArchitectureAssertion, ArchitectureMemberKind
from ..evidence.model import (
    ArtifactEvidence,
    ClassifierEvidence,
    EntityEvidence,
    EntityFieldEvidence,
    ImplementationEvidence,
    ImplementationEvidenceManifest,
    MemberEvidence,
    RelationshipEvidence,
)


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
    state: Literal[ArchitectureBindingState.BOUND] = ArchitectureBindingState.BOUND
    evidence_id: str


class ArchitectureMissingBinding(ArchitectureBindingOutcome):
    state: Literal[ArchitectureBindingState.MISSING] = ArchitectureBindingState.MISSING


class ArchitectureAmbiguousBinding(ArchitectureBindingOutcome):
    state: Literal[ArchitectureBindingState.AMBIGUOUS] = ArchitectureBindingState.AMBIGUOUS


class ArchitectureUnsupportedBinding(ArchitectureBindingOutcome):
    state: Literal[ArchitectureBindingState.UNSUPPORTED] = ArchitectureBindingState.UNSUPPORTED
    explanation: str


class ArchitectureRealizationMap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bindings: tuple[
        SerializeAsAny[
            ArchitectureBoundBinding
            | ArchitectureMissingBinding
            | ArchitectureAmbiguousBinding
            | ArchitectureUnsupportedBinding
        ],
        ...,
    ]
    digest: str


class ArchitectureEvidenceIndex(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    by_id: dict[str, ImplementationEvidence]
    positions: dict[str, int]
    artifact_candidates: dict[tuple[str, ArchitectureArtifactKind], tuple[ArtifactEvidence, ...]]
    classifier_references: dict[str, tuple[ClassifierEvidence, ...]]
    classifier_names: dict[str, tuple[ClassifierEvidence, ...]]
    member_candidates: dict[tuple[str, str, ArchitectureMemberKind], tuple[MemberEvidence, ...]]
    relationship_candidates: dict[tuple[str, str], tuple[RelationshipEvidence, ...]]
    entity_names: dict[str, tuple[EntityEvidence, ...]]
    entity_field_candidates: dict[tuple[str, str], tuple[EntityFieldEvidence, ...]]

    def evidence(self, evidence_id: str) -> ImplementationEvidence:
        try:
            return self.by_id[evidence_id]
        except KeyError as error:
            raise ProjectsError(f"Implementation evidence {evidence_id!r} is not unique.") from error

    def artifacts(self, path: str, artifact_kind: ArchitectureArtifactKind) -> tuple[ArtifactEvidence, ...]:
        return self.artifact_candidates.get((path, artifact_kind), ())

    def classifiers(self, references: tuple[str, ...], name: str) -> tuple[ClassifierEvidence, ...]:
        exact = {item.id: item for reference in references for item in self.classifier_references.get(reference, ())}
        if exact:
            return tuple(sorted(exact.values(), key=lambda item: self.positions[item.id]))
        return self.classifier_names.get(name, ())

    def members(self, owner: str, name: str, member_kind: ArchitectureMemberKind) -> tuple[MemberEvidence, ...]:
        return self.member_candidates.get((owner, name, member_kind), ())

    def relationships(self, source: str, target: str) -> tuple[RelationshipEvidence, ...]:
        return self.relationship_candidates.get((source, target), ())

    def entities(self, name: str) -> tuple[EntityEvidence, ...]:
        return self.entity_names.get(name.replace("_", "").casefold(), ())

    def entity_fields(self, owner: str, name: str) -> tuple[EntityFieldEvidence, ...]:
        return self.entity_field_candidates.get((owner, name), ())


class ArchitectureBindingContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observed: ImplementationEvidenceManifest
    index: ArchitectureEvidenceIndex
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
        return self.index.evidence(evidence_id)

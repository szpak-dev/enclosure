import json
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from operator import attrgetter
from typing import cast

from wireup import injectable

from ....errors import ProjectsError
from ..assertions.model import ArchitectureArtifactKind, ArchitectureAssertionKind, ArchitectureMemberKind
from ..evidence.model import (
    ArtifactEvidence,
    ClassifierEvidence,
    EntityEvidence,
    EntityFieldEvidence,
    ImplementationEvidenceManifest,
    MemberEvidence,
    RelationshipEvidence,
)
from ..model import ArchitectureContractManifest
from .base import ArchitectureBindingRule
from .model import (
    ArchitectureBindingContext,
    ArchitectureBindingOutcome,
    ArchitectureEvidenceIndex,
    ArchitectureRealizationMap,
)


@injectable
@dataclass(frozen=True)
class ArchitectureEvidenceIndexer:
    def index(self, observed: ImplementationEvidenceManifest) -> ArchitectureEvidenceIndex:
        artifacts = tuple(item for item in observed.evidence if item.kind == ArchitectureAssertionKind.ARTIFACT)
        classifiers = tuple(item for item in observed.evidence if item.kind == ArchitectureAssertionKind.CLASSIFIER)
        members = tuple(item for item in observed.evidence if item.kind == ArchitectureAssertionKind.MEMBER)
        relationships = tuple(item for item in observed.evidence if item.kind == ArchitectureAssertionKind.RELATIONSHIP)
        entities = tuple(item for item in observed.evidence if item.kind == ArchitectureAssertionKind.ENTITY)
        entity_fields = tuple(item for item in observed.evidence if item.kind == ArchitectureAssertionKind.ENTITY_FIELD)
        artifact_values = tuple(cast(ArtifactEvidence, item) for item in artifacts)
        classifier_values = tuple(cast(ClassifierEvidence, item) for item in classifiers)
        member_values = tuple(cast(MemberEvidence, item) for item in members)
        relationship_values = tuple(cast(RelationshipEvidence, item) for item in relationships)
        entity_values = tuple(cast(EntityEvidence, item) for item in entities)
        entity_field_values = tuple(cast(EntityFieldEvidence, item) for item in entity_fields)
        artifact_index: dict[tuple[str, ArchitectureArtifactKind], list[ArtifactEvidence]] = {}
        classifier_reference_index: dict[str, list[ClassifierEvidence]] = {}
        classifier_name_index: dict[str, list[ClassifierEvidence]] = {}
        member_index: dict[tuple[str, str, ArchitectureMemberKind], list[MemberEvidence]] = {}
        relationship_index: dict[tuple[str, str], list[RelationshipEvidence]] = {}
        entity_index: dict[str, list[EntityEvidence]] = {}
        entity_field_index: dict[tuple[str, str], list[EntityFieldEvidence]] = {}
        for item in artifact_values:
            artifact_index.setdefault((item.path, item.artifact_kind), []).append(item)
        for item in classifier_values:
            classifier_reference_index.setdefault(item.reference, []).append(item)
            classifier_name_index.setdefault(item.name, []).append(item)
        for item in member_values:
            member_index.setdefault((item.owner_id, item.name, item.member_kind), []).append(item)
        for item in relationship_values:
            relationship_index.setdefault((item.source_id, item.target_reference), []).append(item)
        for item in entity_values:
            entity_index.setdefault(item.name.replace("_", "").casefold(), []).append(item)
        for item in entity_field_values:
            entity_field_index.setdefault((item.owner_id, item.name), []).append(item)
        return ArchitectureEvidenceIndex(
            by_id={item.id: item for item in observed.evidence},
            positions={item.id: position for position, item in enumerate(observed.evidence)},
            artifact_candidates={key: tuple(values) for key, values in artifact_index.items()},
            classifier_references={key: tuple(values) for key, values in classifier_reference_index.items()},
            classifier_names={key: tuple(values) for key, values in classifier_name_index.items()},
            member_candidates={key: tuple(values) for key, values in member_index.items()},
            relationship_candidates={key: tuple(values) for key, values in relationship_index.items()},
            entity_names={key: tuple(values) for key, values in entity_index.items()},
            entity_field_candidates={key: tuple(values) for key, values in entity_field_index.items()},
        )


@injectable
@dataclass(frozen=True)
class ArchitectureBindingResolver:
    rules: Sequence[ArchitectureBindingRule]
    indexer: ArchitectureEvidenceIndexer

    def resolve(
        self,
        expected: ArchitectureContractManifest,
        observed: ImplementationEvidenceManifest,
    ) -> ArchitectureRealizationMap:
        rules = tuple(sorted(self.rules, key=attrgetter("order", "name")))
        kinds = tuple(rule.assertion_kind for rule in rules)
        if len(kinds) != len(set(kinds)) or set(kinds) != set(ArchitectureAssertionKind):
            raise ProjectsError("Architecture binding requires exactly one rule per assertion kind.")
        indexed_rules = {rule.assertion_kind: rule for rule in rules}
        assertions = tuple(assertion for unit in expected.units for assertion in unit.assertions)
        ordered_assertions = tuple(
            sorted(
                assertions,
                key=lambda assertion: (
                    indexed_rules[assertion.kind].order,
                    assertion.unit_key,
                    assertion.id,
                ),
            )
        )
        outcomes: list[ArchitectureBindingOutcome] = []
        evidence_index = self.indexer.index(observed)
        for assertion in ordered_assertions:
            context = ArchitectureBindingContext(
                observed=observed,
                index=evidence_index,
                assertions=assertions,
                outcomes=tuple(outcomes),
            )
            outcomes.append(indexed_rules[assertion.kind].bind(assertion, context))
        bindings = tuple(sorted(outcomes, key=attrgetter("unit_key", "assertion_id", "state")))
        payload = {"bindings": [binding.model_dump(mode="json") for binding in bindings]}
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return ArchitectureRealizationMap(
            bindings=bindings,
            digest=sha256(canonical.encode("utf-8")).hexdigest(),
        )

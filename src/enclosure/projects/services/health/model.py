from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ...models import GuidanceRelationshipKind
from ..adapters.model import WorkspaceGuidance


class GuidanceRequirement(StrEnum):
    MANDATORY = "mandatory"
    SUPPLEMENTAL = "supplemental"


class GuidanceRule(StrEnum):
    MISSING_ENTRY_POINT = "missing-entry-point"
    AMBIGUOUS_ENTRY_POINT = "ambiguous-entry-point"
    INVALID_RELATIONSHIP = "invalid-relationship"
    DANGLING_RELATIONSHIP = "dangling-relationship"
    GUIDANCE_CYCLE = "guidance-cycle"
    UNREACHABLE_GUIDANCE = "unreachable-guidance"
    INVALID_REFINEMENT = "invalid-refinement"
    AUTHORITY_CONFLICT = "authority-conflict"
    DUPLICATE_EFFECTIVE_POLICY = "duplicate-effective-policy"
    GUIDANCE_OVERSIZED = "guidance-oversized"
    OPTIONAL_BUDGET_EXCEEDED = "optional-budget-exceeded"


class RemediationCategory(StrEnum):
    CONTRACT = "contract"
    RELATIONSHIP = "relationship"
    REACHABILITY = "reachability"
    AUTHORITY = "authority"
    BUDGET = "budget"


class GuidanceRelationshipInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_record_id: str
    target_record_id: str
    kind: GuidanceRelationshipKind


class GuidanceRelationship(GuidanceRelationshipInput):
    id: str
    project_id: str


class GuidanceNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    guidance: WorkspaceGuidance
    requirement: GuidanceRequirement


class GuidanceGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    nodes: tuple[GuidanceNode, ...]
    entry_point_ids: tuple[str, ...]
    relationships: tuple[GuidanceRelationship, ...]
    missing_record_ids: tuple[str, ...]


class GuidanceFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: GuidanceRule
    source_id: str
    guidance_ids: tuple[str, ...]
    message: str
    remediation: RemediationCategory


class GuidanceHealthMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    description: str
    model: str
    path: str
    order: int
    children: tuple[str, ...]


class GuidanceHealthReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    healthy: bool
    metadata: GuidanceHealthMetadata
    violations: tuple[GuidanceFinding, ...]
    advisories: tuple[GuidanceFinding, ...]

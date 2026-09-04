from typing import Annotated, Literal

from ninja import Schema
from pydantic import Field, JsonValue

ProjectId = Annotated[str, Field(description="Project identifier.")]
WorkspaceId = Annotated[str, Field(description="Workspace-binding identifier.")]


class DiscoverProject(Schema):
    root: str = Field(description="Absolute path to the project directory.")


class DetectedStack(Schema):
    language: str = Field(description="Detected programming-language identifier.")
    language_version: str = Field(description="Detected programming-language version, when available.")
    package_manager: str = Field(description="Detected package-manager identifier.")


class DiscoveredProject(Schema):
    root: str = Field(description="Absolute path to the project directory.")
    stack: DetectedStack = Field(description="Technology stack detected in the project directory.")


class FindProjectByRoot(Schema):
    root: str = Field(description="Absolute path to the registered project directory.")


class GetWorkspaceContext(Schema):
    root: str = Field(description="Absolute path to the registered project directory.")
    task: str = Field(description="Current task used to select relevant project guidance.")


class WorkspaceGuidance(Schema):
    id: str = Field(description="Guidance record identifier.")
    title: str = Field(description="Guidance title.")
    summary: str = Field(description="Compact statement of the guidance purpose.")
    authority: str = Field(description="Stable authority claimed by this guidance source.")
    revision: str = Field(description="Deterministic revision of the resolved guidance source.")
    schema_revision: int = Field(description="Category schema revision assigned to this guidance source.", ge=1)
    current_schema_revision: int = Field(description="Current category schema revision.", ge=1)
    applies_when: list[str] = Field(description="Situations in which the guidance applies.")
    guidance: list[str] = Field(description="Constraints applicable to the task.")
    checks: list[str] = Field(description="Checks required before handoff.")


class WorkspaceAuthority(Schema):
    kind: Literal["project-operating-contract"] = Field(description="Authority mechanism used for this response.")
    id: str = Field(description="Stable identifier of the effective authority.")
    revision: str = Field(description="Deterministic revision of the effective authority.")
    provenance: str = Field(description="Origin of the effective operating contract.")


class WorkspaceContextDiagnostic(Schema):
    code: str = Field(description="Stable machine-readable readiness diagnostic code.")
    message: str = Field(description="Actionable explanation of the readiness problem.")
    guidance_ids: list[str] = Field(description="Bound guidance records affected by the diagnostic.")


class ReceiptItem(Schema):
    record_id: str = Field(description="Durable guidance record identifier for get_record follow-up.")
    title: str = Field(description="Guidance title.")
    requirement: Literal["mandatory", "supplemental"] = Field(
        description="Whether the item is contract-mandated or routed supplemental guidance."
    )
    reason: Literal["operating-contract", "task-applicable", "project-default"] = Field(
        description="Stable selection reason."
    )
    explanation: str = Field(description="Stable human-readable explanation of the selection reason.")
    authority: str = Field(description="Authority claimed by the selected guidance.")
    revision: str = Field(description="Selected guidance revision.")
    checks: list[str] = Field(description="Checks contributed by the selected guidance.")


class ContextBudget(Schema):
    used_optional_characters: int = Field(
        description="Characters consumed by minified serialized selected supplemental guidance."
    )
    optional_character_limit: int = Field(
        description="Maximum minified serialized characters available to supplemental guidance."
    )


class ContextCoverage(Schema):
    status: Literal["complete", "partial"] = Field(description="Whether selection has omissions or diagnostics.")
    selected_count: int = Field(description="Number of selected guidance items.")
    omitted_count: int = Field(description="Number of omitted supplemental guidance items.")
    diagnostic_count: int = Field(description="Number of context diagnostics.")


class ContextOmission(Schema):
    code: Literal["optional-budget-exhausted"] = Field(description="Stable omission reason code.")
    guidance_ids: list[str] = Field(description="Supplemental guidance records omitted by the context budget.")
    message: str = Field(description="Human-readable omission explanation.")


class ContextReceipt(Schema):
    authority: WorkspaceAuthority = Field(description="Authority and revision used to resolve this response.")
    items: list[ReceiptItem] = Field(description="Selection receipt in effective guidance order.")
    required_checks: list[str] = Field(description="Ordered, de-duplicated checks required before handoff.")
    budget: ContextBudget = Field(description="Supplemental guidance budget accounting.")
    coverage: ContextCoverage = Field(description="Selection coverage summary.")
    omissions: list[ContextOmission] = Field(description="Explicit supplemental-guidance omissions.")
    diagnostics: list[WorkspaceContextDiagnostic] = Field(
        description="Stable reasons the response is incomplete or conflicted."
    )
    stop_condition: Literal["selected-guidance-and-checks", "resolve-context-gaps"] = Field(
        description="Condition the agent must satisfy before continuing."
    )


class WorkspaceContext(Schema):
    project_id: ProjectId
    root: str = Field(description="Registered project root.")
    readiness: Literal["ready", "incomplete", "conflicted"] = Field(
        description="Whether the returned context is safe to treat as complete."
    )
    guidance: list[WorkspaceGuidance] = Field(
        description="Mandatory guidance first, followed by routed optional guidance."
    )
    receipt: ContextReceipt = Field(description="Deterministic explanation of selection, coverage, and checks.")


class GuidanceScope(Schema):
    id: str = Field(description="Guidance-scope identifier.")
    project_id: ProjectId
    record_id: str = Field(description="Optional guidance record made eligible for this project.")
    position: int = Field(description="Deterministic fallback position within the project.", ge=1)


class ReplaceGuidanceScopes(Schema):
    record_ids: list[str] = Field(description="Ordered optional guidance records eligible for routing.")


class GuidanceRelationshipInput(Schema):
    source_record_id: str = Field(description="Guidance record at the relationship source.")
    target_record_id: str = Field(description="Guidance record at the relationship target.")
    kind: Literal["prerequisite", "containment", "refinement", "escalation"] = Field(
        description="Typed guidance-graph relationship."
    )


class GuidanceRelationship(GuidanceRelationshipInput):
    id: str = Field(description="Guidance-relationship identifier.")
    project_id: ProjectId


class ReplaceGuidanceRelationships(Schema):
    relationships: list[GuidanceRelationshipInput] = Field(
        description="Complete project-scoped guidance relationship set."
    )


class RegisterProject(Schema):
    discovery: DiscoveredProject = Field(description="Detected project root and technology stack.")
    architecture_root: str = Field(description="Absolute path analyzed by the architecture rules.")
    boundaries_yaml: str = Field(description="Modwire boundary configuration in YAML.")
    shape_yaml: str = Field(description="Modwire architecture-shape configuration in YAML.")
    scaffolding_id: str = Field(description="Identifier of the scaffolding used to generate project source code.")
    record_ids: list[str] = Field(
        description="Records used to publish and bind the initial operating contract; empty leaves it unconfigured."
    )


class UpdateProject(Schema):
    title: str = Field(description="Editable logical project title.", min_length=1, max_length=255)
    stack: DetectedStack = Field(description="Detected technology stack for the logical project.")
    boundaries_yaml: str = Field(description="Modwire boundary configuration in YAML.")
    shape_yaml: str = Field(description="Modwire architecture-shape configuration in YAML.")
    scaffolding_id: str = Field(description="Identifier of the scaffolding used to generate project source code.")


class CreateOperatingContract(Schema):
    title: str = Field(description="Human-readable operating-contract title.", min_length=1)
    authority: str = Field(description="Stable canonical authority owned by this contract.", min_length=1)
    provenance: str = Field(description="Origin of the contract definition.", min_length=1)


class OperatingContract(Schema):
    id: str = Field(description="Operating-contract identifier.")
    title: str = Field(description="Human-readable operating-contract title.")
    authority: str = Field(description="Stable canonical authority owned by this contract.")
    provenance: str = Field(description="Origin of the contract definition.")


class OperatingContractReference(Schema):
    kind: Literal["guidance", "policy", "architecture"] = Field(description="Referenced contract kind.")
    id: str = Field(description="Identifier owned by the referenced domain.", min_length=1)
    authority: str = Field(description="Canonical authority of the referenced contract.", min_length=1)
    revision: str = Field(description="Immutable referenced revision.", min_length=1)


class PublishOperatingContractRevision(Schema):
    record_ids: list[str] = Field(description="Mandatory guidance records captured by this revision.", min_length=1)
    references: list[OperatingContractReference] = Field(
        default_factory=list,
        description="Typed policy and architecture references captured without copying their semantics.",
    )


class OperatingContractRevision(Schema):
    id: str = Field(description="Published operating-contract revision identifier.")
    contract_id: str = Field(description="Owning operating-contract identifier.")
    version: int = Field(description="Contract-local immutable revision number.", ge=1)
    references: list[OperatingContractReference] = Field(description="Ordered immutable contract references.")


class WriteOperatingContractBinding(Schema):
    contract_id: str = Field(description="Operating contract to bind.")
    version: int = Field(description="Published revision anchoring the binding.", ge=1)
    update_policy: Literal["pinned", "follow-latest"] = Field(
        description="Whether the effective revision stays pinned or follows later publications."
    )


class ConfiguredOperatingContractBinding(Schema):
    state: Literal["configured"] = Field(description="Discriminator for an active operating-contract binding.")
    project_id: ProjectId
    contract: OperatingContract = Field(description="Canonical operating-contract envelope bound to the project.")
    update_policy: Literal["pinned", "follow-latest"] = Field(
        description="Policy used to resolve the effective published revision."
    )
    bound_revision: int = Field(description="Revision selected when the binding was written.", ge=1)
    effective_revision: OperatingContractRevision = Field(
        description="Published revision currently governing the project."
    )


class UnconfiguredOperatingContractBinding(Schema):
    state: Literal["unconfigured"] = Field(description="Discriminator for a project without a contract binding.")
    project_id: ProjectId


class GenerateProjectSource(Schema):
    destination: str = Field(
        description="Destination directory relative to the registered project root.",
        min_length=1,
    )
    parameters: dict[str, JsonValue] = Field(description="Values for the associated scaffolding variables.")


class GeneratedProjectSource(Schema):
    files: tuple[str, ...] = Field(description="Written file paths relative to the registered project root.")


class ProjectReference(Schema):
    id: ProjectId
    title: str = Field(description="Editable logical project title.")


class Project(Schema):
    id: ProjectId
    title: str = Field(description="Editable logical project title.")
    language_id: str = Field(description="Detected programming-language identifier.")
    language_version: str = Field(description="Detected programming-language version, when available.")
    package_manager_id: str = Field(description="Detected package-manager identifier.")
    scaffolding_id: str = Field(description="Identifier of the scaffolding used to generate project source code.")


class WriteWorkspaceBinding(Schema):
    root: str = Field(description="Absolute path to the local project checkout.", min_length=1, max_length=1024)
    architecture_root: str = Field(
        description="Absolute local path analyzed by the architecture rules.",
        min_length=1,
        max_length=1024,
    )


class ReplaceWorkspaceBinding(WriteWorkspaceBinding):
    expected_revision: int = Field(description="Current workspace revision used for conflict detection.", ge=1)


class DeleteWorkspaceBinding(Schema):
    expected_revision: int = Field(description="Current workspace revision used for conflict detection.", ge=1)


class WorkspaceBinding(WriteWorkspaceBinding):
    id: WorkspaceId
    project_id: ProjectId
    revision: int = Field(description="Optimistic-concurrency revision.", ge=1)


class WorkspaceStatus(Schema):
    workspace: WorkspaceBinding = Field(description="Inspected local workspace binding.")
    state: Literal["available", "missing_root", "missing_architecture_root"] = Field(
        description="Availability derived from the local filesystem."
    )


class WorkspaceResolution(Schema):
    project: Project = Field(description="Portable logical project.")
    workspace: WorkspaceBinding = Field(description="Exact normalized local workspace binding.")


class ProjectArchitectureConfigurationReference(Schema):
    id: str = Field(description="Architecture configuration identifier within the project.")
    project_id: ProjectId
    revision: str = Field(description="Deterministic revision of the architecture configuration.")


class ProjectArchitectureConfiguration(ProjectArchitectureConfigurationReference):
    boundaries_yaml: str = Field(description="Modwire boundary configuration in YAML.")
    shape_yaml: str = Field(description="Modwire architecture-shape configuration in YAML.")


class ReadArchitectureConfigurationContent(Schema):
    document: Literal["boundaries_yaml", "shape_yaml"] = Field(
        description="Architecture configuration document to read."
    )
    expected_revision: str = Field(description="Configuration revision on which this read is based.")
    offset: int = Field(description="Character offset at which the bounded read starts.")
    limit: int = Field(description="Maximum characters returned by the bounded read.")


class ArchitectureConfigurationContent(Schema):
    project_id: ProjectId
    configuration_id: str = Field(description="Architecture configuration identifier within the project.")
    revision: str = Field(description="Deterministic revision of the architecture configuration.")
    document: Literal["boundaries_yaml", "shape_yaml"] = Field(
        description="Architecture configuration document that was read."
    )
    offset: int = Field(description="Character offset at which this page starts.", ge=0)
    limit: int = Field(description="Maximum characters requested for this page.", ge=1)
    total_characters: int = Field(description="Total characters in the selected document.", ge=0)
    content: str = Field(description="Bounded configuration content.")
    has_more: bool = Field(description="Whether another bounded page remains.")
    next_offset: int = Field(description="Character offset for the next read.", ge=0)


class HealthFinding(Schema):
    rule: str = Field(description="Rule that produced the finding.")
    target: str = Field(description="Project area affected by the finding.")
    message: str = Field(description="Actionable explanation of the finding.")
    related_ids: tuple[str, ...] = Field(description="Stable identifiers related to the finding.")
    remediation: str = Field(description="Remediation category supplied by the owning health rule.")
    next_action: str = Field(description="Deterministic remediation instruction.")


class HealthReportSummary(Schema):
    id: str = Field(description="Stable health-report identifier.")
    title: str = Field(description="Human-readable health-report title.")
    failure_count: int = Field(description="Number of gating failures.", ge=0)
    advisory_count: int = Field(description="Number of advisory findings.", ge=0)


class HealthReport(Schema):
    outcome: Literal["healthy", "advisory", "gating-failure"] = Field(description="Overall health outcome.")
    healthy: bool = Field(description="Whether all gating architecture and guidance rules pass.")
    reports: tuple[HealthReportSummary, ...] = Field(description="Compact architecture and guidance report summaries.")
    failure_count: int = Field(description="Total gating failures.", ge=0)
    advisory_count: int = Field(description="Total advisory findings.", ge=0)
    targets: tuple[str, ...] = Field(description="Distinct project areas affected by findings.")
    next_actions: tuple[str, ...] = Field(description="Distinct deterministic remediation instructions.")
    failures: tuple[HealthFinding, ...] = Field(description="Normalized gating findings.")
    advisories: tuple[HealthFinding, ...] = Field(description="Normalized advisory findings.")


class InsightSection(Schema):
    path: str = Field(description="Absolute JSON pointer for a bounded page operation.")
    total: int = Field(description="Number of items available at this path.", ge=0)


class InsightFinding(Schema):
    kind: Literal["hotspot", "cluster"] = Field(description="Kind of high-pressure architecture finding.")
    area: str = Field(description="Source file or cluster affected by the finding.")
    pressure_score: float = Field(description="Relative architecture pressure score.")
    incoming_count: int = Field(description="Incoming dependency count.", ge=0)
    outgoing_count: int = Field(description="Outgoing dependency count.", ge=0)


class InsightsReport(Schema):
    project_id: ProjectId
    workspace_id: WorkspaceId
    revision: str = Field(description="Deterministic revision of the complete insights report.")
    reports: tuple[dict[str, JsonValue], ...] = Field(description="Complete non-gating architecture reports.")
    sections: tuple[InsightSection, ...] = Field(description="Collections available through bounded page reads.")
    affected_areas: tuple[str, ...] = Field(description="Distinct areas represented by the highest-priority findings.")
    top_findings: tuple[InsightFinding, ...] = Field(description="Highest-priority architecture findings.")


class ReadInsightPage(Schema):
    path: str = Field(description="Absolute JSON pointer identifying an insight collection.", pattern=r"/")
    expected_revision: str = Field(description="Insights revision on which this read is based.")
    offset: int = Field(description="Item offset at which the bounded page starts.")
    limit: int = Field(description="Maximum items returned by the bounded page.")


class InsightPage(Schema):
    project_id: ProjectId
    workspace_id: WorkspaceId
    revision: str = Field(description="Deterministic revision of the complete insights report.")
    path: str = Field(description="Absolute JSON pointer identifying the paged insight collection.")
    offset: int = Field(description="Item offset at which this page starts.", ge=0)
    limit: int = Field(description="Maximum items requested for this page.", ge=1)
    total: int = Field(description="Total items in the selected collection.", ge=0)
    items: tuple[JsonValue, ...] = Field(description="Bounded projected insight items.")
    has_more: bool = Field(description="Whether another page remains.")
    next_offset: int = Field(description="Item offset for the next page.", ge=0)

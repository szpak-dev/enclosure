from django.db import models

from ..core.models import ShortUUIDModel


class GuidanceRelationshipKind(models.TextChoices):
    PREREQUISITE = "prerequisite", "Prerequisite"
    CONTAINMENT = "containment", "Containment"
    REFINEMENT = "refinement", "Refinement"
    ESCALATION = "escalation", "Escalation"


class Project(ShortUUIDModel):
    title = models.CharField(max_length=255)
    language_id = models.CharField(max_length=32)
    language_version = models.CharField(max_length=32)
    package_manager_id = models.CharField(max_length=32)
    scaffolding_id = models.CharField(max_length=22)


class WorkspaceBinding(ShortUUIDModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="workspace_bindings",
    )
    root = models.CharField(max_length=1024, unique=True)
    architecture_root = models.CharField(max_length=1024)
    revision = models.PositiveIntegerField(default=1)


class ProjectArchitectureConfiguration(ShortUUIDModel):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="architecture_configuration",
    )
    boundaries_yaml = models.TextField()
    shape_yaml = models.TextField()


class OperatingContract(ShortUUIDModel):
    title = models.CharField(max_length=255)
    authority = models.CharField(max_length=512, unique=True)
    provenance = models.CharField(max_length=512)


class OperatingContractRevision(ShortUUIDModel):
    contract = models.ForeignKey(
        OperatingContract,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    version = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("contract", "version"),
                name="projects_operating_contract_revision_unique",
            ),
        ]


class OperatingContractGuidance(ShortUUIDModel):
    revision = models.ForeignKey(
        OperatingContractRevision,
        on_delete=models.CASCADE,
        related_name="guidance_references",
    )
    record = models.ForeignKey(
        "records.Record",
        on_delete=models.PROTECT,
        related_name="operating_contract_references",
    )
    record_revision = models.CharField(max_length=64)
    authority = models.CharField(max_length=512)
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("revision", "record"),
                name="projects_operating_contract_guidance_unique",
            ),
            models.UniqueConstraint(
                fields=("revision", "position"),
                name="projects_operating_contract_guidance_position_unique",
            ),
        ]


class OperatingContractReference(ShortUUIDModel):
    class Kind(models.TextChoices):
        POLICY = "policy", "Policy"
        ARCHITECTURE = "architecture", "Architecture"

    revision = models.ForeignKey(
        OperatingContractRevision,
        on_delete=models.CASCADE,
        related_name="contract_references",
    )
    kind = models.CharField(max_length=32, choices=Kind)
    target_id = models.CharField(max_length=255)
    authority = models.CharField(max_length=512)
    target_revision = models.CharField(max_length=128)
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("revision", "kind", "target_id"),
                name="projects_operating_contract_reference_unique",
            ),
            models.UniqueConstraint(
                fields=("revision", "position"),
                name="projects_operating_contract_reference_position_unique",
            ),
        ]


class OperatingContractBinding(ShortUUIDModel):
    class UpdatePolicy(models.TextChoices):
        PINNED = "pinned", "Pinned"
        FOLLOW_LATEST = "follow-latest", "Follow latest"

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="operating_contract_binding",
    )
    bound_revision = models.ForeignKey(
        OperatingContractRevision,
        on_delete=models.PROTECT,
        related_name="bindings",
    )
    update_policy = models.CharField(max_length=32, choices=UpdatePolicy)


class GuidanceScope(ShortUUIDModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="guidance_scopes",
    )
    record = models.ForeignKey(
        "records.Record",
        on_delete=models.PROTECT,
        related_name="guidance_scopes",
    )
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "record"),
                name="projects_guidance_scope_record_unique",
            ),
            models.UniqueConstraint(
                fields=("project", "position"),
                name="projects_guidance_scope_position_unique",
            ),
        ]


class GuidanceRelationship(ShortUUIDModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="guidance_relationships",
    )
    source_record = models.ForeignKey(
        "records.Record",
        on_delete=models.PROTECT,
        related_name="outgoing_guidance_relationships",
    )
    target_record = models.ForeignKey(
        "records.Record",
        on_delete=models.PROTECT,
        related_name="incoming_guidance_relationships",
    )
    kind = models.CharField(
        max_length=32,
        choices=GuidanceRelationshipKind,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "source_record", "target_record", "kind"),
                name="projects_guidance_relationship_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=GuidanceRelationshipKind.values),
                name="projects_guidance_relationship_kind_valid",
            ),
        ]


class ArchitectureContractPublication(ShortUUIDModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="architecture_contract_publications",
    )
    version = models.PositiveIntegerField()
    authority = models.CharField(max_length=512)
    revision = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "version"),
                name="projects_arch_contract_publication_version_unique",
            ),
            models.UniqueConstraint(
                fields=("project", "revision"),
                name="projects_arch_contract_publication_revision_unique",
            ),
        ]


class ArchitectureContractUnit(ShortUUIDModel):
    publication = models.ForeignKey(
        ArchitectureContractPublication,
        on_delete=models.CASCADE,
        related_name="units",
    )
    key = models.CharField(max_length=255)
    diagram_set_id = models.CharField(max_length=22)
    source_root = models.CharField(max_length=1024)
    coverage = models.CharField(max_length=32)
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("publication", "key"),
                name="projects_arch_contract_unit_key_unique",
            ),
            models.UniqueConstraint(
                fields=("publication", "position"),
                name="projects_arch_contract_unit_position_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(coverage__in=("closed", "declared")),
                name="projects_arch_contract_unit_coverage_valid",
            ),
        ]


class ArchitectureContractDiagram(ShortUUIDModel):
    unit = models.ForeignKey(
        ArchitectureContractUnit,
        on_delete=models.CASCADE,
        related_name="diagrams",
    )
    diagram_id = models.CharField(max_length=22)
    diagram_revision = models.PositiveIntegerField()
    role = models.CharField(max_length=32)
    scope = models.CharField(max_length=32)
    kind = models.CharField(max_length=64)
    snapshot_version = models.PositiveIntegerField()
    registry_fingerprint = models.CharField(max_length=64)
    snapshot_digest = models.CharField(max_length=64)
    snapshot = models.JSONField()
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("unit", "diagram_id"),
                name="projects_arch_contract_diagram_id_unique",
            ),
            models.UniqueConstraint(
                fields=("unit", "position"),
                name="projects_arch_contract_diagram_position_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=("tree", "uml", "entity")),
                name="projects_arch_contract_diagram_role_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(scope__in=("complete", "focused", "reference")),
                name="projects_arch_contract_diagram_scope_valid",
            ),
        ]


class ArchitectureContractExclusion(ShortUUIDModel):
    unit = models.ForeignKey(
        ArchitectureContractUnit,
        on_delete=models.CASCADE,
        related_name="exclusions",
    )
    path = models.CharField(max_length=1024)
    reason = models.TextField()
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("unit", "path"),
                name="projects_arch_contract_exclusion_path_unique",
            ),
            models.UniqueConstraint(
                fields=("unit", "position"),
                name="projects_arch_contract_exclusion_position_unique",
            ),
        ]

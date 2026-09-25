from django.db import models

from ..core.models import ShortUUIDModel


class ApprovalRequest(ShortUUIDModel):
    actor_id = models.CharField(max_length=255)
    actor_kind = models.CharField(max_length=32)
    operation_id = models.CharField(max_length=255)
    target = models.TextField()
    payload_digest = models.CharField(max_length=64)
    correlation_id = models.CharField(max_length=255)
    requested_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(
                fields=("actor_id", "actor_kind", "operation_id", "payload_digest"),
                name="security_approval_scope_idx",
            ),
        ]


class ApprovalResolution(ShortUUIDModel):
    request = models.OneToOneField(ApprovalRequest, on_delete=models.PROTECT, related_name="resolution")
    decision = models.CharField(max_length=32)
    decider_actor_id = models.CharField(max_length=255)
    decided_at = models.DateTimeField()


class ApprovalConsumption(ShortUUIDModel):
    resolution = models.OneToOneField(ApprovalResolution, on_delete=models.PROTECT, related_name="consumption")
    execution_id = models.CharField(max_length=255, unique=True)
    consumed_at = models.DateTimeField()


class AuditEvent(ShortUUIDModel):
    execution_id = models.CharField(max_length=255, db_index=True)
    actor_id = models.CharField(max_length=255, db_index=True)
    actor_kind = models.CharField(max_length=32)
    operation_id = models.CharField(max_length=255, db_index=True)
    target = models.TextField()
    payload_digest = models.CharField(max_length=64)
    phase = models.CharField(max_length=32)
    decision = models.CharField(max_length=32)
    outcome = models.CharField(max_length=32)
    reason_code = models.CharField(max_length=128)
    correlation_id = models.CharField(max_length=255, db_index=True)
    safe_metadata = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(db_index=True)

    class Meta:
        permissions = (
            ("invoke_read", "Can invoke read operations"),
            ("invoke_mutation", "Can invoke mutation operations"),
            ("invoke_destructive", "Can invoke destructive operations"),
            ("approve_operation", "Can approve destructive operations"),
        )

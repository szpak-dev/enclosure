import json

from django.db import models

from ..core.models import ShortUUIDModel


class DiagramSet(ShortUUIDModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Diagram(ShortUUIDModel):
    diagram_set = models.ForeignKey(DiagramSet, on_delete=models.CASCADE, related_name="diagrams")
    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=64)
    snapshot = models.JSONField(default=dict)
    source = models.TextField()
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def source_document(self) -> str:
        return "source"

    @property
    def snapshot_document(self) -> str:
        return "snapshot"

    @property
    def source_total_characters(self) -> int:
        return len(self.source)

    @property
    def snapshot_total_characters(self) -> int:
        return len(json.dumps(self.snapshot, ensure_ascii=False, separators=(",", ":"), sort_keys=True))

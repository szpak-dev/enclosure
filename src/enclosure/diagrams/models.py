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
    interactions = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

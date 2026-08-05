from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from ..core.models import ShortUUIDModel


class Category(ShortUUIDModel):
    title = models.CharField(max_length=255, unique=True)


class CategorySchemaRevision(ShortUUIDModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="schema_revisions")
    version = models.PositiveIntegerField()
    content_schema = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("category", "version"),
                name="records_category_schema_revision_version_unique",
            ),
        ]


class Tag(ShortUUIDModel):
    name = models.CharField(max_length=255, unique=True)


class Record(ShortUUIDModel):
    title = models.CharField(max_length=255)
    content = models.JSONField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="records")
    schema_revision = models.ForeignKey(
        CategorySchemaRevision,
        on_delete=models.PROTECT,
        related_name="records",
    )
    tags = models.ManyToManyField(Tag, related_name="records")
    embedding = VectorField(dimensions=settings.RECORDS_EMBEDDING_DIMENSIONS, null=True, blank=True)


class Resource(ShortUUIDModel):
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name="resources")
    path = models.CharField(max_length=512)
    language = models.CharField(max_length=64)
    content = models.TextField()
    embedding = VectorField(dimensions=settings.RECORDS_EMBEDDING_DIMENSIONS, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("record", "path"), name="records_resource_record_path_unique"),
        ]
